"""Validate the single portable payload, without generating platform copies."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "skills"
sys.path.insert(0, str(PAYLOAD / "pro-workflow-orchestrator/scripts"))
from installation import ENTRY, SKILLS, files_under


def check() -> list[str]:
    errors = []
    if sorted(p.name for p in PAYLOAD.iterdir() if p.is_dir()) != list(SKILLS):
        errors.append("Skill set differs from declared edition modules")
    marker = json.loads((PAYLOAD / ENTRY / "MATHMODEL_EDITION.json").read_text(encoding="utf-8"))
    if marker.get("version") != (ROOT / "VERSION").read_text(encoding="utf-8").strip():
        errors.append("Edition marker and VERSION differ")
    actual_files = sorted(files_under(PAYLOAD))
    required = sorted(p for p in actual_files if p != f"{ENTRY}/MATHMODEL_EDITION.json")
    if sorted(marker.get("required_files", [])) != required:
        errors.append("Edition marker required_files differs from payload file list")
    for skill in SKILLS:
        entry = PAYLOAD / skill / "SKILL.md"
        text = entry.read_text(encoding="utf-8")
        if not text.startswith("---\n") or not re.search(rf'''(?m)^name: ["']?{re.escape(skill)}["']?$''', text) or not re.search(r"(?m)^description: \S", text):
            errors.append(f"Invalid Skill frontmatter: {skill}")
    for name, path in files_under(PAYLOAD).items():
        if path.suffix not in {".py", ".md"}:
            continue
        text = path.read_text(encoding="utf-8")
        if path.name != "installation.py" and re.search(r"\.(?:claude|codex|agents|trae)/skills", text):
            errors.append(f"Hardcoded host path: {name}")
        if path.suffix != ".md":
            continue
        prose = re.sub(r"```.*?```", "", text, flags=re.S)
        prose = re.sub(r"`[^`]*`", "", prose)
        for target in re.findall(r"\]\(([^)]+)\)", prose):
            if "://" in target or target.startswith(("#", "mailto:", "<")):
                continue
            target = target.split("#")[0]
            if target and not (path.parent / target).exists():
                errors.append(f"Broken local reference in {name}: {target}")
        for relative in re.findall(r"<SKILL_ROOT>/([a-zA-Z0-9_./-]+)", text):
            if not (PAYLOAD / relative).exists():
                errors.append(f"Missing command/resource in {name}: {relative}")
    return errors


if __name__ == "__main__":
    failures = check()
    for failure in failures:
        print("[FAIL] " + failure)
    if not failures:
        print("[PASS] Portable Skill payload, version and local references")
    raise SystemExit(bool(failures))
