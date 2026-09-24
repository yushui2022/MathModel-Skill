# MathModel Skill Flash for Claude Code

Flash 是速度优先的独立版本，适合 DeepSeek、Gemini、GLM 等 Flash 类高吞吐模型。它通过一个 `mathmodel-flash` 入口，快速完成真实实验、图表、结果和约 18–22 页目标的基础 Word 长文草稿。

版本分支：

| 版本 | 分支 | 作用 |
|---|---|---|
| Flash | [flash](https://github.com/yushui2022/MathModel-Skill/tree/flash) | 快速长文草稿，真实运行但不做严格终稿门禁 |
| Lite | [lite](https://github.com/yushui2022/MathModel-Skill/tree/lite) | 普通或较旧模型的低负担基础报告 |
| Standard | [standard](https://github.com/yushui2022/MathModel-Skill/tree/standard) | 正式竞赛论文与证据、Word/PDF 检查 |
| Pro | [pro](https://github.com/yushui2022/MathModel-Skill/tree/pro) | 高计算投入的模型竞赛、复算和审稿；预发布 |
| LaTeX | [Latex](https://github.com/yushui2022/MathModel-Skill/tree/Latex) | 独立实验性 TeX/PDF 旧流程 |

**一个项目只安装一个版本、一个平台包，不要混装。** Flash 输出在 `paper_output_flash/`，不能读取 Standard、Lite 或 Pro 的旧结果。Flash PASS 只表示基础运行和文档检查通过；正式提交前请转用 Standard 或 Pro 复核。

将本目录的 `.claude/skills/` 解压到项目根目录，保留已有 `CLAUDE.md`。使用 Python 3.11 或 3.12，安装包内 `requirements.txt` 后，把赛题和附件放进 `problem_files/`，然后发送：

```text
请使用 $mathmodel-flash。按预检、计划、真实实验、长文写作、Word 检查的固定流程完成，所有产物写入 paper_output_flash/。只有 flash_report.json 为 PASS 才交付 paper.docx。
```

详见仓库根目录 README 和 `docs/flash-starter-prompt.md`。
