"""Synchronize only maintained LaTeX hotfix files; leave legacy payloads alone."""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "packages/claude/.claude/skills"
FILES = [
    "paper-formal-writer/scripts/latex_integrity.py",
    "paper-formal-writer/scripts/format_formal_latex.py",
    "paper-formal-writer/scripts/check_latex_format.py",
    "paper-formal-writer/SKILL.md",
    "quality-assurance-auditor/scripts/evidence_gate.py",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    failures = []
    for folder, prefix in (("codex/skills", "skills"), ("trae/.trae/skills", ".trae/skills")):
        for name in FILES:
            text = (SOURCE / name).read_text(encoding="utf-8")
            if name.endswith(".md"):
                text = text.replace(".claude/skills", prefix)
            target = ROOT / "packages" / folder / name
            if args.check:
                if not target.exists() or target.read_text(encoding="utf-8") != text:
                    failures.append(str(target))
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8", newline="\n")
    if failures:
        raise SystemExit("Hotfix drift: " + ", ".join(failures))
    print("LaTeX hotfix payloads synchronized.")


if __name__ == "__main__":
    main()
