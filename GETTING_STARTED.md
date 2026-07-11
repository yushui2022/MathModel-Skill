# Getting Started with MathModel Lite

1. 下载与你平台对应的 `MathModel-Skill-Lite-*.zip`。
2. 解压到一个未安装 MathModel Standard 的项目根目录。
3. 创建 `problem_files/`，放入赛题和附件。
4. 运行 `pip install -r requirements.txt`。
5. 让 Agent 读取 `mathmodel-lite/SKILL.md` 并严格执行固定六步。
6. 只有 `paper_output_lite/lite_report.json` 为 `PASS` 时才使用 `paper.docx`。

完整说明见 [README](README.md) 和 [Lite Workflow](docs/lite-workflow.md)。
