---
name: "paper-formal-writer"
description: "国赛数学建模正式论文范式、outline、Word/LaTeX 排版和格式门禁 skill。Invoke when 证据门禁通过后需要生成 CUMCM 风格正式论文、规范标题编号、扩写正文、插入图表表格、导出 Word/LaTeX 或检查论文格式。"
---

# 正式论文范式写作器

## 执行契约
- 上游输入：必须优先读取 `paper_output/plan/model_route.json`、`paper_output/results/`、`paper_output/tables/table_index.json`、`paper_output/figure_index.json` 和证据门禁报告。
- 核心输出：`paper_output/plan/paper_outline.json`、`paper_output/final_paper_source.md`、`paper_output/final_paper.docx`、`paper_output/final_paper.tex`（LaTeX 分支可选）、`paper_output/format_check_report.md`。
- 下游交接：格式检查通过后，回到 `quality-assurance-auditor` 做最终一致性检查；未通过时继续补正文、图表解释或证据引用。
- 失败回退：证据门禁未通过时，不得把 Word 称为最终稿；可以只生成 outline 和待写作清单。

## 目标
- 本技能负责正式论文范式、章节编号、写作约束、Word/LaTeX 排版和格式检查。
- 正式论文必须由 Agent 基于完整证据链全局写作，不得机械拼接 quickstart 草稿或微单元草稿。
- 标题编号固定采用 `1 / 1.1 / 1.1.1`。
- 正式稿默认目标为 `18000-25000` 中文字；低于 `18000` 在正式格式检查中失败。

## 何时使用
- `quality-assurance-auditor/scripts/evidence_gate.py` official 模式已经通过，需要进入正式成稿。
- 用户要求“按国赛论文格式”“正式 Word”“LaTeX 版本”“扩写到比赛论文工作量”“图表插入并解释”“检查论文格式”。
- 已有 `final_paper_source.md` 或 `final_paper.md`，需要统一 Word 样式、图题表题和标题层级。

## References
- 正式格式总规范：`references/cumcm-paper-standard.md`
- 可直接交给 Agent 的全文模板：`references/formal-paper-template.md`
- 各章节扩写规则：`references/section-expansion-rules.md`
- 图表、公式、算法和结果解释规则：`references/figure-table-writing-rules.md`

## 脚本清单
- `scripts/build_paper_outline.py`
  - 读取题意、模型路线、结果、指标、结论、图表和表格索引。
  - 输出 `paper_output/plan/paper_outline.json`。
- `scripts/format_formal_docx.py`
  - 输入 `paper_output/final_paper_source.md`。
  - 输出 `paper_output/final_paper.docx` 和 `paper_output/format_check_report.md`。
  - 使用 `python-docx`，不依赖 LibreOffice。
- `scripts/format_formal_latex.py`
  - 输入 `paper_output/final_paper_source.md`，共用 Word 的证据链和正文源。
  - 输出 `paper_output/final_paper.tex`；传入 `--compile` 且本机存在 `xelatex` 时，额外输出 `paper_output/final_paper.pdf`。
  - 证据门禁未通过时默认阻塞；如需草稿，使用 `--allow-draft`，只写 `final_paper_draft.tex`。
- `scripts/check_paper_format.py`
  - 检查字数、章节、三级标题、图表引用、参考文献、附录、占位符、证据覆盖和 Word 视觉结构。
  - Word 视觉 QA 至少检查 docx 能否打开、段落数、标题样式数量、图片数量和表格数量是否与索引大体匹配。
  - 输出 `paper_output/format_check_report.md` 与 `paper_output/format_check_report.json`。
- `scripts/check_latex_format.py`
  - 检查 `final_paper.tex` 的 LaTeX 基础结构、章节关键词、图表数量、占位符和可选 PDF 是否生成。
  - 输出 `paper_output/latex_check_report.md` 与 `paper_output/latex_check_report.json`。

## 正式工作流
1. 确认证据门禁已通过；若未通过，先补齐 `paper_output/code/`、`results/`、`tables/` 和 `figures/`。
2. 运行：
   ```bash
   python .trae/skills/paper-formal-writer/scripts/build_paper_outline.py
   ```
3. Agent 读取 `paper_outline.json` 和 references，基于完整证据链全局撰写：
   ```text
   paper_output/final_paper_source.md
   ```
4. 运行：
   ```bash
   python .trae/skills/paper-formal-writer/scripts/format_formal_docx.py
   python .trae/skills/paper-formal-writer/scripts/check_paper_format.py
   ```
5. LaTeX 分支如需 LaTeX 交付，可额外运行：
   ```bash
   python .trae/skills/paper-formal-writer/scripts/format_formal_latex.py
   python .trae/skills/paper-formal-writer/scripts/check_latex_format.py
   ```
   若要尝试生成 PDF：
   ```bash
   python .trae/skills/paper-formal-writer/scripts/format_formal_latex.py --compile
   ```
6. 若格式检查失败，按报告补正文、图表解释、参考文献、附录或缺失章节。

## 正式论文必须满足
- 摘要按子问题展开，包含方法、模型、算法和关键结果。
- `1 问题重述`、`2 问题分析`、`3 模型假设`、`4 符号说明`、`5 模型的建立与求解`、`6 模型检验与灵敏度分析`、`7 模型评价与推广`、`8 参考文献`、`附录` 结构完整。
- 每问在第 5 章中至少包含 `5.x.1 建模思路`、`5.x.2 变量定义与公式推导`、`5.x.3 求解算法`、`5.x.4 结果分析`、`5.x.5 模型检验或灵敏度分析`。
- 每张图表必须在正文中引用并解释；图表不能只插入不分析。
- 每个公式必须先定义变量、再给公式、再解释公式含义和用途。
- 算法必须用 `Step 1`、`Step 2` 等形式说明。

## 与其他 skill 的关系
- `paper-workflow-orchestrator`：总入口，证据门禁通过后路由到本技能。
- `paper-micro-unit-generator`：提示词资产库和兜底草稿工具，不再作为正式论文主笔。
- `quality-assurance-auditor`：负责证据门禁；本技能负责格式门禁，两者都通过后才可称为正式稿。
