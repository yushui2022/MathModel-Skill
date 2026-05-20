QUICKSTART_COMMAND = "python .trae/skills/paper-workflow-orchestrator/scripts/quickstart_run.py"


def main() -> int:
    print("run_all.py 已废弃，不再作为正式论文生成入口。")
    print("正式使用 MathModel Skill 时，请先读取 paper-workflow-orchestrator/SKILL.md。")
    print("由 Agent 按当前赛题完成题意解析、专用代码、真实结果、证据门禁和全局写作。")
    print()
    print("如果只是验证安装或跑 quickstart smoke test，请改用：")
    print(f"  {QUICKSTART_COMMAND}")
    print()
    print("本脚本没有执行任何生成流程。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
