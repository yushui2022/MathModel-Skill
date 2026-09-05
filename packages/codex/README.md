# MathModel Skill Lite for Codex

这是面向较弱或较旧模型的低上下文版本，只包含一个 `mathmodel-lite` Skill 和三个固定脚本。

只在没有安装 Standard 或 Pro 的项目中，解压 Lite Codex 包的 `.agents/skills/`。从源码安装时，将本目录的 `skills/mathmodel-lite` 放到项目的 `.agents/skills/mathmodel-lite`。保留用户已有 `AGENTS.md`，不要复制仓库里的历史入口文件。把赛题放进 `problem_files/`，然后说：

```text
请使用 MathModel Lite，严格按固定六步完成，并在 lite_report.json 为 PASS 后交付 paper.docx。
```

Lite 输出位于 `paper_output_lite/`。它保留输入哈希、真实代码运行、输出哈希和占位检查，但不提供 Standard 的多 Skill 路由、原生 Word 公式、严格引文和 PDF 渲染 QA。
