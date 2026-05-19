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
赛题解析 -> 模型选择 -> 数据获取 -> 数据清洗与可视化 -> QA 门禁 -> 微单元生成 -> 合并成稿
```

本仓库按“完整 skill 包”分发，不把 skill 压平成单个 Markdown 文件。每个 skill 都保留自己的 `SKILL.md`、`scripts/`、`references/`、memory 文件等资源。

当前升级后的关键数据契约是 `paper_output/step1/problem_analysis.json`：先把赛题拆成结构化子问题、模型路线、验证计划和建议图表，再让 QA 根据它动态生成 `tasks.json`。这样整套 skill 不再只是顺序提示，而是能用同一份结构化题意把后续生成环节串起来。

## 选择你的 Agent

根据你使用的平台，只复制对应包即可：

| 平台 | 复制来源 | 复制到你的项目 | 原生入口 |
|---|---|---|---|
| Trae | `packages/trae/.trae/skills/` | `.trae/skills/` | `.trae/skills/*/SKILL.md` |
| Claude Code | `packages/claude/.claude/skills/` + `packages/claude/CLAUDE.md` | `.claude/skills/` + `CLAUDE.md` | `.claude/skills/*/SKILL.md` |
| Codex | `packages/codex/skills/` + `packages/codex/AGENTS.md` | `skills/` + `AGENTS.md` | `skills/*/SKILL.md` |

详细安装步骤见 [Agent 安装指南](docs/agent-install-guide.md)。

## 仓库结构

```text
MathModel-Skill/
├── README.md
├── assets/                       # 项目 logo 等展示资源
├── docs/                         # 安装与使用文档
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

### 4. 一键运行

按你安装的平台执行：

```bash
# Trae
python .trae/skills/paper-workflow-orchestrator/scripts/run_all.py

# Claude Code
python .claude/skills/paper-workflow-orchestrator/scripts/run_all.py

# Codex
python skills/paper-workflow-orchestrator/scripts/run_all.py
```

也可以直接对 Agent 说：

```text
开始生成数学建模论文
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
├── final_paper.docx              # Word 最终稿
├── final_paper.md                # Markdown 合并稿
├── tasks.json                    # 微单元任务清单
├── ref_check.md                  # 引用/图表/公式断链检查
├── data_cleaned/                 # 清洗后的数据
└── figures/                      # 自动生成的图表
```

## 核心能力

这套流程包含 7 个论文生产核心 skills，另有 1 个辅助记忆 skill。

### 规划与模型选择

- `problem-doc-model-selector`：解析赛题 PDF/Word，抽取每一问的任务、约束、输入输出和模型方向。
- `modeling-paper-rubric-and-model-selector`：对齐评分点、论文结构和模型路线，补全“为什么这样建模能拿分”。

### 数据获取、清洗与可视化

- `authoritative-data-harvester`：定位权威公开数据源，优先 API 或官方批量下载。
- `data-cleaning-and-visualization`：提供数据清洗、图表生成和可视化代码样板，帮助 Agent 按更稳定的格式生成论文可用图表。

### 论文生成与质量审计

- `quality-assurance-auditor`：作为全局门禁，优先读取 `problem_analysis.json` 动态生成任务清单，并检查输入目录、微单元进度和最终产物。
- `paper-micro-unit-generator`：把论文拆成微单元，批量生成并合并为 Markdown/Word。
- `paper-workflow-orchestrator`：中心编排器，一键串联数据、QA、生成、合并和 Word 导出。

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
- 给 Agent 一个可参考的代码结构，避免从空白状态随意发挥。
- 在真实赛题中，应该先分析当前题目的数据格式和建模需求，再引用 `scripts/` 中的写法二次修改，或基于这些脚本重新生成适配当前赛题的新代码。

也就是说，`scripts/` 既可以在简单场景下直接运行，也可以在复杂赛题中作为“代码级提示词”使用：让 Trae、Claude Code、Codex 先读现有脚本，再按当前赛题的数据表结构、指标含义和图表要求生成新的处理代码。

## 局部重跑

如果只想重跑某一步，可以按平台路径替换命令前缀。

以 Trae 为例：

```bash
# 数据清洗与可视化
python .trae/skills/data-cleaning-and-visualization/scripts/run_pipeline.py

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
