---
name: "mathmodel-flash"
description: "速度优先的数学建模长文工作流。Use when 用户明确选择 Flash，或使用 DeepSeek、Gemini、GLM 等高吞吐 Flash 类模型，希望快速完成真实实验并生成约 20 页的基础竞赛论文草稿。不要在用户要求 Standard/Pro 的严格证据链、独立复算、原生 Word 公式或 PDF 排版验收时使用。"
---

# MathModel Flash

Flash 是独立的快速版本。它把模型输出速度和长文初稿完成度放在第一位，适合快速得到一份包含实验、图表、结果和 Word 文件的基础论文草稿。它不是 Standard 或 Pro 的质量替代品，也不保证直接满足正式竞赛终稿要求。

## 适用边界

- 适合高吞吐 Flash 类模型、时间紧、先要完整基础稿再人工打磨的场景。
- 目标是约 18–22 页的基础长文，页数是排版目标，不允许用重复段落或无意义空白凑页数。
- 不做 Pro 的多路线模型竞赛、独立双路径复算、五角色审稿和用户确认点。
- 不做 Standard 的原生 Word OMML 公式、严格引用审计或 LibreOffice PDF 最终门禁。
- 与 Standard、Lite、Pro、LaTeX 不得混装；预检发现其他 MathModel 版本时停止。

## 固定目录

只读取 `problem_files/`，只写入 `paper_output_flash/`：

```text
paper_output_flash/
├── input_manifest.json
├── plan.json
├── code/model.py
├── run_manifest.json
├── results.json
├── figures/                    # 必须由真实运行产生
├── tables/                     # 必须由真实运行产生
├── paper.md
├── paper.docx
└── flash_report.json
```

不要修改 `problem_files/`，不要读取其他版本的 `paper_output_*` 结果，也不要把赛题代码写回安装包目录。

## 快速流程

严格按以下顺序执行，不路由到其他 MathModel 入口：

1. **预检**：运行 `flash_preflight.py`，记录题目和附件的大小及 SHA-256，并检查混装。
2. **快速建模计划**：写 `plan.json`。每个显式子问题对应一个 `Q*`，优先使用可解释基线；只有明显必要时才加入一个轻量备选。
3. **一次性实验脚本**：写 `code/model.py`，实际读取附件、处理全部问题、计算指标、输出 `results.json`、CSV 和 PNG。不能手写或编造运行结果。
4. **真实运行**：运行 `flash_run.py`。默认 240 秒，可按实际算法使用 `--timeout` 调高；运行前会删除旧结果，避免复用旧实验。
5. **长文写作**：根据计划和结果生成完整 `paper.md`，按问题展开问题重述、假设、符号、模型、算法、实验、结果、检验、局限和结论。正式目标为 18–22 页，不是几段摘要。
6. **快速交付检查**：运行 `flash_finalize.py`，通过后生成可编辑 `paper.docx`。检查会拒绝占位符、空指标、缺问题、重复段落、失效图表和运行后篡改。

命令示例：

```bash
python .claude/skills/mathmodel-flash/scripts/flash_preflight.py
python .claude/skills/mathmodel-flash/scripts/flash_run.py
python .claude/skills/mathmodel-flash/scripts/flash_finalize.py
```

## 计划与论文要求

`plan.json` 至少包含：

```json
{
  "delivery": {"mode": "basic-long-paper", "target_pages": 20},
  "questions": [
    {"id": "Q1", "task": "要解决的问题", "model": "可解释方法", "output": "需要报告的结果"}
  ]
}
```

正文至少包含摘要、问题重述、模型假设、符号与数据、模型建立与求解、实验设计、结果与检验、敏感性或局限、结论。每个 `Q*` 必须有独立标题，并同时解释方法、真实数值、验证方式和适用边界。图表使用 `![说明](paper_output_flash/figures/...)`，且必须在运行清单中有记录。

Flash 会报告有效字符数和粗略页数估计。粗略页数不足目标时给出警告；内容完整性仍必须通过，不能通过重复文字强行填充。若需要可提交、可审计的正式稿，改用 Standard；若需要最高强度研究与审稿闭环，改用 Pro。

## 交付底线

- `input_manifest.json`、`plan.json`、`model.py`、`run_manifest.json` 和 `results.json` 必须哈希绑定。
- `results.json` 必须为 `computed`，每个问题恰好出现一次，指标必须是有限数值，引用文件必须存在且非空。
- 论文中的关键数值必须出现在对应问题段落；不得使用占位词、空答案或重复正文。
- 只在 `flash_report.json.status == PASS` 时把 `paper.docx` 称为 Flash 基础长文交付物。
- PASS 只表示真实运行和基础文档完整性通过，不表示数学结论、引用、公式或比赛格式已经达到 Standard/Pro 水平。
