from __future__ import annotations

import hashlib
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from lite_common import safe_path, configure_stdio


ROOT = Path.cwd()
OUTPUT_DIR = ROOT / "paper_output_lite"
MANIFEST_FILE = OUTPUT_DIR / "input_manifest.json"
MODEL_FILE = OUTPUT_DIR / "code" / "model.py"
RESULTS_FILE = OUTPUT_DIR / "results.json"
RUN_FILE = OUTPUT_DIR / "run_manifest.json"
PLAN_FILE = OUTPUT_DIR / "plan.json"


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve(path_text: object) -> Path:
    return safe_path(ROOT, path_text)


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def input_failures(manifest: Any) -> list[str]:
    if not isinstance(manifest, dict) or manifest.get("status") != "PASS":
        return ["缺少通过的 input_manifest.json；请先运行 lite_preflight.py。"]
    failures: list[str] = []
    if not isinstance(manifest.get("files"), list) or not manifest["files"]:
        return ["input manifest has no file records"]
    expected = {entry.get("path") for entry in manifest["files"] if isinstance(entry, dict)}
    actual = {rel(p) for p in (ROOT / "problem_files").rglob("*") if p.is_file()}
    if expected != actual:
        failures.append("input files were added or removed; rerun preflight")
    for entry in manifest.get("files", []):
        path = resolve(entry.get("path"))
        if not path.exists():
            failures.append(f"输入文件缺失：{rel(path)}")
            continue
        if path.stat().st_size != entry.get("bytes") or sha256_file(path) != entry.get("sha256"):
            failures.append(f"输入文件已变化，请重新预检：{rel(path)}")
    return failures


def output_records() -> list[dict[str, object]]:
    paths: list[Path] = []
    if RESULTS_FILE.exists():
        paths.append(RESULTS_FILE)
    for folder in (OUTPUT_DIR / "figures", OUTPUT_DIR / "tables"):
        if folder.exists():
            paths.extend(path for path in folder.rglob("*") if path.is_file())
    for path in paths:
        safe_path(ROOT, path.relative_to(ROOT).as_posix())
    return [
        {"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for path in sorted(set(paths))
    ]


def write_run(status: str, failures: list[str], completed: subprocess.CompletedProcess[str] | None, initial: dict | None = None) -> None:
    manifest = load_json(MANIFEST_FILE)
    outputs = []
    if status == "PASS":
        try:
            outputs = output_records()
        except (ValueError, OSError) as exc:
            failures.append(f"unsafe output: {exc}")
            status = "FAIL"
    run = {
        "schema_version": "1.0",
        "generated_by": "mathmodel-lite/scripts/lite_run.py",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "failures": failures,
        "command": [sys.executable, rel(MODEL_FILE)],
        "returncode": completed.returncode if completed else None,
        "stdout": (completed.stdout or "")[-4000:] if completed else "",
        "stderr": (completed.stderr or "")[-4000:] if completed else "",
        "script": rel(MODEL_FILE),
        "script_sha256": sha256_file(MODEL_FILE) if MODEL_FILE.exists() else "",
        "inputs": manifest.get("files", []) if isinstance(manifest, dict) else [],
        "outputs": outputs,
        "initial_hashes": initial or {},
    }
    RUN_FILE.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser(description="Execute a Lite model with a configurable watchdog.")
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    if args.timeout < 1:
        parser.error("timeout must be positive")
    try:
        safe_path(ROOT, "paper_output_lite")
        for name in (MANIFEST_FILE, MODEL_FILE, RESULTS_FILE, PLAN_FILE, RUN_FILE):
            safe_path(ROOT, name.relative_to(ROOT).as_posix())
        failures = input_failures(load_json(MANIFEST_FILE))
    except (ValueError, TypeError, AttributeError, OSError) as exc:
        print(f"[FAIL] {exc}")
        return 1
    if not isinstance(load_json(PLAN_FILE), dict):
        failures.append("missing plan.json; plan must be recorded before computation")
    if not MODEL_FILE.exists() or MODEL_FILE.stat().st_size == 0:
        failures.append("缺少非空建模脚本：paper_output_lite/code/model.py")
    if failures:
        write_run("FAIL", failures, None)
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1

    initial = {rel(p): sha256_file(p) for p in (MODEL_FILE, PLAN_FILE, MANIFEST_FILE)}
    # A no-op run must not reuse a previous successful results.json.
    if RESULTS_FILE.exists():
        RESULTS_FILE.unlink()
    write_run("RUNNING", [], None, initial)
    try:
        completed = subprocess.run(
            [sys.executable, str(MODEL_FILE)],
            cwd=str(ROOT),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
            check=False, timeout=args.timeout,
        )
    except subprocess.TimeoutExpired:
        write_run("FAIL", [f"model exceeded {args.timeout} seconds; inspect or explicitly raise --timeout"], None, initial)
        return 1
    for name, expected in initial.items():
        if not resolve(name).is_file() or sha256_file(resolve(name)) != expected:
            failures.append(f"input/plan/script changed during execution: {name}")
    failures.extend(input_failures(load_json(MANIFEST_FILE)))
    if completed.returncode != 0:
        failures.append(f"model.py 运行失败，退出码 {completed.returncode}。")
    if not RESULTS_FILE.exists() or RESULTS_FILE.stat().st_size == 0:
        failures.append("model.py 未生成非空 paper_output_lite/results.json。")
    elif not isinstance(load_json(RESULTS_FILE), dict):
        failures.append("results.json 不是有效 JSON 对象。")

    status = "PASS" if not failures else "FAIL"
    try:
        write_run(status, failures, completed, initial)
    except (ValueError, OSError) as exc:
        print(f"[FAIL] unsafe or invalid output: {exc}")
        return 1
    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        if completed.stderr:
            print(completed.stderr[-2000:])
        return 1
    print("[PASS] Lite model run recorded with input, script and output hashes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

