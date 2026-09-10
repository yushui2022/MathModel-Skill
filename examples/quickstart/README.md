# Quickstart 工程冒烟样例

这是仓库保留的历史 Standard 样例，用最小输入检查 Standard 平台包的安装、基础解析、契约、脚手架生成和 Word 导出链路。它不是真实竞赛流程，也不能作为当前 Pro 插件 P0–P9 流程或论文质量验收的成果。

项目与版本说明见[主 README](../../README.md)，当前 Codex 插件的安装与使用见[插件 README](../../plugins/mathmodel/README.md)。当前插件可以恢复、展示实际新项目中已记录的题意、路线、运行与证据；Pro 新项目使用 `paper_output_pro/`。本样例保留 Standard 的 `paper_output/` 产物根，旧样例的产物和批准不会自动迁移为 Pro 批准或验收结果。

## 运行历史 Standard 样例

将 `problem_files/` 复制到已放入一个 Standard 平台包的临时项目目录中，然后按对应平台运行。以下命令保留原有 Standard 契约，不是当前 Pro 插件的启动命令。

```bash
# Codex
python .agents/skills/paper-workflow-orchestrator/scripts/quickstart_run.py

# Claude Code
python .claude/skills/paper-workflow-orchestrator/scripts/quickstart_run.py

# Trae
python .trae/skills/paper-workflow-orchestrator/scripts/quickstart_run.py
```

## 预期产物

Quickstart 可能生成用于冒烟检查的输入、计划、结果契约和历史任务产物。所有论文类草稿必须保存在：

```text
paper_output/quickstart/
```

不得生成正式稿 `paper_output/final_paper_source.md` 或 `paper_output/final_paper.docx`。

如果仍使用历史 Standard 2.2 平台包处理真实赛题，应调用 `$paper-workflow-orchestrator`，完成正式 S6 证据验证、Standard 2.2 自适应 S7 写作及要求的 S8 渲染 QA。使用当前 Codex 插件开展新赛题时，请按[插件 README](../../plugins/mathmodel/README.md)进入 Pro 流程，并基于该项目的实际输入、确认和证据推进。
