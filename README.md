<div align="center">
  <img src="./assets/mathe-skill-logo.svg" alt="MathModel Skill logo" width="132" height="132" />

# MathModel Skill

### 数学建模论文自动化多 Agent 原生 Skill 包

#### 为 Trae、Claude Code、Codex 设计的完整数学建模工作流

[![Core Skills](https://img.shields.io/badge/core%20skills-7-2563eb)](#核心能力)
[![Trae](https://img.shields.io/badge/Trae-native-0ea5e9)](#选择你的-agent)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-native-7c3aed)](#选择你的-agent)
[![Codex](https://img.shields.io/badge/Codex-native-111827)](#选择你的-agent)
[![Output](https://img.shields.io/badge/output-docx%20%2B%20markdown-16a34a)](#输出目录)

</div>

MathModel Skill 是一套面向数学建模比赛的完整 skill 工作流，把常见流程固化为可复用的 Agent 原生能力：

```text
赛题解析 -> 模型选择 -> 数据获取 -> 数据清洗与可视化 -> 结果证据 -> QA 门禁 -> 微单元生成 -> 合并成稿
```

本仓库按“完整 skill 包”分发，不把 skill 压平成单个 Markdown 文件。每个 skill 都保留自己的 `SKILL.md`、`scripts/`、`references/`、memory 文件等资源。

这套 workflow 通过少量 JSON 文件沉淀模型路线、评分证据、数据处理、图表计划和结果证据，让不同 skill 能稳定交接上下文。JSON 是交接单，不是黑盒系统；详细规则见 [工作流契约说明](docs/workflow-contracts.md)。

## 选择你的 Agent

根据你使用的平台，只复制对应包即可：

| 平台 | 复制来源 | 复制到你的项目 | 原生入口 |
|---|---|---|---|
| Trae | `packages/trae/.trae/skills/` | `.trae/skills/` | `.trae/skills/*/SKILL.md` |
| Claude Code | `packages/claude/.claude/skills/` + `packages/claude/CLAUDE.md` | `.claude/skills/` + `CLAUDE.md` | `.claude/skills/*/SKILL.md` |
| Codex | `packages/codex/skills/` + `packages/codex/AGENTS.md` | `skills/` + `AGENTS.md` | `skills/*/SKILL.md` |

详细安装步骤见 [Agent 安装指南](docs/agent-install-guide.md)。

## 不知道从哪个 Skill 开始？

不用让用户选择多个 skill。把赛题和附件放进 `problem_files/` 后，直接对 Agent 说：

```text
开始生成数学建模论文
```

三端入口文件和 skill 元数据都会指向 `paper-workflow-orchestrator`。它是 MathModel Skill 的总入口，负责判断当前阶段，并路由到题意解析、模型路线、数据图表、QA、微单元生成等子 skill。

## 3 分钟跑通示例

仓库内置了一个最小示例：

```text
examples/quickstart/problem_files/
├── sample_problem.txt
└── sample_data.csv
```

你可以新建空项目，复制对应平台 skill 包，再复制这个 `problem_files/` 目录，然后让 Agent 使用 `paper-workflow-orchestrator`。如果只是验证安装，也可以手动运行随 skill 附带的 `run_all.py`。完整步骤见 [Quickstart Demo Walkthrough](docs/demo-walkthrough.md)。

这个示例用于验证安装和 workflow 是否跑通；真实赛题中仍应让 Agent 根据当前题目、附件字段和模型输出二次修改数据处理、建模和图表代码。

## 仓库结构

```text
MathModel-Skill/
├── README.md
├── assets/                       # 项目 logo 等展示资源
├── docs/                         # 安装与使用文档
├── examples/                     # 可直接跑通的 quickstart 示例
├── packages/                     # 三端原生 skill 分发包
│   ├── trae/                     # Trae 原生包，也是当前 canonical source
│   ├── claude/                   # Claude Code 原生包
│   └── codex/                    # Codex 原生包
├── requirements.txt              # Python 依赖
└── .gitignore
```

`packages/trae/.trae/skills/` 是当前最成熟的原版 skill 包；Claude Code 与 Codex 包以它为基础做平台路径适配。

## 快速使用

### 1. 安装依赖

在你的数学建模项目根目录安装依赖：

```bash
pip install -r requirements.txt
```

如果你只复制了某个平台包，也可以从本仓库复制 `requirements.txt` 到你的项目中。

### 2. 复制对应平台包

Trae 用户：

```text
packages/trae/.trae/skills/ -> your-project/.trae/skills/
```

Claude Code 用户：

```text
packages/claude/.claude/skills/ -> your-project/.claude/skills/
packages/claude/CLAUDE.md       -> your-project/CLAUDE.md
```

Codex 用户：

```text
packages/codex/skills/    -> your-project/skills/
packages/codex/AGENTS.md  -> your-project/AGENTS.md
```

### 3. 放入赛题与附件

在你的项目根目录创建：

```text
problem_files/      # 放赛题 PDF/Word 和官方附件数据
crawled_data/       # 可选，放外部补充数据
```

也可以先复制 `examples/quickstart/problem_files/` 跑通最小示例。

### 4. 让 Agent 自动使用

推荐方式是直接对 Agent 说：

```text
开始生成数学建模论文
```

Agent 应先读取 `paper-workflow-orchestrator/SKILL.md`，再按 skill 里定义的流程调用其他 skill。`run_all.py` 只是这个总编排 skill 附带的可执行辅助脚本，用来把已确定的流程顺序稳定串起来。

### 5. 可选：手动验证安装

如果你想确认 skill 包路径、Python 依赖和示例 workflow 是否能跑通，可以手动执行验证命令：

按你安装的平台执行：

```bash
# Trae
python .trae/skills/paper-workflow-orchestrator/scripts/run_all.py

# Claude Code
python .claude/skills/paper-workflow-orchestrator/scripts/run_all.py

# Codex
python skills/paper-workflow-orchestrator/scripts/run_all.py
```

如果 Windows PowerShell 出现 GBK 编码问题，先执行：

```powershell
$env:PYTHONIOENCODING="utf-8"
```

## 输出目录

所有平台的输入输出约定一致：

```text
paper_output/
├── step1/
│   ├── problem_analysis.json     # 结构化题意分析，后续 skill 的数据契约
│   ├── A_题意对齐.md
│   ├── B_论文大纲.md
│   ├── C_评分点对齐表.md
│   └── D_模型路线.json
├── plan/
│   ├── model_route.json          # 每问模型路线与图表证据
│   ├── rubric_alignment.json     # 评分点与证据映射
│   ├── scoring_strategy.md       # 给人和 Agent 看的评分闭环说明
│   ├── data_plan.json            # 数据字段、清洗任务与子问题链接
│   └── visualization_plan.json   # 建议图表、图题、用途与输出路径
├── figure_index.json             # 图表计划索引
├── results/
│   ├── model_results.json        # 模型输出、参数、方案、预测值等结果证据
│   ├── metrics.json              # 误差、得分、约束满足率等评价指标
│   └── conclusions.json          # 每问回扣题目的结构化结论
├── tables/
│   ├── table_index.json          # 表格索引、表题、用途和路径
│   └── *.csv                     # 参数表、结果表、误差表、对比表等
├── final_paper.docx              # Word 最终稿
├── final_paper.md                # Markdown 合并稿
├── tasks.json                    # 微单元任务清单
├── ref_check.md                  # 引用/图表/公式断链检查
├── data_cleaned/                 # 清洗后的数据
└── figures/                      # 自动生成的图表
```

## JSON 通信契约

MathModel Skill 的 skill 之间不靠“记住上一轮对话”硬撑长流程，而是把关键中间结论写入固定 JSON，再由下一个 skill 读取：

```text
problem_analysis.json -> model_route.json / rubric_alignment.json -> data_plan.json / visualization_plan.json -> model_results.json / metrics.json / conclusions.json / table_index.json -> tasks.json -> micro_units -> final_paper
```

| 文件 | 生成者 | 读取者 | 作用 |
|---|---|---|---|
| `paper_output/step1/problem_analysis.json` | `problem-doc-model-selector` | 模型路线、QA、微单元生成 | 结构化保存题意、子问题、任务类型和附件画像 |
| `paper_output/plan/model_route.json` | `modeling-paper-rubric-and-model-selector` | QA、微单元生成 | 保存每一问的主模型、基线模型、验证计划和建议图表 |
| `paper_output/plan/rubric_alignment.json` | `modeling-paper-rubric-and-model-selector` | QA、微单元生成 | 保存评分点、证据形式和论文落点 |
| `paper_output/plan/data_plan.json` | `data-cleaning-and-visualization` | QA、微单元生成、后续代码生成 | 保存数据文件、字段画像、清洗任务和子问题链接 |
| `paper_output/plan/visualization_plan.json` | `data-cleaning-and-visualization` | QA、微单元生成、后续绘图代码 | 保存建议图表、图题、用途、候选字段和输出路径 |
| `paper_output/figure_index.json` | `data-cleaning-and-visualization` | QA、正文引用检查 | 保存计划图表索引，帮助检查图文是否断链 |
| `paper_output/results/model_results.json` | `model-code-and-result-generator` | QA、微单元生成 | 保存每问模型输出、参数、方案、预测值或排序结果 |
| `paper_output/results/metrics.json` | `model-code-and-result-generator` | QA、微单元生成 | 保存误差、得分、约束满足率、稳定性等评价指标 |
| `paper_output/results/conclusions.json` | `model-code-and-result-generator` | QA、微单元生成 | 保存每问可回扣题目的结构化结论 |
| `paper_output/tables/table_index.json` | `model-code-and-result-generator` | QA、微单元生成、正文引用检查 | 保存表格索引、表题、用途和相对路径 |
| `paper_output/tasks.json` | `quality-assurance-auditor` | `paper-micro-unit-generator` | 保存微单元任务清单，以及正文生成所需的模型路线、评分证据和结果证据字段 |

## 核心能力

这套流程包含 7 个论文生产核心 skills，另有结果证据与上下文记忆等辅助 skill。

### 规划与模型选择

- `problem-doc-model-selector`：解析赛题 PDF/Word，抽取每一问的任务、约束、输入输出和模型方向。
- `modeling-paper-rubric-and-model-selector`：读取 `problem_analysis.json`，生成 `model_route.json`、`rubric_alignment.json` 和 `scoring_strategy.md`，补全“为什么这样建模能拿分”。

### 数据获取、清洗与可视化

- `authoritative-data-harvester`：定位权威公开数据源，优先 API 或官方批量下载。
- `data-cleaning-and-visualization`：提供数据清洗、图表生成和论文级可视化代码样板，并生成数据/图表计划，帮助 Agent 按更稳定的格式产出论文可用图表。
- `model-code-and-result-generator`：根据模型路线、数据计划和清洗数据生成结果、指标、结论和表格证据契约。它不是万能自动建模系统，真实赛题仍应由 Agent 基于当前数据二次生成或修改专用建模代码。

### 论文生成与质量审计

- `quality-assurance-auditor`：作为全局门禁，优先读取 `model_route.json` 和 `rubric_alignment.json` 动态生成任务清单，并检查输入目录、微单元进度和最终产物。
- `paper-micro-unit-generator`：把论文拆成微单元，批量生成并合并为 Markdown/Word。
- `paper-workflow-orchestrator`：中心编排器，指导 Agent 按顺序串联数据、QA、生成、合并和 Word 导出；其中 `scripts/run_all.py` 可作为可选的稳定执行器。

### 辅助记忆

- `context-memory-keeper`：维护长期准则、短期工作台和外部文献/数据源索引。

## Skill 包结构

每个 skill 都是完整文件夹：

```text
skill-name/
├── SKILL.md
├── scripts/
├── references/
├── assets/
└── 其他资源
```

并不是每个 skill 都有 `scripts/`、`references/` 或 `assets/`，但只要原版存在，平台包里都会完整保留。

## scripts 的定位

数学建模赛题的数据结构、字段名称、单位口径、附件格式和需要展示的图表类型通常都不一样，所以 `scripts/` 里的代码不应被理解成“所有赛题都能直接复用的万能脚本”。

这些脚本更重要的价值，是作为高质量代码提示词和规范样板：

- 告诉 Agent 数据清洗应该如何组织输入、输出和中间产物。
- 告诉 Agent 图表生成应保持怎样的尺寸、配色、标注、保存路径和论文引用口径。
- 提供预测对比图、残差图、敏感性分析图、模型/方案对比图、权重图、排序图、热力图等论文级图表代码样板。
- 给 Agent 一个可参考的代码结构，避免从空白状态随意发挥。
- 在真实赛题中，应该先分析当前题目的数据格式和建模需求，再引用 `scripts/` 中的写法二次修改，或基于这些脚本重新生成适配当前赛题的新代码。

也就是说，`scripts/` 既可以在简单场景下直接运行，也可以在复杂赛题中作为“代码级提示词”使用：让 Trae、Claude Code、Codex 先读现有脚本，再按当前赛题的数据表结构、指标含义和图表要求生成新的处理代码。

## 可选：局部重跑

如果你在调试、验证安装或只想重跑某一步，可以按平台路径替换命令前缀。普通使用时不需要手动执行这些脚本，Agent 会根据对应 skill 的 `SKILL.md` 决定何时调用。

以 Trae 为例：

```bash
# 赛题结构化分析
python .trae/skills/problem-doc-model-selector/scripts/analyze_problem.py

# 模型路线与评分闭环
python .trae/skills/modeling-paper-rubric-and-model-selector/scripts/build_model_route.py

# 数据与图表计划、清洗与可视化
python .trae/skills/data-cleaning-and-visualization/scripts/run_pipeline.py

# 结果证据契约
python .trae/skills/model-code-and-result-generator/scripts/build_result_contracts.py

# QA 与任务清单
python .trae/skills/quality-assurance-auditor/scripts/pipeline.py

# 微单元生成
python .trae/skills/paper-micro-unit-generator/scripts/generate_all_offline.py

# 合并成稿
python .trae/skills/paper-micro-unit-generator/scripts/merge.py
```

Claude Code 把 `.trae/skills/` 换成 `.claude/skills/`；Codex 把 `.trae/skills/` 换成 `skills/`。

## 一句话总结

MathModel Skill 的价值不是“一个提示词写完整篇论文”，而是把数学建模比赛拆成可控、可检查、可重跑的完整 skill 工作流。Trae、Claude Code、Codex 用户都可以下载对应原生包，自主接入自己的 Agent 工作环境。
