# MathModel Skill for Claude Code

这是 MathModel Skill 的 Claude Code 原生包。

本目录按完整 skill 包分发，不是把 skill 压平成单个 Markdown 文件。每个 skill 都保留自己的 `SKILL.md`、`scripts/`、`references/` 和其他资源。

```text
claude/
├── CLAUDE.md
└── .claude/
    └── skills/
        ├── problem-doc-model-selector/
        ├── modeling-paper-rubric-and-model-selector/
        ├── authoritative-data-harvester/
        ├── data-cleaning-and-visualization/
        ├── model-code-and-result-generator/
        ├── quality-assurance-auditor/
        ├── paper-micro-unit-generator/
        ├── paper-workflow-orchestrator/
        └── context-memory-keeper/
```

## 安装方式

把本目录下的 `CLAUDE.md` 和 `.claude/skills/` 复制到你的 Claude Code 项目根目录：

```text
your-mathmodel-project/
├── CLAUDE.md
└── .claude/
    └── skills/
```

## 使用方式

在项目根目录准备输入目录：

```text
problem_files/      # 放赛题 PDF/Word 和官方附件数据
crawled_data/       # 可选，放外部补充数据
```

第一次使用建议先复制仓库示例：

```text
examples/quickstart/problem_files/ -> your-mathmodel-project/problem_files/
```

然后在 Claude Code 中说：

```text
开始生成数学建模论文
```

Claude Code 应优先读取：

```text
.claude/skills/paper-workflow-orchestrator/SKILL.md
```

这是 MathModel Skill 的总入口，负责判断当前阶段并路由到其他 skill；用户不需要手动选择从哪个 skill 开始。

如果只是验证安装，也可以手动运行随 skill 附带的辅助脚本：

```bash
python .claude/skills/paper-workflow-orchestrator/scripts/quickstart_run.py
```

该命令只用于 quickstart / smoke test，输出是验证草稿，不代表正式比赛论文质量。正式赛题应由 Claude Code 先读取总控 skill，生成当前赛题专用代码、真实结果和证据门禁报告后再全局写作。

## 输出位置

```text
paper_output/OUTPUT_LAYOUT.md
paper_output/final_paper.docx
paper_output/final_paper.md
paper_output/code/data_processing/
paper_output/code/visualization/
paper_output/code/modeling/
paper_output/code/modeling/run_modeling.py
paper_output/code/modeling/result_contract_io.py
paper_output/code/modeling/q1_model.py
paper_output/code/modeling/q2_model.py
paper_output/code/modeling/q3_model.py
paper_output/code/qa/
paper_output/plan/model_route.json
paper_output/plan/data_plan.json
paper_output/plan/visualization_plan.json
paper_output/figure_index.json
paper_output/results/model_results.json
paper_output/results/metrics.json
paper_output/results/conclusions.json
paper_output/tables/table_index.json
paper_output/tasks.json
paper_output/ref_check.md
paper_output/data_cleaned/
paper_output/figures/
```

当前赛题专用代码统一放在 `paper_output/code/`：数据处理代码放 `data_processing/`，绘图代码放 `visualization/`，q1/q2/q3 建模脚手架和二次修改代码放 `modeling/`，检查脚本放 `qa/`。`.claude/skills/*/scripts/` 只作为可复用模板和代码级提示词，不写入当前赛题产物。

## 说明

- Claude Code 包基于 Trae 原版 skill 包适配。
- 适配只改变平台路径和平台称呼，不改变工作流设计。
- 每个 skill 都是完整文件夹，保留脚本和参考材料。
- `model-code-and-result-generator` 会生成结果证据契约和 `q*_model.py` 建模代码脚手架，不承诺自动解决所有赛题建模。
