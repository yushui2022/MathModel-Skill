# MathModel Skill Workflow for Codex

你正在一个安装了 MathModel Skill 的 Codex 项目中工作。

## 工作目标

当用户要求“开始生成”“跑一下这个题”“生成数学建模论文”时，按 MathModel Skill 工作流完成：

```text
读题 -> 拆题 -> 模型路线 -> 判断附件性质 -> 生成/修改赛题专用代码 -> 运行代码 -> 真实图表/表格/结果 -> QA 门禁 -> Agent 全局写作 -> 最终 QA
```

## Start Rule

任何数学建模论文任务都先读取总控 skill：

```text
skills/paper-workflow-orchestrator/SKILL.md
```

包括用户只说“开始生成”“帮我做这个题”“分析赛题”“使用 MathModel Skill”或不知道该用哪个 skill 的情况。不要直接从数据清洗、微单元生成或 QA 开始；先让 `paper-workflow-orchestrator` 判断当前阶段，再路由到其他 skill。

## 原生 Skill 目录

Codex skill 包位于：

```text
skills/
```

优先读取总控 skill：

```text
skills/paper-workflow-orchestrator/SKILL.md
```

不要把这些 skill 当作普通 Markdown 摘要。每个 skill 都是完整包，可能包含：

```text
SKILL.md
scripts/
references/
assets/
memoryskill.md
```

## 输入输出约定

用户应把赛题和附件放到：

```text
problem_files/
```

外部补充数据可放到：

```text
crawled_data/
```

输出产物在：

```text
paper_output/OUTPUT_LAYOUT.md
paper_output/final_paper.docx
paper_output/final_paper.md
paper_output/code/data_processing/
paper_output/code/visualization/
paper_output/code/modeling/
paper_output/code/qa/
paper_output/plan/model_route.json
paper_output/plan/data_plan.json
paper_output/plan/visualization_plan.json
paper_output/figure_index.json
paper_output/results/model_results.json
paper_output/results/metrics.json
paper_output/results/conclusions.json
paper_output/tables/table_index.json
paper_output/ref_check.md
```

`skills/*/scripts/` 是可复用模板和代码级提示词；当前赛题生成或二次修改的代码只写入 `paper_output/code/`。数据处理脚本放 `paper_output/code/data_processing/`，绘图脚本放 `paper_output/code/visualization/`，q1/q2/q3 建模脚本放 `paper_output/code/modeling/`，可选检查脚本放 `paper_output/code/qa/`。

## 可选验证命令

普通使用时不需要用户手动运行脚本；Agent 应先读取总控 skill。正式赛题不要先跑 quickstart。若只是验证安装、跑 quickstart 或调试，可在项目根目录运行：

```bash
python skills/paper-workflow-orchestrator/scripts/quickstart_run.py
```

旧命令 `run_all.py` 已废弃，只保留迁移提示。quickstart 输出是验证草稿，不代表正式比赛论文质量。

如果 Windows 终端出现 GBK 编码问题，先运行：

```powershell
$env:PYTHONIOENCODING="utf-8"
```

## 执行规则

- 不要跳过 `quality-assurance-auditor`。
- 数据清洗后如果需要正文引用结果，先让 `model-code-and-result-generator` 生成或补齐结果、指标、结论和表格证据契约。
- 若 `evidence_status` 仍为 `missing`、`needs_real_modeling` 或 `scaffold_result_needs_review`，不得把 Word 称为最终稿；必须先补齐赛题专用代码和真实结果。
- 不要把输出散落到根目录，统一写入 `paper_output/`。
- 不要把当前赛题专用代码写回 `skills/`；先读取 skill 脚本作为样板，再在 `paper_output/code/` 下生成适配当前数据的代码。
- 不要改动 `problem_files/` 中的原始赛题和附件。
- 当用户只要求局部重跑时，按对应 skill 的 `scripts/` 执行。
- 若流程失败，先检查 `problem_files/` 是否非空，再检查脚本路径和依赖。
