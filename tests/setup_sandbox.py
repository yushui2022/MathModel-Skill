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
        "\n".join(
            [
                "# 摘要",
                "",
                "本文用于测试正式论文导出链路。关键词：测试；模型；证据链。",
                "",
                "# 1 问题重述",
                "",
                "本节说明问题背景、输入附件和需要完成的建模任务。",
                "",
                "# 2 问题分析",
                "",
                "本节分析数据字段、约束条件和评价目标。",
                "",
                "# 3 模型假设",
                "",
                "假设一：测试数据已经完成基础清洗。假设二：模型结果来自实际运行代码。",
                "",
                "# 4 符号说明",
                "",
                "$$",
                "x_i = i",
                "$$",
                "",
                "# 5 模型的建立与求解",
                "",
                "根据数据计划建立基线模型，并用运行结果支撑正文结论。",
                "",
                "# 6 模型检验与灵敏度分析",
                "",
                "通过误差指标和参数扰动检查模型稳定性。",
                "",
                "# 7 模型评价与推广",
                "",
                "说明模型优点、局限和可推广场景。",
                "",
                "# 参考文献",
                "",
                "[1] 测试文献。",
                "",
                "# 附录",
                "",
                "附录给出关键代码和复核说明。",
                "",
            ]
        ),
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
