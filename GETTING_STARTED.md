# Getting Started with MathModel Skill Flash

Flash 是速度优先的独立版本，适合 DeepSeek、Gemini、GLM 等 Flash 类高吞吐模型。

1. 从 [Flash 分支](https://github.com/yushui2022/MathModel-Skill/tree/flash) 的 `dist/` 下载对应平台的 `MathModel-Skill-Flash-*.zip`。
2. 只在一个未安装 Standard、Lite、Pro 或 LaTeX 的项目根目录解压一个平台包。
3. 创建 `problem_files/`，放入赛题和附件。
4. 使用 Python 3.11 或 3.12，运行 `python -m pip install -r requirements.txt` 和 `python -m pip check`。
5. 让 Agent 使用 `$mathmodel-flash`，严格执行预检、计划、真实实验、长文写作和 Word 检查。
6. 只有 `paper_output_flash/flash_report.json` 为 `PASS` 时，才把 `paper.docx` 作为 Flash 基础长文交付物。

Flash 的目标是约 18–22 页的有内容基础稿，不提供 Standard 的严格证据链或 Pro 的高强度复算审稿。完整的版本选择、社媒入口和原理说明见 [README](README.md)。
