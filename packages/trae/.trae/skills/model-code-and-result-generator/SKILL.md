---
name: "model-code-and-result-generator"
description: "根据 model_route.json、数据计划和清洗数据，为数学建模论文生成结果证据契约和 q1/q2/q3 建模代码脚手架。Invoke when 需要把模型输出、评价指标、结构化结论、论文表格和当前赛题专用建模代码沉淀到 paper_output/results/、paper_output/tables/ 和 paper_output/code/modeling/，供 QA 与正文生成读取。"
---

# 建模代码与结果证据生成器

## 全局流程协作约束（长对话防漂移）

- 本 skill 不得作为孤立入口。用户要求完整论文、生成 Word、继续流程或不确定阶段时，先回到 `paper-workflow-orchestrator` 判断当前 S0-S8 阶段。
- 启动或继续本 skill 的正式任务前，必须运行：
  ```bash
  python .trae/skills/paper-workflow-orchestrator/scripts/workflow_guard.py --skill model-code-and-result-generator
  ```
- 如果输出 `[WORKFLOW FAIL]` 或报告 `status != "PASS"`，停止本 skill，按 `paper_output/qa/workflow_guard_report.json` 的失败项回补前置阶段，不得凭记忆继续。
- 本 skill 只写入自己契约范围内的 `paper_output/` 产物；完成后必须回到 `paper-workflow-orchestrator` 判断下一步，并用 `context-memory-keeper` 记录已完成产物、阻塞项和下一步。
- 长对话中如果上下文变长、阶段不确定或用户分开调用 skill，先运行：
  ```bash
  python .trae/skills/paper-workflow-orchestrator/scripts/workflow_guard.py --status
  ```
  再读取 `paper_output/qa/workflow_guard_report.json`、`paper_output/preflight_report.json`、`paper_output/input_manifest.json`、`paper_output/results/run_manifest.json` 和本 skill 的上游 JSON 契约，按报告里的 `recommended_skill` 与 `next_action` 继续。
- 继续流程前，必须把 `paper_output/context/workflow_memory.json` 视为长期断点记录；若其中的 `current_step`、`next_step`、`recommended_skill` 与 `workflow_guard.py --status` 不一致，以 guard 报告为准。
- 每次完成本 skill 的产物后，先回到 `paper-workflow-orchestrator` 或运行 `workflow_guard.py --status`，再更新 workflow memory：
  ```bash
  python .trae/skills/context-memory-keeper/scripts/update_workflow_memory.py
  ```
  更新后读取 `paper_output/context/workflow_memory.json` / `.md`，确认下一步和推荐 skill 已记录。

## 目标

本 skill 不是万能自动建模系统。它的作用是给 Agent 一个稳定的“结果证据层”和可运行的赛题专用建模代码起点，避免正文只根据模型路线空写，也避免 Agent 面对数据时无头乱转。

真实赛题中，Agent 必须根据 `model_route.json`、数据字段、题目约束和评分要求二次修改生成的 `q*_model.py`。生成代码固定放在 `paper_output/code/modeling/`，不要写回 skill 包的 `scripts/`。

## 执行契约

- 上游输入：读取 `paper_output/plan/model_route.json`、`data_plan.json`、`visualization_plan.json`，数据只能来自当前有效 `cleaning_report.json` 绑定的产物，不扫描历史批次。缺清洗报告时先运行数据处理技能；自定义清洗也须记录真实来源与输出哈希。
- 必须输出：`paper_output/results/model_results.json`、`metrics.json`、`conclusions.json`、`run_manifest.json`、`paper_output/tables/table_index.json`、`paper_output/tables/*.csv`。
- 建模代码输出：`paper_output/code/modeling/result_contract_io.py`、`run_modeling.py`、`q1_model.py`、`q2_model.py`、`q3_model.py` 或与 `question_id` 对应的 `q*_model.py`。
- 下游交接：`quality-assurance-auditor` 直接审计结果、指标、表格、图表和结论；证据门禁 PASS 后由 `paper-formal-writer` 构建正式写作计划。
- 失败回退：如果没有清洗数据或真实建模代码，仍生成契约骨架，并用 `needs_real_modeling` 标记，不伪装成最终比赛结果。

## 脚本

- `scripts/build_result_contracts.py`
  - 何时用：已有模型路线，需要生成结果契约、表格索引和当前赛题的 q1/q2/q3 建模代码脚手架。
  - 做什么：扫描 `model_route.json` 的每个 `question_id`，生成结果契约骨架、基础字段画像表、`paper_output/code/modeling/README.md`，并生成可运行的 `q*_model.py`。
  - 覆盖规则：生成文件带有 managed marker；如果 Agent 已经手工改写并去掉 marker，本脚本会保留用户文件，不覆盖。
- `scripts/result_contract_templates.py`
  - 何时用：需要了解不同任务类型应沉淀哪些指标、表格和结论字段。
  - 做什么：提供预测、优化、评价、分类、聚类、仿真、通用建模的契约模板。
- `scripts/modeling_tools.py`
  - 生成脚手架时复制到赛题代码目录，提供当前数据集选择、训练集内预处理的回归基线，以及线性优化解的约束/目标值复核。
  - 需要这些工具时读取 [references/modeling-tools.md](references/modeling-tools.md)。先明确数据源、工作表、字段和样本划分，再调用工具；不要把工具输出自动升级为正式结论。
- `scripts/validation_tools.py` / `scripts/solver_evidence.py`
  - 预测验证或线性/整数优化时读取 [references/experiment-validation.md](references/experiment-validation.md)：时间留出、滚动回测、分组留出、特征可用时点、可选 SciPy/HiGHS 求解与独立约束复核。
  - 报告、预测表和指标 CSV 自动连接运行账本及数值声明；工具成功不自动通过 S6。求解限时/非零差距不能被写成最优。

## 任务类型分发

- 预测/回归 -> forecasting scaffold：显式选择 `regression.validation` 验证方案，或保留旧 `target/features/train_rows/test_rows` 接口。新接口要求单位与特征可用性声明；不能把行号不重叠当成没有泄漏。
- 优化/规划/调度/选址/路径 -> optimization scaffold：显式 `optimization` 配置调用线性/整数求解适配；未配置时仍只是代理方案脚手架，不是正式最优解。
- 评价/排序/权重/TOPSIS/AHP/熵权 -> evaluation scaffold：生成指标归一化、综合得分、排序和权重敏感性待补项。
- 分类/识别/判别 -> classification scaffold：生成代理分类标签、准确率/F1 待补项。
- 聚类/分群 -> clustering scaffold：生成代理聚类标签、聚类数、簇内紧凑度。
- 仿真/机理/动力学/微分 -> simulation scaffold：生成趋势代理、情景结果、拟合误差和敏感性参数。
- 其他 -> general scaffold：生成数值字段统计摘要和通用结果表。

## 输出位置

```text
paper_output/
|-- code/
|   `-- modeling/
|       |-- run_modeling.py
|       |-- result_contract_io.py
|       |-- q1_model.py
|       |-- q2_model.py
|       |-- q3_model.py
|       `-- README.md
|-- results/
|   |-- model_results.json
|   |-- metrics.json
|   `-- conclusions.json
`-- tables/
    |-- table_index.json
    |-- table_q1_result_skeleton.csv
    |-- table_q1_forecasting_scaffold.csv
    `-- ...
```

统一规则：

- 所有路径使用相对路径。
- 所有 JSON 包含 `schema_version`、`generated_by`、`generated_at`。
- 每条结果、指标、结论和表格都应带 `question_id`。
- 草稿或脚手架结果必须使用 `status` 或 `evidence_status` 标记。
- 多数据集时在问题配置中指定原始 `data_source` 和必要的 `sheet`，不能默认选第一个文件。单个数据集允许省略选择，但不自动猜预测目标列。
- `verify_linear_solution` 只核验提供的线性约束、边界、整数性与目标值；PASS 不证明全局最优，也不证明约束忠实于赛题。
- 正式结果必须带 `execution_provenance`，至少包含 `source_code_path`、`source_code_sha256`、`run_command`、`run_exit_code` 和 `output_artifacts`。
- 新 runner 使用 1.1 账本：来源须带本次 `run_id`，结束时绑定四份共享结果契约；默认每问 600 秒超时，日志写文件。编写自定义代码、失败排查或旧项目迁移时读取 [运行记录与迁移](references/execution-records.md)，不要复用旧 ID 或手改账本。
- 统一入口 `run_modeling.py` 必须在实际执行后写入 `paper_output/results/run_manifest.json`，记录总体 `status`、脚本 hash、`question_ids`、退出码、工作目录、Python 实现/版本/平台，以及每个输入和输出文件的 `path`、`bytes`、`sha256`、`exists`。
- `run_manifest.json` 不是日志占位符。建模脚本、输入文件或输出产物在运行后发生变化时，必须重新运行模型，不能手改 manifest 或结果 JSON 续签旧证据。
- 新生成的 runner 绑定当前清洗报告、来源、清洗产物、路线和建模目录内的 Python 辅助文件；运行中变化则失败。已有用户修改过的 runner 不会被覆盖，升级时须人工迁移这些检查或在独立新项目重新生成。
- `model_results.json` 中正式条目必须有非空 `result_summary`；`metrics.json` 中 `status=computed` 的指标必须有非空、有限的 `value`，不得使用 `null`、`NaN` 或无穷值。
- 供正式论文引用的数值指标须由计算代码同时输出稳定的 `metric_id`、`unit`、`split`、`sample_scope` 和唯一 CSV 行定位 `source_table`；同名训练/测试指标使用不同 ID。参阅 [指标与结论绑定契约](../paper-formal-writer/references/metric-claims.md)。缺元数据会在 S7 阻塞，不允许写作者猜测；最优性声明还需同次运行的验证报告。
- `table_index.json` 中正式表格必须指向真实存在且非空的文件；只有索引条目、没有 CSV/XLSX 产物不能作为证据。
- official evidence gate 会重新计算脚本、输入和输出哈希，并拒绝没有真实代码运行来源、运行账本状态失败、文件被修改或运行记录无法关联 `question_id` 的结果。
- 正文中引用的表格必须能在 `paper_output/tables/table_index.json` 找到。

## 使用方式

推荐由 `paper-workflow-orchestrator` 在数据清洗与可视化之后调用。也可以手动运行：

```bash
python .trae/skills/model-code-and-result-generator/scripts/build_result_contracts.py
```

生成脚手架后，Agent 应按真实赛题执行：

```bash
python paper_output/code/modeling/run_modeling.py
```

该入口会写入 `paper_output/results/run_manifest.json`。运行后不要再编辑建模脚本或产物；如需修正，修改后重新运行入口，再重新运行 evidence gate 和 S7 写作准备，使结果与写作契约同步失效并重建。

## 真实赛题使用原则

- 不要把占位式指标或代理结果直接当成最终比赛结果。
- 优先修改 `paper_output/code/modeling/q*_model.py`，不要修改 skill 包内的 `scripts/`。
- 正式建模完成后，必须由建模代码实际运行并把真实输出写回 `paper_output/results/` 与 `paper_output/tables/`；不要手写 `model_results.json` 冒充运行结果。没有 `run_manifest.json` 对应运行记录时，不能进入正式 evidence gate。
- 如果某一问没有真实结果，QA 应保留 warning，正文不得把该问写成已经完成精确计算。
