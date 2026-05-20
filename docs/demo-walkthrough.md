# Quickstart Demo Walkthrough

本页用于帮助用户在 3 分钟内跑通 MathModel Skill。示例只验证工作流，不代表真实比赛建模质量。

## 1. 准备一个空项目

```text
my-mm-demo/
```

把本仓库的示例赛题复制进去：

```text
examples/quickstart/problem_files/ -> my-mm-demo/problem_files/
```

## 2. 复制对应平台 Skill 包

Trae:

```text
packages/trae/.trae/skills/ -> my-mm-demo/.trae/skills/
```

Claude Code:

```text
packages/claude/.claude/skills/ -> my-mm-demo/.claude/skills/
packages/claude/CLAUDE.md       -> my-mm-demo/CLAUDE.md
```

Codex:

```text
packages/codex/skills/   -> my-mm-demo/skills/
packages/codex/AGENTS.md -> my-mm-demo/AGENTS.md
```

## 3. 安装依赖

在 `my-mm-demo/` 根目录运行：

```bash
pip install -r path/to/MathModel-Skill/requirements.txt
```

如果已经在当前 Python 环境安装过依赖，可以跳过。

Windows PowerShell 如遇到中文编码问题，先运行：

```powershell
$env:PYTHONIOENCODING="utf-8"
```

## 4. 使用 Skill Workflow

推荐方式是直接对 Agent 说：

```text
开始生成数学建模论文
```

Agent 应优先读取 `paper-workflow-orchestrator/SKILL.md`，再按 workflow 调用其他 skill。

如果你只是想验证安装和示例链路，也可以手动运行随 skill 附带的辅助脚本：

Trae:

```bash
python .trae/skills/paper-workflow-orchestrator/scripts/run_all.py
```

Claude Code:

```bash
python .claude/skills/paper-workflow-orchestrator/scripts/run_all.py
```

Codex:

```bash
python skills/paper-workflow-orchestrator/scripts/run_all.py
```

## 5. 检查输出

运行完成后检查：

```text
paper_output/final_paper.docx
paper_output/final_paper.md
paper_output/OUTPUT_LAYOUT.md
paper_output/code/README.md
paper_output/code/modeling/README.md
paper_output/tasks.json
paper_output/ref_check.md
paper_output/figure_index.json
paper_output/plan/model_route.json
paper_output/plan/data_plan.json
paper_output/plan/visualization_plan.json
paper_output/results/model_results.json
paper_output/results/metrics.json
paper_output/results/conclusions.json
paper_output/tables/table_index.json
paper_output/data_cleaned/
paper_output/figures/
```

如果这些文件存在，说明 skill 包安装和示例 workflow 已经跑通。

## 6. 如何理解示例输出

- `problem_analysis.json` 是赛题结构化分析。
- `model_route.json` 是每一问的模型路线交接单。
- `data_plan.json` 是数据处理交接单。
- `visualization_plan.json` 是图表计划交接单。
- `figure_index.json` 是图表索引，用于检查图文断链。
- `results/` 和 `tables/table_index.json` 是结果、指标、结论和表格证据交接单；示例里会标记真实建模结果待补。
- `OUTPUT_LAYOUT.md` 和 `code/README.md` 说明当前赛题的生成代码、图表、表格、微单元和 Word 草稿应该放在哪里。
- `tasks.json` 是微单元任务清单。
- `final_paper.docx` 是最终 Word 草稿。

示例中的图表和正文是 workflow 草稿，用于证明链路可跑。真实赛题中，Agent 应读取这些 JSON 和 `scripts/` 样板，再结合当前数据字段、模型输出和图表需求，把赛题专用代码生成或修改到 `paper_output/code/`，再重跑 QA 和正文生成。
