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
EXPECTED_EDITION = "lite"
SKILL_ROOTS = ("skills", ".agents/skills", ".codex/skills", ".claude/skills", ".trae/skills")
LEGACY_ENTRY_EDITIONS = {
    "paper-workflow-orchestrator": "standard",
    "mathmodel-lite": "lite",
    "pro-workflow-orchestrator": "pro",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def detect_mathmodel_installations() -> list[dict[str, str | None]]:
    installations: list[dict[str, str | None]] = []
    for root_text in SKILL_ROOTS:
        skills_root = ROOT / Path(root_text)
        if not skills_root.is_dir():
            continue
        for skill_dir in sorted(path for path in skills_root.iterdir() if path.is_dir()):
            marker_path = skill_dir / "MATHMODEL_EDITION.json"
            marker: dict[str, object] = {}
            marker_error: str | None = None
            if marker_path.is_file():
                try:
                    value = json.loads(marker_path.read_text(encoding="utf-8"))
                    marker = value if isinstance(value, dict) else {}
                    if marker.get("product") not in (None, "", "MathModel-Skill"):
                        continue
                except Exception as exc:
                    marker_error = f"{type(exc).__name__}: {exc}"
            legacy_edition = LEGACY_ENTRY_EDITIONS.get(skill_dir.name)
            edition = str(marker.get("edition") or legacy_edition or "").strip().lower()
            if edition not in {"standard", "lite", "pro"}:
                continue
            installations.append({
                "edition": edition,
                "version": str(marker.get("version") or "legacy-unmarked"),
                "entry_skill": str(marker.get("entry_skill") or skill_dir.name),
                "skill_root": root_text,
                "path": rel(skill_dir),
                "marker": rel(marker_path) if marker_path.is_file() else None,
                "marker_error": marker_error,
            })
    return installations


def main() -> int:
    from lite_common import configure_stdio
    configure_stdio()
    from lite_common import safe_path
    try:
        safe_path(ROOT, "paper_output_lite")
        safe_path(ROOT, "problem_files")
    except ValueError as exc:
        print(f"[FAIL] {exc}")
        return 1
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for name in ("code", "figures", "tables"):
        (OUTPUT_DIR / name).mkdir(parents=True, exist_ok=True)

    files = sorted(path for path in INPUT_DIR.rglob("*") if path.is_file()) if INPUT_DIR.exists() else []
    failures: list[str] = []
    warnings: list[str] = []
    installations = detect_mathmodel_installations()
    editions = sorted({str(item["edition"]) for item in installations})
    if len(editions) > 1:
        failures.append(f"检测到 MathModel Skill 混装：{', '.join(editions)}。一个项目只能安装一个版本。")
    elif editions and editions != [EXPECTED_EDITION]:
        failures.append(f"当前入口是 Lite，但项目中检测到 {editions[0]} 安装。请移除其他版本后重试。")
    for item in installations:
        if item.get("marker_error"):
            failures.append(f"Edition marker 无法读取：{item['marker']} ({item['marker_error']})")
    versions = sorted({str(item["version"]) for item in installations if item["edition"] == EXPECTED_EDITION})
    if len(versions) > 1:
        warnings.append(f"检测到多个 Lite 安装版本：{', '.join(versions)}。建议只保留当前版本。")
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
        "warnings": warnings,
        "mathmodel_installation": {
            "expected_edition": EXPECTED_EDITION,
            "detected_editions": editions,
            "installations": installations,
        },
        "files": entries,
    }
    MANIFEST_FILE.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Lite input manifest: {rel(MANIFEST_FILE)}")
    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1
    for warning in warnings:
        print(f"[WARNING] {warning}")
    print(f"[PASS] Recorded {len(entries)} input files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
