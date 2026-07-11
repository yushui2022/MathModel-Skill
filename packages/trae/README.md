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
        ├── model-code-and-result-generator/
        ├── quality-assurance-auditor/
        ├── paper-formal-writer/
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
python .trae/skills/paper-workflow-orchestrator/scripts/quickstart_run.py
```

该命令只用于 quickstart / smoke test，输出是验证草稿，不代表正式比赛论文质量。正式赛题应由 Trae 先读取总控 skill，生成当前赛题专用代码、真实结果和证据门禁报告后，再调用 `paper-formal-writer` 生成正式 outline、全局写作 `final_paper_source.md`、排版 Word 并通过格式门禁。

## 输出位置

```text
paper_output/OUTPUT_LAYOUT.md
paper_output/final_paper.docx
paper_output/final_paper.md
paper_output/final_paper_source.md
paper_output/format_check_report.md
paper_output/format_check_report.json
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
paper_output/plan/paper_outline.json
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

当前赛题专用代码统一放在 `paper_output/code/`：数据处理代码放 `data_processing/`，绘图代码放 `visualization/`，q1/q2/q3 建模脚手架和二次修改代码放 `modeling/`，检查脚本放 `qa/`。`.trae/skills/*/scripts/` 只作为可复用模板和代码级提示词，不写入当前赛题产物。

## 说明

- Trae 包是当前 canonical skill source 的原版复制。
- 本包按完整 skill 文件夹分发，包含 `SKILL.md`、`scripts/`、`references/` 和 memory 文件。
- `model-code-and-result-generator` 是结果证据辅助 skill，用于生成结果、指标、结论、表格契约和 `q*_model.py` 建模代码脚手架；它不是万能自动建模系统。
- `paper-formal-writer` 负责 CUMCM 正式论文范式、`1 / 1.1 / 1.1.1` 标题、动态篇幅、可编辑 Word OMML 公式、正文引文、Word 排版和 required render 格式门禁。
- `context-memory-keeper` 是辅助记忆 skill，不计入 8 个论文生产核心 skill。
