# Output Layout

MathModel Skill 的生成物必须有固定位置。这个约定的目的不是把项目做成黑盒系统，而是让 Trae、Claude Code、Codex 在真实赛题中知道“该读哪里、该写哪里、哪些文件可以二次修改”。

核心原则：

- Skill 包目录只放可复用能力和样板，不放当前赛题生成物。
- 当前赛题的所有运行产物统一写入 `paper_output/`。
- 当前赛题专用代码统一写入 `paper_output/code/`，不要写回 `.trae/skills/`、`.claude/skills/` 或 `skills/`。
- 所有 JSON 契约和索引中的路径使用相对路径。

## Top-Level Layout

```text
your-project/
├── problem_files/                 # 赛题 PDF/Word 和官方附件数据
├── crawled_data/                  # 可选，外部权威数据或手动补充数据
├── .trae/skills/                  # Trae skill 包，或
├── .claude/skills/                # Claude Code skill 包，或
├── skills/                        # Codex skill 包
└── paper_output/                  # 当前赛题所有生成物
```

## paper_output

```text
paper_output/
├── OUTPUT_LAYOUT.md               # 自动生成的输出位置说明
├── step1/                         # 赛题结构化分析
├── plan/                          # 模型路线、评分、数据和图表计划
├── code/                          # 当前赛题专用代码
│   ├── README.md                   # 当前赛题代码工作区说明
│   ├── data_processing/README.md
│   ├── visualization/README.md
│   ├── modeling/README.md
│   └── qa/README.md
├── data_cleaned/                  # 清洗后的数据
├── figures/                       # 论文图片和 EDA 图
├── tables/                        # 论文表格和 table_index.json
├── results/                       # 模型结果、指标和结论契约
├── micro_units/                   # 微单元文本
├── tasks.json                     # 微单元任务清单
├── generate_log.json              # 微单元生成日志
├── final_paper.md                 # Markdown 草稿
├── final_paper.docx               # Word 草稿
└── ref_check.md                   # 引用、图表和公式断链检查
```

## Generated Code

当前赛题专用代码放在：

```text
paper_output/code/
├── README.md                       # 总说明：当前赛题代码只写这里
├── data_processing/
│   ├── README.md
│   └── ...                        # Agent 根据当前附件字段生成或修改的数据处理代码
├── visualization/
│   ├── README.md
│   └── ...                        # Agent 根据当前图表需求生成或修改的绘图代码
├── modeling/
│   ├── run_modeling.py            # 建议的建模统一入口，后续生成
│   ├── result_contract_io.py      # 写回 results/tables 契约的 helper，后续生成
│   ├── q1_model.py                # 问题一专用建模代码，后续生成
│   ├── q2_model.py                # 问题二专用建模代码，后续生成
│   ├── q3_model.py                # 问题三专用建模代码，后续生成
│   └── README.md                  # 当前脚本会先生成工作区说明
└── qa/
    ├── README.md
    └── ...                        # 可选，当前赛题专用检查脚本
```

`packages/*/skills/*/scripts/` 里的代码是 skill 自带样板；`paper_output/code/` 里的代码是当前赛题产物。真实赛题中，Agent 应先读取 skill 样板，再在 `paper_output/code/` 中生成或修改专用代码。
`paper-workflow-orchestrator/scripts/prepare_output_layout.py` 会先创建这些目录和 README，帮助 Agent 在开工前明确落点；这一步只规划工作区，不替代真实的数据处理、绘图和建模。

## Data And Figures

```text
paper_output/data_cleaned/
└── *_cleaned.csv                  # 统一清洗后的建模输入数据

paper_output/figures/
├── fig_q1_*.png                   # 推荐的论文级图表路径
├── fig_q2_*.png
├── fig_q3_*.png
└── <dataset_name>/                # 基础 EDA 图表可使用数据集子目录
```

图表索引固定为：

```text
paper_output/figure_index.json
```

正文中引用的图片必须能在 `figure_index.json` 中追溯。格式化、论文级图表优先放在 `paper_output/figures/` 根目录或按 `fig_q*_*.png` 命名；基础探索图可以放入数据集子目录。

## Tables And Results

```text
paper_output/results/
├── model_results.json             # 每问模型输出、参数、方案、预测值或排序结果
├── metrics.json                   # RMSE、MAE、F1、得分、约束满足率等指标
└── conclusions.json               # 每问回扣题目的结构化结论

paper_output/tables/
├── table_index.json               # 表格索引、表题、用途、关联 question_id 和路径
├── table_q1_*.csv
├── table_q2_*.csv
└── table_q3_*.csv
```

当前赛题专用建模代码应把真实结果写回 `paper_output/results/` 和 `paper_output/tables/`。如果某些文件仍标记 `draft_contract`、`to_be_filled` 或 `needs_real_modeling`，最终正文不能把它当成真实比赛结果。

## Micro Units And Word

```text
paper_output/tasks.json
paper_output/micro_units/*.txt
paper_output/final_paper.md
paper_output/final_paper.docx
paper_output/ref_check.md
```

`tasks.json` 是正文生成的唯一任务清单入口。微单元生成器应优先读取其中的 `main_model`、`model_reason`、`validation_plan`、`figure_suggestions`、`result_summary`、`key_metrics`、`tables` 和 `conclusions`。

## Ownership

| Area | Owner Skill | Purpose |
|---|---|---|
| `paper_output/step1/` | `problem-doc-model-selector` | 题意和子问题结构化 |
| `paper_output/plan/` | `modeling-paper-rubric-and-model-selector` / `data-cleaning-and-visualization` | 模型路线、评分、数据和图表计划 |
| `paper_output/code/data_processing/` | Agent + `data-cleaning-and-visualization` | 当前赛题数据处理代码 |
| `paper_output/code/visualization/` | Agent + `data-cleaning-and-visualization` | 当前赛题绘图代码 |
| `paper_output/code/modeling/` | Agent + `model-code-and-result-generator` | 当前赛题建模代码 |
| `paper_output/data_cleaned/` | `data-cleaning-and-visualization` | 清洗后的输入数据 |
| `paper_output/figures/` | `data-cleaning-and-visualization` / Agent | 论文图片 |
| `paper_output/tables/` | `model-code-and-result-generator` / Agent | 论文表格 |
| `paper_output/results/` | `model-code-and-result-generator` / Agent | 模型结果、指标和结论 |
| `paper_output/tasks.json` | `quality-assurance-auditor` | 微单元任务清单 |
| `paper_output/micro_units/` | `paper-micro-unit-generator` | 微单元文本 |
| `paper_output/final_paper.*` | `paper-micro-unit-generator` | Markdown 与 Word 草稿 |
