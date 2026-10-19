# Formal Paper Authoring

`paper-formal-writer` 是正式论文范式层。它在证据门禁通过后启动，负责生成正式 outline、约束 Agent 写作、格式化 Word，并执行格式门禁。它不做黑盒建模，也不伪造结果。

## 责任边界

```text
证据链负责真实结果
paper-formal-writer 负责正式论文范式、outline、写作约束、Word 排版和格式检查
Agent 负责基于证据链全局写作
脚本负责确定性排版与检查
```

`paper-micro-unit-generator` 仍然保留高质量微单元提示词资产，但它不再是正式论文主笔。正式稿应由 Agent 读取完整题面、模型路线、代码、图表、表格、指标和结论后整体写作。

## 正式流程

```text
证据门禁通过
-> build_paper_outline.py
-> Agent 全局写 final_paper_source.md
-> format_formal_docx.py
-> check_paper_format.py
-> 最终 QA
```

从赛题根运行，`<SKILL_ROOT>` 替换为实际加载的 Skill 父目录：

```bash
python "<SKILL_ROOT>/quality-assurance-auditor/scripts/evidence_gate.py"
python "<SKILL_ROOT>/paper-formal-writer/scripts/build_paper_outline.py"
python "<SKILL_ROOT>/paper-formal-writer/scripts/format_formal_docx.py"
python "<SKILL_ROOT>/paper-formal-writer/scripts/check_paper_format.py"
```


## `paper_outline.json`

正式 outline 写入：

```text
paper_output/plan/paper_outline.json
```

它读取 `problem_analysis.json`、`model_route.json`、`rubric_alignment.json`、`figure_index.json`、`model_results.json`、`metrics.json`、`conclusions.json` 和 `table_index.json`，动态生成第 5 章的 `5.1`、`5.2`、`5.3` 等章节。

每个 `5.x` 默认包含：

- `5.x.1 建模思路`
- `5.x.2 变量定义与公式推导`
- `5.x.3 求解算法`
- `5.x.4 结果分析`
- `5.x.5 模型检验或灵敏度分析`

有图表、表格、指标和结论证据时，outline 会把它们写入 `required_figures`、`required_tables` 和 `required_evidence`。

## Agent 写作要求

Agent 写 `paper_output/final_paper_source.md` 时必须：

- 使用 `1 / 1.1 / 1.1.1` 标题编号。
- 目标 `18000-25000` 中文字。
- 摘要按子问题展开，目标 `800-1200` 字。
- 每问写清模型、公式、算法、结果、图表解释和结论回扣。
- 图表必须先引用、后插入、再解释。
- 公式必须先定义变量、后解释含义。
- 算法必须使用 `Step 1`、`Step 2` 等形式。
- 必须包含模型评价、改进方向、推广应用、参考文献和附录代码说明。

## 格式门禁

`check_paper_format.py` 会检查：

- `final_paper_source.md` 是否存在。
- 有效字数是否达到 `18000`。
- 摘要、关键词、问题重述、问题分析、模型假设、符号说明、参考文献和附录是否存在。
- 是否存在 `5.1`、`5.1.1`、`5.1.2` 等三级标题。
- 每个 `Q*` 是否有建模、算法、结果分析、图表或表格证据、结论回扣。
- `figure_index.json` 和 `table_index.json` 中的图表是否在正文中被引用。
- 是否存在占位符，例如 `内容生成中`、`关键词1`、`论文题目缺失`。

格式门禁未通过时，当前 Word 只能叫草稿，不能称为正式稿。
