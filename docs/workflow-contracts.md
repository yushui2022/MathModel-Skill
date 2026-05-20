# Workflow Contracts

MathModel Skill 使用少量 JSON 文件作为不同 skill 之间的结构化交接单。这些文件不是 Trae、Claude Code 或 Codex 的平台标准，而是本项目自己的 workflow contract。

JSON 只保存后续环节必须稳定读取的结构化信息；长篇解释、写作策略和提示词仍放 Markdown 或 `references/`。

## Contract List

| Contract | Producer | Consumers | Purpose |
|---|---|---|---|
| `paper_output/step1/problem_analysis.json` | `problem-doc-model-selector` | 模型路线、QA、微单元生成 | 保存结构化题意分析、子问题、任务类型、数据附件画像 |
| `paper_output/plan/model_route.json` | `modeling-paper-rubric-and-model-selector` | QA、微单元生成 | 保存每一问的模型路线、验证计划、图表证据和章节落点 |
| `paper_output/plan/rubric_alignment.json` | `modeling-paper-rubric-and-model-selector` | QA、微单元生成 | 保存评分点与证据形式的映射 |
| `paper_output/plan/data_plan.json` | `data-cleaning-and-visualization` | QA、微单元生成、后续代码生成 | 保存数据文件、字段画像、清洗任务与子问题链接 |
| `paper_output/plan/visualization_plan.json` | `data-cleaning-and-visualization` | QA、微单元生成、后续绘图代码 | 保存建议图表、图题、用途、候选字段、图表模板和输出路径 |
| `paper_output/figure_index.json` | `data-cleaning-and-visualization` | QA、正文引用检查 | 保存计划图表索引，辅助检查图文断链 |
| `paper_output/results/model_results.json` | `model-code-and-result-generator` | QA、微单元生成 | 保存每问模型输出、参数、方案、预测值或排序结果 |
| `paper_output/results/metrics.json` | `model-code-and-result-generator` | QA、微单元生成 | 保存 RMSE、MAE、F1、综合得分、约束满足率等评价指标 |
| `paper_output/results/conclusions.json` | `model-code-and-result-generator` | QA、微单元生成 | 保存每问可直接回扣题目的结构化结论 |
| `paper_output/tables/table_index.json` | `model-code-and-result-generator` / `data-cleaning-and-visualization` | QA、微单元生成、正文引用检查 | 保存论文表格索引、表题、用途、关联子问题和路径 |
| `paper_output/tasks.json` | `quality-assurance-auditor` | `paper-micro-unit-generator` | 保存微单元任务清单 |

## Rules

- 所有路径使用相对路径，不写入本机绝对路径。
- 所有 JSON 必须包含 `schema_version`、`generated_by`、`generated_at`。
- 子问题 ID 统一使用 `Q1`、`Q2`、`Q3`。
- 结果、指标、结论和表格都必须能追溯到 `question_id`；公共数据画像表可使用 `ALL`。
- JSON 只保存结构化交接信息，不保存完整论文正文。
- Markdown 用于解释为什么这样建模、如何对应评分点、后续生成应注意什么。
- 下游 skill 读取更具体的 contract 时，必须保留回退能力，避免缺少某个文件就中断全流程。

## Current Flow

```text
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
        ↓
model-code-and-result-generator
        ↓
paper_output/results/model_results.json
paper_output/results/metrics.json
paper_output/results/conclusions.json
paper_output/tables/table_index.json
        ↓
quality-assurance-auditor
        ↓
paper_output/tasks.json
        ↓
paper-micro-unit-generator
        ↓
paper_output/final_paper.md
paper_output/final_paper.docx
```

## User Control

高级用户可以直接检查或修改 `paper_output/plan/model_route.json`。例如把某一问的 `main_model` 改成更合适的方法后，再重新运行 QA 和微单元生成，即可让后续正文围绕新的模型路线展开。

同理，`data_plan.json` 与 `visualization_plan.json` 可以被当作数据和图表的“工作清单”。真实赛题中，Agent 应读取这些契约和 `scripts/` 样板，再按当前字段、单位和图表要求二次生成或修改代码，而不是机械套用固定脚本。

`paper_figure_templates.py` 提供论文级图表代码样板，`generate_paper_figures_from_plan.py` 可以先按计划生成一版草稿图并更新 `figure_index.json`。这些草稿图用于帮助 Agent 对齐图表格式和路径，正式论文仍应接入当前赛题真实模型输出。

`paper_output/results/` 与 `paper_output/tables/` 是结果证据层。第一版脚本会先生成可追溯的结果、指标、结论和表格骨架；真实赛题中，Agent 仍应根据当前数据和模型路线生成专用建模代码，再把真实数值写回这些契约。
