# MathModel Skill Lite for Claude Code

这是面向较弱或较旧模型的低上下文版本，只包含一个 `mathmodel-lite` Skill 和三个固定脚本。

只在没有安装 Standard 的项目中，将 `CLAUDE.md` 与 `.claude/skills/` 复制到项目根目录。不要同时保留 Standard 的 `paper-workflow-orchestrator`。把赛题放进 `problem_files/`，然后说：

```text
请使用 MathModel Lite，严格按固定六步完成，并在 lite_report.json 为 PASS 后交付 paper.docx。
```

Lite 输出位于 `paper_output_lite/`。它保留输入哈希、真实代码运行、输出哈希和占位检查，但不提供 Standard 的多 Skill 路由、原生 Word 公式、严格引文和 PDF 渲染 QA。
