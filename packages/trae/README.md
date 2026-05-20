# MathModel Skill for Trae

这是 MathModel Skill 的 Trae 原生包。

本目录保留当前最成熟的原版 skill 结构：

```text
trae/
└── .trae/
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

把本目录下的 `.trae/skills/` 复制到你的 Trae 项目根目录：

```text
your-mathmodel-project/
└── .trae/
    └── skills/
```

如果你的项目里已经有 `.trae/skills/`，可以只复制需要的 skill 文件夹。

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

然后对 Trae 说：

```text
开始生成数学建模论文
```

Trae 应先读取 `.trae/skills/paper-workflow-orchestrator/SKILL.md`。这是 MathModel Skill 的总入口，负责判断当前阶段并路由到其他 skill；用户不需要手动选择从哪个 skill 开始。

如果只是验证安装，也可以手动运行随 skill 附带的辅助脚本：

```bash
python .trae/skills/paper-workflow-orchestrator/scripts/run_all.py
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

- Trae 包是当前 canonical skill source 的原版复制。
- 本包按完整 skill 文件夹分发，包含 `SKILL.md`、`scripts/`、`references/` 和 memory 文件。
- `context-memory-keeper` 是辅助记忆 skill，不计入 7 个论文生产核心 skill。
