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
python .claude/skills/paper-workflow-orchestrator/scripts/run_all.py
```

## 输出位置

```text
paper_output/final_paper.docx
paper_output/final_paper.md
paper_output/plan/model_route.json
paper_output/plan/data_plan.json
paper_output/plan/visualization_plan.json
paper_output/figure_index.json
paper_output/tasks.json
paper_output/ref_check.md
paper_output/data_cleaned/
paper_output/figures/
```

## 说明

- Claude Code 包基于 Trae 原版 skill 包适配。
- 适配只改变平台路径和平台称呼，不改变工作流设计。
- 每个 skill 都是完整文件夹，保留脚本和参考材料。
