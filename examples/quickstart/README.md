# Quickstart Demo

这是 MathModel Skill 的最小可跑示例，用来验证 Trae、Claude Code、Codex 三端 skill 包是否安装正确。

注意：本示例不是正式数学建模赛题，也不代表真实比赛论文质量。它只验证目录链路、JSON 交接单、脚本样板、图表目录和 Word 输出是否能跑通。

```text
题意解析 -> 模型路线 -> 数据与图表计划 -> 结果契约草稿 -> QA -> 微单元验证草稿 -> Word
```

## 示例文件

```text
examples/quickstart/
└── problem_files/
    ├── sample_problem.txt
    └── sample_data.csv
```

## 使用方式

1. 新建一个空项目目录，例如 `my-mm-demo/`。
2. 按你的 Agent 平台复制对应 skill 包。
3. 把本目录下的 `problem_files/` 复制到 `my-mm-demo/problem_files/`。
4. 在 `my-mm-demo/` 根目录让 Agent 使用 `paper-workflow-orchestrator`。
5. 如果只是验证安装，可以手动运行下面的辅助脚本。

Trae:

```bash
python .trae/skills/paper-workflow-orchestrator/scripts/quickstart_run.py
```

Claude Code:

```bash
python .claude/skills/paper-workflow-orchestrator/scripts/quickstart_run.py
```

Codex:

```bash
python skills/paper-workflow-orchestrator/scripts/quickstart_run.py
```

## 期望输出

成功后会生成：

```text
paper_output/
├── OUTPUT_LAYOUT.md
├── step1/problem_analysis.json
├── plan/model_route.json
├── plan/data_plan.json
├── plan/visualization_plan.json
├── results/model_results.json
├── results/metrics.json
├── results/conclusions.json
├── tables/table_index.json
├── tasks.json
├── final_paper.md
├── final_paper.docx
├── ref_check.md
├── data_cleaned/
├── figures/
└── code/
```

`quickstart_run.py` 产出的 `final_paper.md` 和 `final_paper.docx` 只是验证草稿。正式赛题必须由 Agent 读取完整 skill、赛题附件、模型路线、真实代码运行结果、图表、表格和证据门禁报告后全局写作，不能机械拼接 quickstart 草稿。

## 正式门禁

正式写作前可以运行证据门禁：

```bash
python skills/quality-assurance-auditor/scripts/evidence_gate.py
```

如果只是在 quickstart 场景验证链路，使用：

```bash
python skills/quality-assurance-auditor/scripts/evidence_gate.py --mode quickstart
```

当证据状态仍是 `missing`、`needs_real_modeling` 或 `scaffold_result_needs_review` 时，不能把 Word 称为最终稿。
