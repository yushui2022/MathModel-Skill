---
name: paper-formal-writer
description: "MathModel Pro P7-P9 正式论文写作与 Word/PDF 交付。仅基于冻结证据全局写稿，生成原生 DOCX，再由 LibreOffice 渲染和核验 PDF。"
---

# Pro Formal Paper Writer

仅当检查点 3 新鲜批准且 `evidence_freeze.json` PASS 时运行。读取题意共识、获选路线、
冻结证据、来源账本、图表和表格，从整体论证出发写
`paper_output_pro/final_paper_source.md`。正式主稿不得由微单元或旧草稿拼接。

- 所有数值、图表、结论和外部声明必须有冻结 claim ID。
- 论文语言跟随题面和用户要求，默认中文竞赛论文。
- 假设、符号、模型、求解、验证、不确定性、局限和结论形成完整闭环。
- 图表和公式在正文中先引用后出现，编号、标题、单位和来源一致。
- 只从同一正式源稿生成 DOCX；公式用 Word 原生 OMML。

完成 `pro-review-board` 全轮审稿和修复后，用 LibreOffice 生成 `final_paper.pdf`。
写 `final_format_report.json`，记录源稿、DOCX、PDF 当前哈希和页数、可提取文本、
公式、图表、分页、引用、DOCX/PDF 内容一致性及 LibreOffice 版本。全部 PASS 后运行
`pro_format_check.py` 与 `pro_gate.py`。没有 LibreOffice、渲染失败、PDF 为空或内容
不一致时阻止正式交付。
