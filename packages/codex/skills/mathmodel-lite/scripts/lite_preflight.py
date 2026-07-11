from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path.cwd()
INPUT_DIR = ROOT / "problem_files"
OUTPUT_DIR = ROOT / "paper_output_lite"
MANIFEST_FILE = OUTPUT_DIR / "input_manifest.json"
STANDARD_ENTRIES = (
    ROOT / "skills" / "paper-workflow-orchestrator" / "SKILL.md",
    ROOT / ".claude" / "skills" / "paper-workflow-orchestrator" / "SKILL.md",
    ROOT / ".trae" / "skills" / "paper-workflow-orchestrator" / "SKILL.md",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for name in ("code", "figures", "tables"):
        (OUTPUT_DIR / name).mkdir(parents=True, exist_ok=True)

    files = sorted(path for path in INPUT_DIR.rglob("*") if path.is_file()) if INPUT_DIR.exists() else []
    failures: list[str] = []
    mixed_entries = [path for path in STANDARD_ENTRIES if path.exists()]
    if mixed_entries:
        failures.append(
            "检测到 Standard 的 paper-workflow-orchestrator；Lite 与 Standard 不得混装。"
        )
    if not files:
        failures.append("problem_files/ 为空；请先放入赛题和附件。")

    entries = [
        {
            "path": rel(path),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in files
    ]
    manifest = {
        "schema_version": "1.0",
        "generated_by": "mathmodel-lite/scripts/lite_preflight.py",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "files": entries,
    }
    MANIFEST_FILE.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Lite input manifest: {rel(MANIFEST_FILE)}")
    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1
    print(f"[PASS] Recorded {len(entries)} input files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
