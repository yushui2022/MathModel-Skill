"""Bounded Python replay bundles. Replay never creates or reuses Pro approval.

Export and execution are separate, explicit operations. Numerical replay equality
does not establish mathematical correctness or grant a new project's stage PASS.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
from datetime import datetime, timezone

from .safety import (MAX_LOG_BYTES, atomic_json, contained_file, file_hash, is_link, spawn_options)
from .processes import popen_tree

VERSION = "1.0"
MAX_BUNDLE_FILE = 1024 * 1024 * 1024


def _now():
    return datetime.now(timezone.utc).isoformat()


def _canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _json(path: Path):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError(f"duplicate JSON key: {key}")
            value[key] = item
        return value
    def reject(value):
        raise ValueError(f"non-finite JSON number: {value}")
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs, parse_constant=reject)
    if type(value) is not dict:
        raise ValueError("JSON object required")
    return value


def _finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _plain(path: Path):
    path = path.absolute()
    if any(is_link(parent) for parent in (path, *path.parents)):
        raise ValueError("replay paths must not contain symbolic links or junctions")
    return path.resolve()


def _relative(value):
    if type(value) is not str or not value or "\\" in value or ":" in value or "\x00" in value:
        raise ValueError("portable relative path required")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or not path.parts or value != path.as_posix():
        raise ValueError("portable relative path required")
    return value


def _file(base: Path, name: str):
    return contained_file(base, _relative(name), limit=MAX_BUNDLE_FILE)


def _empty_destination(path: Path):
    path = _plain(path)
    if path.exists() and (not path.is_dir() or any(path.iterdir())):
        raise ValueError("destination must be a new or empty directory")
    return path


def _portable_args(args):
    if type(args) is not list or any(type(arg) is not str or "\x00" in arg for arg in args):
        raise ValueError("frozen arguments must be an array of strings")
    for arg in args:
        value = arg.split("=", 1)[-1] if "=" in arg else arg
        normalized = value.replace("\\", "/")
        if (normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized)
                or ".." in normalized.split("/")):
            raise ValueError("non-portable absolute/traversing run argument; author a new portable run before freezing")
    return args


def _validate_source(root: Path):
    """Use the complete installed read-only P0-P6 gate, including raw inputs."""
    scripts = Path(__file__).resolve().parents[2]/"skills/pro-workflow-orchestrator/scripts"
    if not (scripts/"pro_status.py").is_file():
        raise ValueError("installed Pro validators are missing")
    done = subprocess.run([sys.executable, "-B", str(scripts/"pro_status.py"), "--project-root", str(root.parent),
                           "--format", "json", "--fail-if-blocked", "--require-through", "P6"],
                          capture_output=True, text=True, encoding="utf-8", timeout=60,
                          env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}, **spawn_options())
    if done.returncode:
        raise ValueError("source is not a current verified freeze: " + (done.stdout or done.stderr)[-3000:])


def _environment(receipt):
    source = receipt.get("environment", {})
    version = str(source.get("python", "")).split(" ")[0]
    if not re.match(r"^\d+\.\d+\.\d+", version):
        raise ValueError("source receipt lacks a Python version")
    packages = source.get("packages")
    if type(packages) is not list or any(type(p) is not str or not re.fullmatch(r"[A-Za-z0-9_.-]+==[^\s;@]+", p) for p in packages):
        raise ValueError("source package versions cannot form a portable dependency lock")
    result = {}
    for package in packages:
        name, required = package.split("==", 1)
        key = re.sub(r"[-_.]+", "-", name).lower()
        if key in result and result[key] != required:
            raise ValueError("source environment has conflicting package versions")
        result[key] = required
    return {"python_version": version, "python_major_minor": ".".join(version.split(".")[:2]),
            "platform": source.get("platform", "unknown"), "packages": result}


def export_replay(project_root: Path | str, destination: Path | str,
                  allowed_inputs: list[str] | None = None) -> dict:
    result = {"status": "BLOCKED", "scope": "REPLAY_EXPORT_ONLY", "errors": []}
    created = False
    try:
        project = _plain(Path(project_root))
        root = _plain(project/"paper_output_pro")
        destination = _empty_destination(Path(destination))
        if destination == root or root.is_relative_to(destination):
            raise ValueError("export destination cannot replace or contain the source project")
        if destination.is_relative_to(root) and not destination.is_relative_to(root/"delivery"):
            raise ValueError("an in-project replay export must be under paper_output_pro/delivery/")
        if allowed_inputs is not None and (type(allowed_inputs) is not list or any(type(p) is not str for p in allowed_inputs)):
            raise ValueError("allowed_inputs must be an explicit list of relative file paths")
        allowed = {_relative(name) for name in (allowed_inputs or [])}
        _validate_source(root)
        freeze = _json(_file(root, "evidence_freeze.json"))
        frozen = freeze["file_hashes"]
        # Check boundaries before reading/copying each frozen file, including ancestor links.
        for name, digest in frozen.items():
            if file_hash(_file(root, name)) != digest:
                raise ValueError(f"frozen file changed: {name}")
        manifest = _json(_file(root, "experiment_manifest.json"))
        runs, roles, environments, original_metrics = [], {}, {}, {}
        failed = []
        def add(name, role, digest):
            _relative(name)
            if name in {"checkpoint_ledger.json", "pro_config.json", "evidence_freeze.json", "pro_gate_report.json"}:
                raise ValueError("project approval/configuration contracts are not replay payloads")
            if role == "input" and name.startswith("experiments/"):
                raise ValueError("cross-run experiment-output inputs are not supported by this replay release; never substitute old outputs for a new upstream run")
            if frozen.get(name) != digest or file_hash(_file(root, name)) != digest:
                raise ValueError(f"unfrozen or changed replay dependency: {name}")
            if name in roles and roles[name]["sha256"] != digest:
                raise ValueError("conflicting replay dependency hashes")
            # A file used as data requires input authorization even if named code/*.
            prior = roles.get(name)
            roles[name] = {"sha256": digest, "role": "input" if role == "input" or prior and prior["role"] == "input" else "code"}
        for entry in manifest["runs"]:
            receipt = _json(_file(root, entry["receipt_path"]))
            if receipt["status"] != "PASS":
                failed.append({"run_id": receipt["run_id"], "failure_reason": receipt.get("failure_reason")})
                continue
            run_id = receipt["run_id"]
            if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
                raise ValueError("invalid source run ID")
            spec_name = _relative(receipt["spec_path"])
            spec = _json(_file(root, spec_name))
            script = _relative(spec["script"])
            if not script.startswith("code/") or not script.endswith(".py") or not spec_name.startswith("code/"):
                raise ValueError("replay supports only frozen Python entrypoints and run specifications under code/")
            if any(spec.get(key) != receipt.get(key) for key in ("run_id", "route_id", "implementation_id", "seed")):
                raise ValueError(f"{run_id}: source receipt identity disagrees with frozen run specification")
            args = _portable_args(spec.get("args", []))
            original_tail = [arg.replace("{run_dir}", str(root/"experiments"/run_id)).replace("{seed}", str(spec.get("seed"))) for arg in args]
            argv = receipt.get("argv", [])
            if len(argv) < 2 or Path(argv[1]).resolve() != (root/script).resolve() or argv[2:] != original_tail:
                raise ValueError(f"{run_id}: recorded command differs from the frozen portable specification")
            timeout = spec.get("timeout_seconds", 1800)
            if type(timeout) is not int or not 0 < timeout <= 86400:
                raise ValueError("replay needs a positive frozen timeout <= 86400 seconds")
            expected_inputs = {_relative(name) for name in spec.get("inputs", [])}
            expected_scripts = {script, *[_relative(name) for name in spec.get("dependencies", [])]}
            if expected_inputs != set(receipt["input_hashes"]) or expected_scripts != set(receipt["script_hashes"]):
                raise ValueError(f"{run_id}: declared scripts/inputs differ from actual frozen receipt")
            if any(not name.startswith("code/") for name in expected_scripts):
                raise ValueError("replay supports only declared local helpers under code/")
            for name, digest in receipt["script_hashes"].items():
                add(name, "code", digest)
            add(spec_name, "code", receipt["spec_sha256"])
            for name, digest in receipt["input_hashes"].items():
                add(name, "input", digest)
            environment = _environment(receipt)
            env_id = _canonical(environment)[:16]
            environments[env_id] = environment
            metrics_name = _relative(receipt["metrics_file"])
            if receipt["output_hashes"].get(metrics_name) != frozen.get(metrics_name):
                raise ValueError("reference metrics were not frozen outputs")
            original_metrics[run_id] = _json(_file(root, metrics_name))["metrics"]
            runs.append({"source_run_id": run_id, "route_id": spec["route_id"], "implementation_id": spec["implementation_id"],
                         "spec_path": spec_name, "script": script, "args": args, "seed": spec.get("seed"),
                         "timeout_seconds": timeout, "input_hashes": receipt["input_hashes"], "script_hashes": receipt["script_hashes"],
                         "environment_id": env_id})
        if not runs:
            raise ValueError("freeze contains no successful runs to replay")
        if allowed-set(name for name, item in roles.items() if item["role"] == "input"):
            raise ValueError("allowed_inputs contains an undeclared replay input")
        rules = _json(_file(root, "tournament_report.json"))["comparison_rules"]
        replication = _json(_file(root, "replication_report.json"))["critical_results"]
        targets = []
        if {item["result_id"] for item in replication} != set(rules):
            raise ValueError("frozen comparison rules and critical results differ")
        for item in replication:
            rule = rules[item["result_id"]]
            if item["comparison_rule"] != rule:
                raise ValueError("frozen comparison rule mismatch")
            for reference in item["replication_paths"]:
                run_id, metric = reference["run_id"], reference["metric"]
                if run_id not in original_metrics or metric not in original_metrics[run_id]:
                    raise ValueError("comparison references an unreplayable run or missing metric")
                targets.append({"result_id": item["result_id"], "source_run_id": run_id, "metric": metric,
                                "expected": original_metrics[run_id][metric], "rule": rule})
        if not targets:
            raise ValueError("freeze has no registered replay comparisons")
        for name, item in roles.items():
            item["included"] = item["role"] == "code" or name in allowed
        bundle = {"schema_version": VERSION, "scope": "REPLAY_ONLY_NO_PROJECT_APPROVAL", "created_at_utc": _now(),
                  "source_freeze_sha256": file_hash(root/"evidence_freeze.json"), "source_snapshot_sha256": freeze["snapshot_sha256"],
                  "files": roles, "runs": runs, "environments": environments, "comparison_rules": rules,
                  "comparisons": targets, "source_failed_runs": failed,
                  "limitations": ["Python local declared dependencies only; no solver/environment installation",
                                  "Only exact/numeric comparison is executed; unsupported statistical rules block comparison",
                                  "No mathematical quality, new-project checkpoint, or official delivery approval is granted"]}
        destination.mkdir(parents=True, exist_ok=True)
        created = True
        for name, item in roles.items():
            if not item["included"]:
                continue
            target = destination/"files"/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(_file(root, name), target)
            if file_hash(target) != item["sha256"]:
                raise ValueError("source changed while exporting")
        lock_files = {}
        for env_id, environment in environments.items():
            name = f"requirements-{env_id}.lock"
            target = destination/name
            target.write_text("".join(f"{key}=={value}\n" for key, value in sorted(environment["packages"].items())), encoding="utf-8")
            lock_files[name] = file_hash(target)
        bundle["lock_files"] = lock_files
        # Ship the same bounded runtime so this bundle can be transferred and
        # run with plain Python without installing the MathModel plugin.
        runtime = Path(__file__).resolve().parent
        runner_sources = {f"runner/replay_runtime/{name}": (runtime/name).read_text(encoding="utf-8")
                          for name in ("replay.py", "safety.py", "processes.py")}
        runner_sources["runner/replay_runtime/__init__.py"] = "\"\"\"Portable MathModel numerical replay runtime.\"\"\"\n"
        runner_sources["runner/run_replay.py"] = (
            "import argparse,json,sys\nfrom pathlib import Path\nsys.dont_write_bytecode=True\n"
            "from replay_runtime.replay import run_replay\n"
            "if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')\n"
            "parser=argparse.ArgumentParser(description='Replay consistency only; grants no project approval')\n"
            "parser.add_argument('--output-root',type=Path,required=True)\n"
            "parser.add_argument('--python-executable',type=Path)\nargs=parser.parse_args()\n"
            "result=run_replay(Path(__file__).resolve().parents[1],args.output_root,args.python_executable)\n"
            "print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))\n"
            "raise SystemExit(0 if result['status']=='PASS' else 1)\n"
        )
        runner_sources["runner/README.md"] = (
            "# Independent numerical replay\n\nUse a compatible Python environment with the recorded dependency versions. "
            "This runner installs nothing and grants no MathModel project approval.\n\n"
            "Run `python -B runner/run_replay.py --output-root /absolute/path/to/new-empty-directory` "
            "from the bundle directory. Optional `--python-executable` selects the model execution interpreter. "
            "Supply any excluded inputs under their manifest `files/` paths with exactly the recorded hashes. "
            "The original bundle remains unchanged; every accepted output directory receives replay_report.json.\n"
        )
        runner_hashes = {}
        for name, text in runner_sources.items():
            target = destination/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8", newline="\n")
            runner_hashes[name] = file_hash(target)
        bundle["runner_files"] = runner_hashes
        bundle["bundle_sha256"] = _canonical(bundle)
        atomic_json(destination/"replay_manifest.json", bundle)
        # The export itself may live in delivery/ (outside frozen inventory).
        _validate_source(root)
        result.update(status="EXPORTED", destination=str(destination), manifest=str(destination/"replay_manifest.json"),
                      runner=str(destination/"runner/run_replay.py"),
                      missing_inputs=sorted(name for name, item in roles.items() if not item["included"]),
                      runs=len(runs), bundle_sha256=bundle["bundle_sha256"])
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        result["errors"].append(str(exc))
        if created:
            atomic_json(Path(destination)/"export_error.json", result)
    return result


def _check_bundle(bundle_root: Path):
    manifest = _json(_file(bundle_root, "replay_manifest.json"))
    if manifest.get("schema_version") != VERSION or manifest.get("scope") != "REPLAY_ONLY_NO_PROJECT_APPROVAL":
        raise ValueError("unsupported replay manifest")
    content = {key: value for key, value in manifest.items() if key != "bundle_sha256"}
    if manifest.get("bundle_sha256") != _canonical(content):
        raise ValueError("replay manifest digest mismatch")
    expected_files = {"replay_manifest.json", *manifest["lock_files"], *manifest["runner_files"]}
    for name, digest in {**manifest["lock_files"], **manifest["runner_files"]}.items():
        if file_hash(_file(bundle_root, name)) != digest:
            raise ValueError(f"dependency lock changed: {name}")
    for name, entry in manifest["files"].items():
        path = _file(bundle_root, "files/"+_relative(name))
        if file_hash(path) != entry["sha256"]:
            raise ValueError(f"missing or changed replay input/code: {name}")
        expected_files.add("files/"+name)
    actual_files = set()
    for directory, folders, filenames in os.walk(bundle_root, followlinks=False):
        for name in [*folders, *filenames]:
            if is_link(Path(directory)/name):
                raise ValueError("linked bundle content is forbidden")
        actual_files.update((Path(directory)/name).relative_to(bundle_root).as_posix() for name in filenames)
    if actual_files != expected_files:
        raise ValueError("bundle contains unregistered files; keep supplied inputs at their declared files/ paths")
    for run in manifest["runs"]:
        if any(name.startswith("experiments/") for name in run["input_hashes"]):
            raise ValueError("cross-run experiment-output inputs are unsupported; cannot reuse old upstream output")
        spec = _json(_file(bundle_root, "files/"+run["spec_path"]))
        if (spec.get("run_id") != run["source_run_id"] or spec.get("script") != run["script"]
                or spec.get("args", []) != run["args"] or spec.get("seed") != run["seed"]
                or spec.get("timeout_seconds", 1800) != run["timeout_seconds"]):
            raise ValueError("replay command differs from its frozen specification")
        if not run["script"].startswith("code/") or not run["script"].endswith(".py"):
            raise ValueError("replay may only execute frozen Python entrypoints under code/")
        _portable_args(run["args"])
    return manifest


def _current_environment(executable: str, temp: Path):
    program = ("import importlib.metadata,json,platform; "
               "print(json.dumps({'python':platform.python_version(),'packages':"
               "{d.metadata['Name']:d.version for d in importlib.metadata.distributions() if d.metadata['Name']}}))")
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
                   "TEMP": str(temp), "TMP": str(temp), "TMPDIR": str(temp)}
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    result = subprocess.run([executable, "-c", program], capture_output=True, text=True, encoding="utf-8",
                            timeout=30, env=environment, **spawn_options())
    if result.returncode:
        raise ValueError("selected Python environment could not be inspected")
    info = json.loads(result.stdout)
    info["packages"] = {re.sub(r"[-_.]+", "-", key).lower(): value for key, value in info["packages"].items()}
    return info, environment


def _compare(left, right, rule):
    a, b = (left if type(left) is list else [left]), (right if type(right) is list else [right])
    if not a or not b or not all(_finite(x) for x in a+b):
        raise ValueError("comparison needs finite numeric observations")
    if rule.get("kind") == "exact":
        return left == right
    if rule.get("kind") == "numeric":
        atol, rtol = rule.get("atol"), rule.get("rtol")
        if not _finite(atol) or not _finite(rtol) or atol < 0 or not 0 <= rtol < 1:
            raise ValueError("invalid frozen numerical comparison tolerances")
        return len(a) == len(b) and all(math.isclose(x, y, abs_tol=atol, rel_tol=rtol) for x, y in zip(a, b))
    raise ValueError("unsupported comparison rule; this replay release checks exact/numeric only")


def _execute(command, workspace, run_dir, environment, timeout):
    process, tree = popen_tree(command, cwd=workspace, env=environment, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **spawn_options())
    size = 0
    errors = []
    truncated = False
    with (run_dir/"stdout.log").open("xb") as log:
        def pump():
            nonlocal size, truncated
            try:
                while True:
                    chunk = process.stdout.read(8192)
                    if not chunk:
                        break
                    kept = chunk[:max(0, MAX_LOG_BYTES-size)]
                    log.write(kept)
                    log.flush()
                    size += len(kept)
                    truncated = truncated or len(kept) < len(chunk)
            except (OSError, ValueError) as exc:
                errors.append(str(exc))
        thread = threading.Thread(target=pump, daemon=True)
        thread.start()
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            tree.kill()
            process.wait(timeout=20)
            code = -1
            errors.append("replay timed out")
        thread.join(timeout=5)
        if thread.is_alive():
            errors.append("replay left a descendant holding its log stream")
            tree.kill()
            thread.join(timeout=5)
        tree.close()
        process.stdout.close()
        return code, errors, truncated


def run_replay(bundle_root: Path | str, output_root: Path | str,
               python_executable: Path | str | None = None) -> dict:
    report = {"schema_version": VERSION, "scope": "REPLAY_CONSISTENCY_ONLY_NO_PROJECT_APPROVAL",
              "status": "BLOCKED", "started_at_utc": _now(), "runs": [], "comparisons": [], "errors": []}
    created = False
    try:
        bundle_root = _plain(Path(bundle_root))
        output_root = _empty_destination(Path(output_root))
        if output_root.is_relative_to(bundle_root) or bundle_root.is_relative_to(output_root):
            raise ValueError("replay output and immutable bundle must use disjoint directories")
        output_root.mkdir(parents=True, exist_ok=True)
        created = True
        manifest = _check_bundle(bundle_root)
        report["bundle_sha256"] = manifest["bundle_sha256"]
        workspace, temp = output_root/"workspace", output_root/"temp"
        workspace.mkdir()
        temp.mkdir()
        for name, item in manifest["files"].items():
            target = workspace/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(_file(bundle_root, "files/"+name), target)
            if file_hash(target) != item["sha256"]:
                raise ValueError("bundle changed during workspace preparation")
        executable = str(python_executable or sys.executable)
        current, environment = _current_environment(executable, temp)
        report["environment"] = current
        for expected in manifest["environments"].values():
            if ".".join(current["python"].split(".")[:2]) != expected["python_major_minor"]:
                raise ValueError("selected Python major/minor differs from recorded environment")
            missing = [f"{name}=={version}" for name, version in expected["packages"].items() if current["packages"].get(name) != version]
            if missing:
                raise ValueError("missing or changed dependencies; no automatic installation: " + ", ".join(missing[:30]))
        outputs = {}
        for run in manifest["runs"]:
            run_id = run["source_run_id"]
            run_dir = output_root/"runs"/run_id
            run_dir.mkdir(parents=True)
            command = [executable, str(_file(workspace, run["script"])),
                       *[arg.replace("{run_dir}", str(run_dir)).replace("{seed}", str(run["seed"])) for arg in run["args"]]]
            receipt = {"schema_version": VERSION, "scope": "REPLAY_RUN_ONLY", "source_run_id": run_id,
                       "argv": command, "started_at_utc": _now(), "status": "FAILED", "errors": []}
            try:
                for name, item in manifest["files"].items():
                    if file_hash(_file(workspace, name)) != item["sha256"]:
                        raise ValueError(f"declared dependency changed before replay: {name}")
                exit_code, errors, truncated = _execute(command, workspace, run_dir, environment, run["timeout_seconds"])
                receipt.update(exit_code=exit_code, log_truncated=truncated)
                receipt["errors"].extend(errors)
                if exit_code:
                    receipt["errors"].append(f"process exited with code {exit_code}")
                for name, item in manifest["files"].items():
                    if file_hash(_file(workspace, name)) != item["sha256"]:
                        receipt["errors"].append(f"declared dependency changed during replay: {name}")
                if not receipt["errors"]:
                    metrics = _json(_file(run_dir, "metrics.json")).get("metrics")
                    if type(metrics) is not dict or not metrics:
                        raise ValueError("replay produced no metrics")
                    if any(not (_finite(value) or type(value) is list and value and all(_finite(x) for x in value)) for value in metrics.values()):
                        raise ValueError("replay produced non-finite or nonnumeric metrics")
                    outputs[run_id] = metrics
                    receipt["metrics_sha256"] = file_hash(run_dir/"metrics.json")
                    receipt["status"] = "SUCCEEDED"
            except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
                receipt["errors"].append(str(exc))
            receipt["finished_at_utc"] = _now()
            atomic_json(run_dir/"replay_receipt.json", receipt)
            report["runs"].append(receipt)
            report["errors"].extend(f"{run_id}: {error}" for error in receipt["errors"])
        for target in manifest["comparisons"]:
            comparison = {"result_id": target["result_id"], "source_run_id": target["source_run_id"],
                          "metric": target["metric"], "rule": target["rule"], "status": "BLOCKED"}
            try:
                actual = outputs[target["source_run_id"]][target["metric"]]
                comparison.update(actual=actual, expected=target["expected"])
                comparison["status"] = "PASS" if _compare(actual, target["expected"], target["rule"]) else "FAIL"
                if comparison["status"] == "FAIL":
                    report["errors"].append(f"{target['result_id']}/{target['source_run_id']}: numerical replay differs")
            except (ValueError, KeyError, TypeError) as exc:
                comparison["error"] = str(exc)
                report["errors"].append(f"{target['result_id']}: {exc}")
            report["comparisons"].append(comparison)
        _check_bundle(bundle_root)  # Executed scripts receive only the workspace copy.
        report["status"] = "PASS" if not report["errors"] else "FAILED"
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        report["errors"].append(str(exc))
    report["finished_at_utc"] = _now()
    if created:
        atomic_json(Path(output_root)/"replay_report.json", report)
    return report
