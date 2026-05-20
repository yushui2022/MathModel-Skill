---
name: "model-code-and-result-generator"
description: "根据模型路线、数据计划和清洗数据生成建模结果证据契约。Invoke when 需要把模型输出、评价指标、结论和论文表格沉淀为 paper_output/results/ 与 paper_output/tables/，供 QA 和正文生成读取。"
---

# 建模代码与结果证据生成器

## 执行契约
- 上游输入：优先读取 `paper_output/plan/model_route.json`、`data_plan.json`、`visualization_plan.json`，并扫描 `paper_output/data_cleaned/` 中的清洗数据。
- 必须输出：`paper_output/results/model_results.json`、`metrics.json`、`conclusions.json`、`paper_output/tables/table_index.json`、可复用的 `paper_output/tables/*.csv`，并准备 `paper_output/code/modeling/README.md`。
- 下游交接：`quality-assurance-auditor` 读取结果和表格证据后写入 `tasks.json`；`paper-micro-unit-generator` 通过任务清单引用结果、指标、表格和结论。
- 推荐下一步：结果证据生成后进入 `quality-assurance-auditor`；完整论文目标应回到 `paper-workflow-orchestrator` 判断后续阶段。
- 失败回退：若没有真实建模代码或清洗数据，仍生成结果契约骨架，并明确标记“真实数值需结合当前赛题专用代码补齐”。

## 目标

本 skill 不是万能自动建模系统。它的作用是给 Agent 一个稳定的结果证据层，避免正文只根据模型路线空写。

真实赛题中，Agent 应根据 `model_route.json`、`data_plan.json`、清洗数据和现有代码样板，生成或修改当前赛题专用建模代码，然后把输出沉淀到本 skill 规定的契约中。当前赛题专用建模代码统一放在 `paper_output/code/modeling/`，不要写回 skill 包的 `scripts/`。

## 脚本清单

- `scripts/build_result_contracts.py`
  - 何时用：已有模型路线和数据计划，需要先生成结果证据契约骨架，或根据清洗数据生成基础描述统计和候选结果表。
  - 做什么：扫描 `model_route.json` 的每个 `question_id`，生成 `model_results.json`、`metrics.json`、`conclusions.json`、`table_index.json`、若干 `tables/*.csv`，并写入 `paper_output/code/modeling/README.md` 说明 q1/q2/q3 建模脚本的放置位置。

- `scripts/result_contract_templates.py`
  - 何时用：Agent 需要了解不同任务类型应沉淀哪些指标、表格和结论字段时。
  - 做什么：提供预测、优化、评价、分类、聚类、机理仿真等任务的结果契约模板。

## 结果契约

输出目录固定为：

```text
paper_output/
├── code/
│   └── modeling/
│       └── README.md
├── results/
│   ├── model_results.json
│   ├── metrics.json
│   └── conclusions.json
└── tables/
    ├── table_index.json
    ├── table_q1_result_skeleton.csv
    ├── table_data_profile_*.csv
    └── ...
```

统一规则：

- 所有路径使用相对路径。
- 所有 JSON 包含 `schema_version`、`generated_by`、`generated_at`。
- 每条结果、指标、结论和表格都应带 `question_id`。
- 若当前只是骨架结果，必须用 `status` 或 `evidence_status` 标记，不能伪装成真实计算结果。
- 表格进入正文前必须能在 `paper_output/tables/table_index.json` 中找到。

## 建模代码位置

当前赛题专用建模代码固定放在：

```text
paper_output/code/modeling/
├── run_modeling.py          # 可选，统一运行 Q1/Q2/Q3
├── result_contract_io.py    # 可选，统一写回 results/tables 契约
├── q1_model.py              # 问题一专用建模代码
├── q2_model.py              # 问题二专用建模代码
├── q3_model.py              # 问题三专用建模代码
└── README.md
```

第一版脚本只会生成结果契约骨架和建模代码工作区说明，不承诺自动生成完整真实建模代码。真实赛题中，Agent 应先读取本 skill 的模板和 `model_route.json`，再在 `paper_output/code/modeling/` 中生成或修改 q1/q2/q3 专用脚本，并把真实输出写回 `paper_output/results/` 与 `paper_output/tables/`。

## 使用方式

推荐由 `paper-workflow-orchestrator` 在数据清洗与可视化之后调用。也可以手动运行：

```bash
python skills/model-code-and-result-generator/scripts/build_result_contracts.py
```

平台路径不同时，按对应平台 skill 目录替换命令前缀即可。

## 真实赛题使用原则

- 不要把本 skill 生成的占位式指标直接当成最终比赛结果。
- 需要正式建模时，先让 Agent 读取 `model_route.json` 和清洗数据，再参考本 skill 的脚本生成当前题目的专用建模代码，代码位置固定为 `paper_output/code/modeling/`。
- 专用建模代码完成后，应覆盖或补全 `paper_output/results/` 与 `paper_output/tables/`，再进入 QA 和正文生成。
