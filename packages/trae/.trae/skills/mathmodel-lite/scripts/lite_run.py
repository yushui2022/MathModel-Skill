from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path.cwd()
OUTPUT_DIR = ROOT / "paper_output_lite"
MANIFEST_FILE = OUTPUT_DIR / "input_manifest.json"
MODEL_FILE = OUTPUT_DIR / "code" / "model.py"
RESULTS_FILE = OUTPUT_DIR / "results.json"
RUN_FILE = OUTPUT_DIR / "run_manifest.json"


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
    path = Path(str(path_text or ""))
    return path if path.is_absolute() else ROOT / path


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def input_failures(manifest: Any) -> list[str]:
    if not isinstance(manifest, dict) or manifest.get("status") != "PASS":
        return ["缺少通过的 input_manifest.json；请先运行 lite_preflight.py。"]
    failures: list[str] = []
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
    return [
        {"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for path in sorted(set(paths))
    ]


def write_run(status: str, failures: list[str], completed: subprocess.CompletedProcess[str] | None) -> None:
    manifest = load_json(MANIFEST_FILE)
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
        "outputs": output_records(),
    }
    RUN_FILE.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    failures = input_failures(load_json(MANIFEST_FILE))
    if not MODEL_FILE.exists() or MODEL_FILE.stat().st_size == 0:
        failures.append("缺少非空建模脚本：paper_output_lite/code/model.py")
    if failures:
        write_run("FAIL", failures, None)
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1

    completed = subprocess.run(
        [sys.executable, str(MODEL_FILE)],
        cwd=str(ROOT),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        failures.append(f"model.py 运行失败，退出码 {completed.returncode}。")
    if not RESULTS_FILE.exists() or RESULTS_FILE.stat().st_size == 0:
        failures.append("model.py 未生成非空 paper_output_lite/results.json。")
    elif not isinstance(load_json(RESULTS_FILE), dict):
        failures.append("results.json 不是有效 JSON 对象。")

    status = "PASS" if not failures else "FAIL"
    write_run(status, failures, completed)
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

