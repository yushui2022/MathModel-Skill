from __future__ import annotations

import argparse
import importlib.metadata
import os
import platform
import subprocess
import sys
from pathlib import Path

from pro_checkpoint import require_checkpoints
from pro_contracts import contract, hash_paths, output_root, read_json, safe_path, sha256_file, utc_now, write_json


def refresh_manifest(root: Path) -> None:
    runs = []
    for path in sorted((root / "experiments").glob("*/receipt.json")):
        receipt = read_json(path)
        runs.append({"run_id": receipt["run_id"], "receipt_path": path.relative_to(root).as_posix(), "receipt_sha256": sha256_file(path)})
    write_json(root / "experiment_manifest.json", contract(
        producer_role="pro-experiment-runner", status="PASS", runs=runs,
        input_hashes={r["receipt_path"]: r["receipt_sha256"] for r in runs},
    ))


def execute(project: Path, spec_path: Path) -> tuple[Path, bool]:
    root = output_root(project)
    errors = require_checkpoints(project, root, 2)
    if errors:
        raise ValueError("; ".join(errors))
    spec_path = spec_path.resolve()
    if not spec_path.is_relative_to((root / "code").resolve()):
        raise ValueError("run specification must be under code/")
    spec_hash = sha256_file(spec_path)
    spec = read_json(spec_path)
    run_id = spec.get("run_id", "")
    if not isinstance(run_id, str) or not run_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in run_id):
        raise ValueError("run_id must be a simple unique identifier")
    directory = safe_path(root, "experiments/" + run_id)
    if directory.exists():
        raise ValueError("run_id already exists; retain previous runs and use a new ID")
    script = safe_path(root, spec.get("script", ""))
    if not script.is_relative_to((root / "code").resolve()) or script.suffix != ".py":
        raise ValueError("experiment entrypoint must be a Python file under code/")
    if not spec.get("route_id") or not spec.get("implementation_id"):
        raise ValueError("route_id and implementation_id are required")
    routes = {r["route_id"] for p in read_json(root / "candidate_routes.json")["subproblems"] for r in p["routes"]}
    if spec["route_id"] not in routes:
        raise ValueError("run route is not in the approved tournament")
    seed = spec.get("seed")
    if spec.get("stochastic") is True and type(seed) is not int:
        raise ValueError("stochastic runs require a recorded integer seed")
    inputs = [safe_path(root, p) for p in spec.get("inputs", [])]
    scripts = [script, *[safe_path(root, p) for p in spec.get("dependencies", [])]]
    if not inputs or any(not p.is_file() for p in [*inputs, *scripts]):
        raise ValueError("all declared scripts and non-empty inputs must exist")
    argv_tail = spec.get("args", [])
    if not isinstance(argv_tail, list) or any(not isinstance(a, str) for a in argv_tail):
        raise ValueError("args must be strings; shell command strings are not accepted")
    timeout = spec.get("timeout_seconds", 1800)
    if type(timeout) is not int or timeout <= 0:
        raise ValueError("timeout_seconds must be a positive per-process watchdog")
    directory.mkdir(parents=True)
    metrics_path = directory / "metrics.json"
    argv = [sys.executable, str(script), *[a.replace("{run_dir}", str(directory)).replace("{seed}", str(seed)) for a in argv_tail]]
    before_scripts, before_inputs = hash_paths(scripts, root), hash_paths(inputs, root)
    started = utc_now()
    environment = {
        "python": sys.version, "executable": sys.executable, "platform": platform.platform(),
        "packages": sorted({f"{d.metadata['Name']}=={d.version}" for d in importlib.metadata.distributions() if d.metadata['Name']}),
    }
    child_env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}
    failure = ""
    with (directory / "stdout.log").open("w", encoding="utf-8") as stdout, (directory / "stderr.log").open("w", encoding="utf-8") as stderr:
        try:
            completed = subprocess.run(argv, cwd=root, env=child_env, stdout=stdout, stderr=stderr, timeout=timeout, check=False)
            exit_code = completed.returncode
            if exit_code:
                failure = f"process exited with code {exit_code}"
        except (subprocess.TimeoutExpired, OSError) as exc:
            exit_code, failure = -1, str(exc)
    try:
        if hash_paths(scripts, root) != before_scripts or hash_paths(inputs, root) != before_inputs or sha256_file(spec_path) != spec_hash:
            failure = "scripts, inputs or run specification changed during execution"
    except OSError:
        failure = "scripts, inputs or run specification removed during execution"
    if not failure:
        try:
            from pro_validation import finite
            metrics = read_json(metrics_path).get("metrics", {})
            if not metrics or any(not (finite(v) or isinstance(v, list) and v and all(finite(x) for x in v)) for v in metrics.values()):
                failure = "missing, empty or nonnumeric metrics"
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            failure = str(exc)
    paths = [p for p in directory.rglob("*") if p.is_file()]
    outputs = hash_paths(paths, root)
    receipt = contract(
        producer_role="pro-experiment-runner", status="FAILED" if failure else "PASS",
        input_hashes=before_inputs, script_hashes=before_scripts, output_hashes=outputs,
        run_id=run_id, route_id=spec["route_id"], implementation_id=spec["implementation_id"],
        argv=argv, cwd="paper_output_pro", environment=environment, seed=seed,
        stochastic=spec.get("stochastic") is True, exit_code=exit_code,
        started_at_utc=started, finished_at_utc=utc_now(), failure_reason=failure or None,
        metrics_file=metrics_path.relative_to(root).as_posix(),
        spec_path=spec_path.relative_to(root).as_posix(), spec_sha256=spec_hash,
    )
    receipt_path = directory / "receipt.json"
    write_json(receipt_path, receipt)
    return receipt_path, not failure


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute a Pro experiment and record actual outputs.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--spec", help="Run specification relative to paper_output_pro/")
    parser.add_argument("--refresh-manifest", action="store_true", help="Run after a parallel batch has fully completed")
    args = parser.parse_args()
    project = args.project_root.resolve()
    root = output_root(project)
    try:
        if args.refresh_manifest:
            refresh_manifest(root)
            print("[PASS] Collected all execution receipts")
            return 0
        if not args.spec:
            parser.error("--spec is required")
        path, passed = execute(project, safe_path(root, args.spec))
        print(f"[{'PASS' if passed else 'FAILED'}] {path}")
        return 0 if passed else 1
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(f"[BLOCKED] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
