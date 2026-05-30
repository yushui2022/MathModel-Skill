"""Rebuild the preflight / format-gate test sandbox under tests/sandbox/.

Run from the repo root:
    python tests/setup_sandbox.py

This creates scenario_1..5 with the exact inputs used in REVIEW_REPORT.md,
plus optional format-gate fixtures. The sandbox directory itself is gitignored
(see tests/.gitignore); only this script is committed so the run is reproducible.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import openpyxl


# Minimal valid single-page PDF (hand-rolled; ~700 bytes). Used as a fixture so
# scenario_6_no_pypdf can be built without importing pypdf — that way the
# missing-pypdf simulation does not require pypdf at setup time.
MINIMAL_PDF_BYTES = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]/Resources<<>>>>endobj\n"
    b"xref\n0 4\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000052 00000 n \n"
    b"0000000098 00000 n \n"
    b"trailer<</Size 4/Root 1 0 R>>\n"
    b"startxref\n167\n%%EOF\n"
)


REPO_ROOT = Path(__file__).resolve().parent.parent
SANDBOX = REPO_ROOT / "tests" / "sandbox"


def reset_sandbox() -> None:
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX, ignore_errors=True)
    SANDBOX.mkdir(parents=True, exist_ok=True)


def make_scenario(name: str) -> Path:
    d = SANDBOX / name / "problem_files"
    d.mkdir(parents=True, exist_ok=True)
    return d


def main() -> int:
    reset_sandbox()

    # 1: empty problem_files/
    make_scenario("scenario_1_empty")

    # 2: only a .doc file (legacy, not extractable)
    pf = make_scenario("scenario_2_only_doc")
    (pf / "题目.doc").write_bytes(b"")

    # 3: broken xlsx + a real .md problem statement
    pf = make_scenario("scenario_3_broken_xlsx")
    (pf / "broken.xlsx").write_text("not a real xlsx", encoding="utf-8")
    (pf / "题目.md").write_text("## 题目说明\n\n这是测试题面。", encoding="utf-8")

    # 4: suspicious result template (result*.xlsx) + a real .txt problem statement
    pf = make_scenario("scenario_4_suspicious_template")
    wb = openpyxl.Workbook()
    wb.active["A1"] = "填空"
    wb.save(pf / "result1.xlsx")
    (pf / "题目.txt").write_text("题面正文", encoding="utf-8")

    # 5: stale paper_output/final_paper.docx + a real .md problem statement
    pf = make_scenario("scenario_5_stale_output")
    (pf / "题目.md").write_text("## 题面\n\n正文。", encoding="utf-8")
    stale_dir = SANDBOX / "scenario_5_stale_output" / "paper_output"
    stale_dir.mkdir(parents=True, exist_ok=True)
    openpyxl.Workbook().save(stale_dir / "final_paper.docx")  # any docx-shaped blob

    # 6: valid PDF — used together with a runtime import-blocker to verify
    # missing-pypdf behavior. The PDF is a minimal hand-rolled fixture so
    # setup itself does not depend on pypdf.
    pf = make_scenario("scenario_6_no_pypdf")
    (pf / "题目.pdf").write_bytes(MINIMAL_PDF_BYTES)

    # Format-gate fixtures: use scenario_4 because preflight passes there.
    fmt_root = SANDBOX / "scenario_4_suspicious_template" / "paper_output"
    fmt_root.mkdir(parents=True, exist_ok=True)
    (fmt_root / "final_paper_source.md").write_text(
        "# 测试论文\n\n## 1 摘要\n\n这是 format gate 测试用的最小 Markdown。\n",
        encoding="utf-8",
    )

    print(f"sandbox rebuilt at {SANDBOX.relative_to(REPO_ROOT).as_posix()}")
    print("scenarios:")
    for child in sorted(SANDBOX.iterdir()):
        if child.is_dir():
            print(f"  - {child.name}")
    print()
    print("Run preflight per scenario, e.g.:")
    print("  cd tests/sandbox/scenario_1_empty")
    print("  python ../../../packages/claude/.claude/skills/paper-workflow-orchestrator/scripts/preflight_check.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
