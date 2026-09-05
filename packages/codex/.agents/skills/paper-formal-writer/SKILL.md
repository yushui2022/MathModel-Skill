---
name: paper-formal-writer
description: "MathModel Pro P7-P9 正式论文写作与 Word/PDF 交付。仅基于冻结证据全局写稿，生成原生 DOCX，再由 LibreOffice 渲染和核验 PDF。"
---

# Pro Formal Paper Writer

仅当检查点 3 新鲜批准且 `evidence_freeze.json` PASS 时运行。读取题意共识、获选路线、
冻结证据、来源账本、图表和表格，从整体论证出发写
`paper_output_pro/final_paper_source.md`。正式主稿不得由微单元或旧草稿拼接。

先创建 `paper_plan.json`，声明标题、语言、目标有效字符数、有序章节及各章最低篇幅、
图表路径；数值声明必须对应冻结 claim ID。在对应论证段落末尾添加
`<!-- claim:C1 -->` 证据标记，转换 Word 时自动移除。先运行总入口脚本
`pro_paper_audit.py --project-root <项目>`，确认章节、数值、引用、公式和图表通过。
篇幅达标不是质量目标，具体论证要求见总入口 `references/paper-quality.md`。

先读取 `pro_config.json.reasoning_profile.phase_effort.authoring`。平台支持分阶段调节时
使用该档位；否则保留并记录当前档位。长篇正文只正式生成一次：推理用于检查证据、
结构、符号和论证，不得先完整暗写一遍正文再重复输出。通用自检由下列门禁完成，
不要在五角色 review board 之外增加无明确失败假设的重复审稿轮次。

- 所有数值、图表、结论和外部声明必须有冻结 claim ID。
- 论文语言跟随题面和用户要求，默认中文竞赛论文。
- 假设、符号、模型、求解、验证、不确定性、局限和结论形成完整闭环。
- 图表和公式在正文中先引用后出现，编号、标题、单位和来源一致。
- 只从同一正式源稿生成 DOCX；公式用 Word 原生 OMML。

完成 `pro-review-board` 全轮审稿和修复后，用 LibreOffice 生成 `final_paper.pdf`。
使用总入口 `pro_render_pdf.py` 生成 PDF、`render_manifest.json` 和逐页 PNG。
实际查看每一页后填写 `visual_review.json`，绑定当前渲染清单和每页哈希，记录观察和
未解决问题。再运行 `pro_format_check.py --project-root <项目>` 自动生成格式报告，
最后执行 `pro_gate.py --project-root <项目>`。禁止手填格式 PASS。没有 LibreOffice、
渲染失败、PDF 为空、内容不一致或未完成逐页检查时阻止正式交付。
