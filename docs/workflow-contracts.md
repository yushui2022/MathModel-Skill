# Workflow Contracts

MathModel Skill 使用少量 JSON 文件作为不同 skill 之间的结构化交接单。这些文件不是 Trae、Claude Code 或 Codex 的平台标准，而是本项目自己的 workflow contract。

JSON 只保存后续环节必须稳定读取的结构化信息；长篇解释、写作策略和提示词仍放 Markdown 或 `references/`。

生成物位置遵守 [Output Layout](output-layout.md)：当前赛题专用代码统一写入 `paper_output/code/`，不要写回 skill 包目录。

## Contract List

| Contract | Producer | Consumers | Purpose |
|---|---|---|---|
| `paper_output/input_manifest.json` | `paper-workflow-orchestrator` | 数据、建模、QA、workflow guard | 保存附件角色、字节数和 SHA-256，固定本次运行的输入快照 |
| `paper_output/step1/problem_analysis.json` | `problem-doc-model-selector` | 模型路线、QA、微单元生成 | 保存结构化题意分析、子问题、任务类型、数据附件画像 |
| `paper_output/plan/model_route.json` | `modeling-paper-rubric-and-model-selector` | QA、微单元生成 | 保存每一问的模型路线、验证计划、图表证据和章节落点 |
| `paper_output/plan/rubric_alignment.json` | `modeling-paper-rubric-and-model-selector` | QA、微单元生成 | 保存评分点与证据形式的映射 |
| `paper_output/plan/data_plan.json` | `data-cleaning-and-visualization` | QA、微单元生成、后续代码生成 | 保存数据文件、字段画像、清洗任务与子问题链接 |
| `paper_output/plan/visualization_plan.json` | `data-cleaning-and-visualization` | QA、微单元生成、后续绘图代码 | 保存建议图表、图题、用途、候选字段、图表模板和输出路径 |
| `paper_output/figure_index.json` | `data-cleaning-and-visualization` | QA、正文引用检查 | 保存计划图表索引，辅助检查图文断链 |
| `paper_output/data_cleaned/load_report.json` | `data-cleaning-and-visualization` | 建模、workflow guard | 保存数据读取状态和 `input_manifest_sha256`，防止输入变化后继续使用旧清洗结果 |
| `paper_output/results/model_results.json` | `model-code-and-result-generator` | QA、微单元生成 | 保存每问模型输出、参数、方案、预测值或排序结果 |
| `paper_output/results/run_manifest.json` | `run_modeling.py` | workflow guard、evidence gate | 保存建模脚本、命令、退出码、输入/输出大小和 SHA-256 |
| `paper_output/results/metrics.json` | `model-code-and-result-generator` | QA、微单元生成 | 保存 RMSE、MAE、F1、综合得分、约束满足率等评价指标 |
| `paper_output/results/conclusions.json` | `model-code-and-result-generator` | QA、微单元生成 | 保存每问可直接回扣题目的结构化结论 |
| `paper_output/tables/table_index.json` | `model-code-and-result-generator` / `data-cleaning-and-visualization` | QA、微单元生成、正文引用检查 | 保存论文表格索引、表题、用途、关联子问题和路径 |
| `paper_output/tasks.json` | `quality-assurance-auditor` | `paper-micro-unit-generator` | 保存微单元任务清单 |
| `paper_output/qa/evidence_gate_report.json` | `quality-assurance-auditor` | `paper-formal-writer`、workflow guard | 保存证据门禁状态和被审计输入的 SHA-256 |
| `paper_output/plan/paper_outline.json` | `paper-formal-writer` | Agent、Word 排版、格式门禁 | 保存正式论文章节、目标字数、每问图表/表格/公式/证据要求 |
| `paper_output/format_check_report.json` | `paper-formal-writer` | workflow guard、最终 QA | 保存格式门禁、原生公式、引文、渲染结果和输入 SHA-256 |

## Rules

- 所有路径使用相对路径，不写入本机绝对路径。
- 所有 JSON 必须包含 `schema_version`、`generated_by`、`generated_at`。
- 子问题 ID 统一使用 `Q1`、`Q2`、`Q3`。
- 结果、指标、结论和表格都必须能追溯到 `question_id`；公共数据画像表可使用 `ALL`。
- 下游在使用报告前必须重新计算报告中的输入哈希；输入、代码或产物变化后，旧 `load_report`、`run_manifest`、evidence report 和 format report 一律视为过期。
- 正式指标必须非空且为有限值；缺失、空、失败或 placeholder 图表表格不得进入 evidence gate PASS。
- JSON 只保存结构化交接信息，不保存完整论文正文。
- `paper_outline.json` 是正式论文写作计划，不是正文生成器；Agent 必须读取证据链后全局写作 `final_paper_source.md`。
- Markdown 用于解释为什么这样建模、如何对应评分点、后续生成应注意什么。
- 下游 skill 读取更具体的 contract 时，必须保留回退能力，避免缺少某个文件就中断全流程。

## Current Flow

```text
paper-workflow-orchestrator
        ↓
paper_output/OUTPUT_LAYOUT.md
paper_output/code/
        ↓
problem_files/
        ↓
problem-doc-model-selector
        ↓
paper_output/step1/problem_analysis.json
        ↓
modeling-paper-rubric-and-model-selector
        ↓
paper_output/plan/model_route.json
paper_output/plan/rubric_alignment.json
paper_output/plan/scoring_strategy.md
        ↓
data-cleaning-and-visualization
        ↓
paper_output/plan/data_plan.json
paper_output/plan/visualization_plan.json
paper_output/figure_index.json
paper_output/data_cleaned/load_report.json
        ↓
paper_output/code/data_processing/
paper_output/code/visualization/
paper_output/data_cleaned/
paper_output/figures/
        ↓
model-code-and-result-generator
        ↓
paper_output/code/modeling/
paper_output/results/model_results.json
paper_output/results/metrics.json
paper_output/results/conclusions.json
paper_output/results/run_manifest.json
paper_output/tables/table_index.json
        ↓
quality-assurance-auditor
        ↓
paper_output/tasks.json
        ↓
paper-micro-unit-generator (quickstart/草稿/提示词资产)
        ↓
paper_output/final_paper.md
paper_output/final_paper.docx

正式成稿分支：

quality-assurance-auditor/evidence_gate.py
        ↓
paper_output/qa/evidence_gate_report.json
        ↓
paper-formal-writer/build_paper_outline.py
        ↓
paper_output/plan/paper_outline.json
        ↓
Agent writes paper_output/final_paper_source.md
        ↓
paper-formal-writer/format_formal_docx.py
        ↓
paper_output/final_paper.docx
        ↓
paper-formal-writer/check_paper_format.py
        ↓
paper_output/format_check_report.json
```

## User Control

高级用户可以直接检查或修改 `paper_output/plan/model_route.json`。例如把某一问的 `main_model` 改成更合适的方法后，再重新运行 QA 和微单元生成，即可让后续正文围绕新的模型路线展开。

同理，`data_plan.json` 与 `visualization_plan.json` 可以被当作数据和图表的“工作清单”。真实赛题中，Agent 应读取这些契约和 `scripts/` 样板，再按当前字段、单位和图表要求二次生成或修改代码，而不是机械套用固定脚本。

`paper_figure_templates.py` 提供论文级图表代码样板，`generate_paper_figures_from_plan.py` 可以先按计划生成一版草稿图并更新 `figure_index.json`。这些草稿图用于帮助 Agent 对齐图表格式和路径，正式论文仍应接入当前赛题真实模型输出。

`paper_output/code/modeling/` 是当前赛题建模代码工作区。`model-code-and-result-generator` 会根据任务类型生成 `run_modeling.py`、`result_contract_io.py` 和 `q*_model.py` 脚手架；这些文件是 Agent 二次修改的起点，不是最终建模答案。

`paper_output/results/` 与 `paper_output/tables/` 是结果证据层。脚本会先生成可追溯的结果、指标、结论和表格骨架；运行并修改 `q*_model.py` 后，应把真实或已复核的数值写回这些契约，再重新运行 QA，让 `tasks.json` 读取最新结果证据。

`paper_output/plan/paper_outline.json` 是正式论文层的结构契约。它把题意、模型路线、结果、图表、表格和指标映射到 `1 / 1.1 / 1.1.1` 标题结构，尤其是第 5 章每个 `Q*` 对应的 `5.x` 小节。它不保存长篇正文，也不替代 Agent 写作。
