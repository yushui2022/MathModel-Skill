"""Deprecated migration shim for run_all (trae package).

See claude package docstring; this script only prints a migration hint.
"""
from __future__ import annotations

import sys


PREFLIGHT_COMMAND = "python .trae/skills/paper-workflow-orchestrator/scripts/preflight_check.py"
QUICKSTART_COMMAND = "python .trae/skills/paper-workflow-orchestrator/scripts/quickstart_run.py"


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def main() -> int:
    configure_utf8_stdio()
    print("[DEPRECATED] run_all.py 不再作为正式入口，本脚本不执行任何流程。")
    print()
    print("正式赛题请按以下顺序：")
    print("  1) 让 Agent 读取 .trae/skills/paper-workflow-orchestrator/SKILL.md")
    print("  2) 第一步先运行预检：")
    print(f"     {PREFLIGHT_COMMAND}")
    print("  3) 预检 PASS 后，按 SKILL.md 的阶段路由表逐步推进（不要直接跑 quickstart）。")
    print()
    print("如果你只是想验证安装 / 跑 smoke test，可以执行：")
    print(f"  {QUICKSTART_COMMAND}")
    print("（quickstart 产物写入 paper_output/quickstart/，不会污染 paper_output/final_paper.docx）")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
