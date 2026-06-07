<div align="center">
  <img src="./assets/mathe-skill-logo.svg" alt="MathModel Skill logo" width="132" height="132" />

# MathModel Skill

### Agent-native 数学建模工作流 Skill 包

#### 为 Trae、Claude Code、Codex 设计的完整数学建模工作流

[![Workflow Skills](https://img.shields.io/badge/workflow%20skills-10-2563eb)](#核心能力)
[![Trae](https://img.shields.io/badge/Trae-native-0ea5e9)](#选择你的-agent)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-native-7c3aed)](#选择你的-agent)
[![Codex](https://img.shields.io/badge/Codex-native-111827)](#选择你的-agent)
[![Output](https://img.shields.io/badge/output-docx%20%2B%20markdown-16a34a)](#输出目录)

</div>

MathModel Skill 是一套面向数学建模比赛的 Agent-native skill 工作流，不是黑盒一键论文生成器。受长上下文注意力衰减影响，单次一键生成很难稳定产出具备省一竞争力的完整论文。因此，v2.0.0 将论文生产升级为可恢复、可校验、可继续的 workflow。安装好 skill 后，用户只需输入“继续”，coding agent 会在 preflight、workflow guard、证据门禁和格式门禁的引导下，逐步完成读题、建模、运行代码、生成结果、撰写正文和 Word 成稿。它把常见流程固化为可复用的 Agent 原生能力，让 Codex、Claude Code、Trae 知道先读什么、代码写到哪里、结果如何沉淀、正文如何引用证据。

```text
读题 -> 拆题 -> 模型路线 -> 判断附件性质 -> 生成/修改赛题专用代码 -> 运行代码 -> 真实图表/表格/结果 -> 证据门禁 -> 正式 outline -> Agent 全局写作 -> Word 排版 -> 格式门禁 -> 最终 QA
```

本仓库按“完整 skill 包”分发，不把 skill 压平成单个 Markdown 文件。每个 skill 都保留自己的 `SKILL.md`、`scripts/`、`references/`、memory 文件等资源。

这套 workflow 通过少量 JSON 文件沉淀模型路线、评分证据、数据处理、图表计划和结果证据，让不同 skill 能稳定交接上下文。JSON 是交接单，不是黑盒系统；详细规则见 [工作流契约说明](docs/workflow-contracts.md)。

为避免长对话中 Agent 忘记阶段、跳过 skill 或把附件读错，主流程已经加入可执行防漂移机制：正式任务先由 `preflight_check.py` 体检 `problem_files/` 和依赖；每个 skill 启动前用 `workflow_guard.py --skill ...` 检查前置阶段；上下文变长或阶段不确定时用 `workflow_guard.py --status` 恢复当前 S0-S8 位置；`context-memory-keeper` 会把断点写入 `paper_output/context/workflow_memory.json`。也就是说，流程不是靠 README 记忆，而是靠脚本报告和文件证据恢复。

所有生成物都有固定位置：skill 包目录只放可复用能力，当前赛题产物统一放 `paper_output/`；当前赛题专用代码统一放 `paper_output/code/`。完整位置规划见 [Output Layout](docs/output-layout.md)。

原有高质量提示词不会废弃。微单元提示词、评分闭环提示词、模型选择提示词和 QA 审稿提示词仍是本项目的核心资产；它们用于指导 Agent 写作、审稿、拆解和局部重写，而不是强制机械拼接正文。见 [Prompt Assets](docs/prompt-assets.md)。

正式论文范式由新增 `paper-formal-writer` 负责：证据门禁通过后生成 `paper_outline.json`，约束 Agent 写 `final_paper_source.md`，再用脚本生成正式 Word 并检查 `1 / 1.1 / 1.1.1` 标题、`18000-25000` 字数、图表引用和参考文献。详见 [CUMCM Paper Standard](docs/cumcm-paper-standard.md) 和 [Formal Paper Authoring](docs/formal-paper-authoring.md)。

仓库已提交一个 CUMCM 2024 B 题正式生成样例，包含 Word、Markdown 源稿、证据门禁、格式门禁、图表、表格和赛题专用代码。先看 [正式论文生成流程与结果样例](docs/generated-demo-workflow.md)，再打开 [B 题样例 Word](examples/cumcm2024-b-demo/paper_output/final_paper.docx) 检查实际效果。

<div align="center">
  <p><strong>如果你想了解更多我的数学建模、AI 工作流和实战内容，可以扫描下面的小红书二维码。</strong></p>
  <img src="./assets/xiaohongshu-qr.jpg" alt="小红书二维码" width="180" />
</div>

## 关于 LaTeX 版本

主分支继续以 Word 交付为默认主流程，避免给大多数用户增加额外安装和排版步骤。少数需要 LaTeX / PDF 交付的用户，可以切到 [`Latex` 分支](https://github.com/yushui2022/MathModel-Skill/tree/Latex) 使用可选 LaTeX 导出能力。

`Latex` 分支不是另一套“一键生成论文”流程，而是在同一条证据链之后，从 `paper_output/final_paper_source.md` 额外导出 `final_paper.tex`，本机安装 `xelatex` 时可继续编译 `final_paper.pdf`。LaTeX 输出同样要求证据门禁通过；主分支不会默认加入这一步。

## 最快开始

如果你只是想直接使用，不想先读完整架构，按下面 5 步走：

1. 在下一节选择你的 Agent，下载对应 zip 包。
2. 解压到你的数学建模比赛项目根目录。
3. 在项目根目录创建 `problem_files/`，放入赛题 PDF/Word 和官方附件。
4. 安装依赖：

```bash
pip install -r requirements.txt
```

5. 对 Agent 说：

```text
我已经把赛题和附件放进 problem_files/。
请使用 MathModel Skill，从 paper-workflow-orchestrator 开始，不要先跑 quickstart。
请按正式比赛流程完成：读题、拆题、模型路线、附件性质判断、生成并运行赛题专用代码、产出真实结果/图表/表格/指标/结论、通过证据门禁、调用 paper-formal-writer 正式成稿、生成 Word 并通过格式门禁。
所有当前赛题代码写入 paper_output/code/，所有结果和论文产物写入 paper_output/。
如果对当前阶段不确定，请先运行 workflow_guard.py --status，并按报告中的 next_step 和 recommended_skill 继续。
每个阶段完成后，请更新 paper_output/context/workflow_memory.json，方便长对话或中断后恢复。
证据门禁或格式门禁未通过时，不要把 Word 称为最终稿。
```

完成后优先看：

```text
paper_output/final_paper.docx
paper_output/qa/evidence_gate_report.md
paper_output/format_check_report.md
```

## 选择你的 Agent

根据你使用的平台，只复制对应包即可：

| 平台 | 推荐下载包 | 源码复制来源 | 复制到你的项目 | 原生入口 |
|---|---|---|---|---|
| Trae | `dist/MathModel-Skill-Trae.zip` | `packages/trae/.trae/skills/` | `.trae/skills/` | `.trae/skills/*/SKILL.md` |
| Claude Code | `dist/MathModel-Skill-Claude-Code.zip` | `packages/claude/.claude/skills/` + `packages/claude/CLAUDE.md` | `.claude/skills/` + `CLAUDE.md` | `.claude/skills/*/SKILL.md` |
| Codex | `dist/MathModel-Skill-Codex.zip` | `packages/codex/skills/` + `packages/codex/AGENTS.md` | `skills/` + `AGENTS.md` | `skills/*/SKILL.md` |

详细安装步骤见 [Agent 安装指南](docs/agent-install-guide.md)。
可复制的首次使用提示词见 [Starter Prompts](docs/starter-prompts.md)。

## 不知道从哪个 Skill 开始？

不用让用户选择多个 skill。把赛题和附件放进 `problem_files/` 后，直接对 Agent 说：

```text
开始生成数学建模论文
```

三端入口文件和 skill 元数据都会指向 `paper-workflow-orchestrator`。它是 MathModel Skill 的总入口，负责判断当前阶段，并路由到题意解析、模型路线、数据图表、结果证据、QA 和写作辅助等子 skill。

如果不是一次性跑完，而是隔了几轮对话、换了窗口或用户直接点名某个子 skill，Agent 应先回到 `paper-workflow-orchestrator`，运行对应平台的 `workflow_guard.py --status`，读取 `paper_output/qa/workflow_guard_report.json` 和 `paper_output/context/workflow_memory.json` 后再继续。

## 3 分钟跑通示例

仓库内置了一个最小示例：

```text
examples/quickstart/problem_files/
├── sample_problem.txt
└── sample_data.csv
```

你可以新建空项目，复制对应平台 skill 包，再复制这个 `problem_files/` 目录，然后让 Agent 使用 `paper-workflow-orchestrator`。如果只是验证安装，也可以手动运行随 skill 附带的 `quickstart_run.py`。完整步骤见 [Quickstart Demo Walkthrough](docs/demo-walkthrough.md)。

这个示例用于验证安装和 workflow 是否跑通；真实赛题中仍应让 Agent 根据当前题目、附件字段和模型输出二次修改数据处理、建模和图表代码。

## 正式论文生成样例

仓库中的 `examples/cumcm2024-b-demo/` 是正式论文交付样例，不是 quickstart 草稿。它展示了从赛题专用代码、结果契约、图表表格证据，到正式大纲、长文源稿、Word 排版和格式门禁的完整链路。

重点文件：

| 文件 | 说明 |
|---|---|
| [examples/cumcm2024-b-demo/README.md](examples/cumcm2024-b-demo/README.md) | 样例说明、复核命令和新赛题使用方式。 |
| [examples/cumcm2024-b-demo/paper_output/final_paper.docx](examples/cumcm2024-b-demo/paper_output/final_paper.docx) | 已提交的正式 Word 样例。 |
| [examples/cumcm2024-b-demo/paper_output/final_paper_source.md](examples/cumcm2024-b-demo/paper_output/final_paper_source.md) | Agent 基于证据链写出的正式 Markdown 源稿。 |
| [examples/cumcm2024-b-demo/paper_output/format_check_report.md](examples/cumcm2024-b-demo/paper_output/format_check_report.md) | 字数、标题层级、图表表格引用和 Word 结构检查。 |
| [examples/cumcm2024-b-demo/paper_output/qa/evidence_gate_report.md](examples/cumcm2024-b-demo/paper_output/qa/evidence_gate_report.md) | 每个子问题的结果、指标、图表、表格和结论证据检查。 |

更完整的使用说明见 [正式论文生成流程与结果样例](docs/generated-demo-workflow.md)。仓库不会提交官方 `B题.pdf`；用户复现时应自行准备官方赛题文件并放入自己的 `problem_files/`。

## 仓库结构

```text
MathModel-Skill/
├── README.md
├── assets/                       # 项目 logo 等展示资源
├── docs/                         # 安装与使用文档
├── dist/                         # 三端可直接下载的 zip 包
├── examples/                     # quickstart 示例与正式 B 题生成样例
├── packages/                     # 三端原生 skill 分发包
│   ├── trae/                     # Trae 原生包
│   ├── claude/                   # Claude Code 原生包
│   └── codex/                    # Codex 原生包
├── requirements.txt              # Python 依赖
└── .gitignore
```

三端 skill 内容保持同步；Trae 包保留原生 `.trae/skills/` 结构，Claude Code 与 Codex 包做对应平台路径适配。

## 快速使用

如果你已经按“最快开始”完成安装，可以直接跳到第 4 步让 Agent 正式使用。

### 1. 安装依赖

在你的数学建模项目根目录安装依赖：

```bash
pip install -r requirements.txt
```

如果你只复制了某个平台包，也可以从本仓库复制 `requirements.txt` 到你的项目中。

### 2. 下载或复制对应平台包

最简单方式是下载 `dist/` 中对应平台的 zip，解压到你的数学建模项目根目录：

```text
Trae        -> dist/MathModel-Skill-Trae.zip
Claude Code -> dist/MathModel-Skill-Claude-Code.zip
Codex       -> dist/MathModel-Skill-Codex.zip
```

也可以从源码目录手动复制：

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

### 4. 让 Agent 正式使用

推荐方式是直接对 Agent 说：

```text
开始生成数学建模论文
```

正式赛题不要先跑一键脚本。Agent 应先读取 `paper-workflow-orchestrator/SKILL.md`，再按当前赛题判断附件性质、生成赛题专用代码、运行真实结果、通过证据门禁，然后调用 `paper-formal-writer` 生成正式 outline，最后基于完整证据链全局写作、排版 Word 并通过格式门禁。

继续一个中断过的项目时，不要让 Agent 凭聊天记录猜阶段。应要求它先运行 `workflow_guard.py --status`，然后按报告中的 `current_step`、`next_step`、`recommended_skill` 和 `next_action` 接着做。

如果想写得更明确，可以复制 [Starter Prompts](docs/starter-prompts.md) 里的完整流程提示词。

### 5. 可选：手动验证安装

如果你想确认 skill 包路径、Python 依赖和示例 workflow 是否能跑通，可以手动执行 quickstart 验证命令。该命令只生成验证草稿，不代表正式比赛论文质量：

按你安装的平台执行：

```bash
# Trae
python .trae/skills/paper-workflow-orchestrator/scripts/quickstart_run.py

# Claude Code
python .claude/skills/paper-workflow-orchestrator/scripts/quickstart_run.py

# Codex
python skills/paper-workflow-orchestrator/scripts/quickstart_run.py
```

如果 Windows PowerShell 出现 GBK 编码问题，先执行：

```powershell
$env:PYTHONIOENCODING="utf-8"
```

## 输出目录

所有平台的输入输出约定一致：

```text
paper_output/
├── preflight_report.json         # 输入资产、依赖和附件可读性预检报告
├── input_manifest.json           # 题面、原始数据、结果模板等附件角色清单
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
│   ├── visualization_plan.json   # 建议图表、图题、用途与输出路径
│   └── paper_outline.json        # 正式论文章节、字数和证据引用契约
├── figure_index.json             # 图表计划索引
├── OUTPUT_LAYOUT.md              # 当前项目输出位置说明
├── code/
│   ├── README.md                 # 当前赛题专用代码工作区说明
│   ├── data_processing/          # 当前赛题专用数据处理代码
│   ├── visualization/            # 当前赛题专用绘图代码
│   ├── modeling/                 # q1/q2/... 建模代码脚手架位置
│   └── qa/                       # 当前赛题专用检查代码
├── results/
│   ├── model_results.json        # 模型输出、参数、方案、预测值等结果证据
│   ├── metrics.json              # 误差、得分、约束满足率等评价指标
│   └── conclusions.json          # 每问回扣题目的结构化结论
├── tables/
│   ├── table_index.json          # 表格索引、表题、用途和路径
│   └── *.csv                     # 参数表、结果表、误差表、对比表等
├── qa/
│   ├── workflow_guard_report.md  # 当前 S0-S8 状态和下一步恢复建议
│   ├── workflow_guard_report.json
│   ├── evidence_gate_report.md   # 证据门禁报告
│   └── evidence_gate_report.json # 机器可读证据门禁结果
├── context/
│   ├── workflow_memory.md         # 长对话断点摘要
│   └── workflow_memory.json       # 当前阶段、下一步、推荐 skill 和关键产物
├── final_paper_source.md         # Agent 全局写作的正式 Markdown 源稿
├── final_paper.docx              # 正式 Word；证据门禁与格式门禁通过后才可称为正式稿
├── final_paper.md                # quickstart 或微单元合并草稿
├── format_check_report.md        # 正式格式门禁报告
├── format_check_report.json      # 机器可读格式门禁结果
├── tasks.json                    # 微单元任务清单
├── generate_log.json             # 微单元生成日志
├── ref_check.md                  # 引用/图表/公式断链检查
├── data_cleaned/                 # 清洗后的数据
├── micro_units/                  # 微单元草稿素材和局部扩写内容
└── figures/                      # 自动生成的图表
```

注意：`packages/*/skills/*/scripts/` 是 skill 自带样板和代码级提示词；`paper_output/code/` 才是当前赛题生成或二次修改的代码位置。不要把当前赛题的 `q1_model.py`、绘图脚本或清洗脚本写回 skill 包目录。

## 生成位置规划

| 生成物 | 固定位置 | 说明 |
|---|---|---|
| 赛题专用数据处理代码 | `paper_output/code/data_processing/` | 根据当前附件字段生成或修改，不写回 skill 包 |
| 赛题专用绘图代码 | `paper_output/code/visualization/` | 读取图表计划和模型结果，输出论文级图片 |
| 赛题专用建模代码 | `paper_output/code/modeling/` | 建议放 `q1_model.py`、`q2_model.py`、... 与 `run_modeling.py` |
| QA/检查代码 | `paper_output/code/qa/` | 可放当前赛题专用的断链、占位符、证据检查脚本 |
| 清洗数据 | `paper_output/data_cleaned/` | 建模脚本优先读取这里的标准化数据 |
| 格式化图表和图片 | `paper_output/figures/` | 正文引用的图片应能追溯到 `figure_index.json` |
| 论文表格 | `paper_output/tables/` | 表格 CSV 与 `table_index.json` 放这里 |
| 结果证据 | `paper_output/results/` | 模型输出、指标和结论的 JSON 交接单 |
| 状态恢复报告 | `paper_output/qa/workflow_guard_report.json` | S0-S8 阶段检查、阻塞项和下一步推荐 |
| 长对话断点 | `paper_output/context/workflow_memory.json` | 记录当前阶段、下一步、推荐 skill 和关键产物 |
| 微单元草稿素材 | `paper_output/micro_units/` | 用于局部扩写、结构辅助或低能力模型兜底草稿 |
| 微单元草稿 | `paper_output/final_paper.md` | quickstart 或微单元合并稿，不能替代正式论文主稿 |
| 正式论文源稿 | `paper_output/final_paper_source.md` | Agent 基于完整证据链全局写作的 Markdown 源稿 |
| 证据门禁报告 | `paper_output/qa/evidence_gate_report.md` | 检查每个子问题是否具备结果、指标、图表、表格和结论回扣 |
| 正式 Word 与格式报告 | `paper_output/final_paper.docx`、`paper_output/format_check_report.md` | 证据门禁与格式门禁通过后才可称为正式稿 |

## JSON 通信契约

MathModel Skill 的 skill 之间不靠“记住上一轮对话”硬撑长流程，而是把关键中间结论写入固定 JSON，再由下一个 skill 读取：

```text
preflight_report.json / input_manifest.json -> workflow_guard_report.json -> problem_analysis.json -> model_route.json / rubric_alignment.json -> data_plan.json / visualization_plan.json -> run_manifest.json / model_results.json / metrics.json / conclusions.json / table_index.json -> evidence_gate -> paper_outline.json -> final_paper_source.md -> final_paper.docx -> format_check_report -> workflow_memory.json
```

| 文件 | 生成者 | 读取者 | 作用 |
|---|---|---|---|
| `paper_output/preflight_report.json` | `paper-workflow-orchestrator` | 所有正式流程入口 | 检查 `problem_files/`、依赖、题面和数据附件可读性 |
| `paper_output/input_manifest.json` | `paper-workflow-orchestrator` | 数据清洗、建模、QA | 固定记录附件角色，避免把结果模板或说明文档误当原始数据 |
| `paper_output/qa/workflow_guard_report.json` | `paper-workflow-orchestrator` | 所有 skill | 检查 S0-S8 前置产物、恢复当前阶段并给出下一步推荐 |
| `paper_output/step1/problem_analysis.json` | `problem-doc-model-selector` | 模型路线、QA、微单元生成 | 结构化保存题意、子问题、任务类型和附件画像 |
| `paper_output/plan/model_route.json` | `modeling-paper-rubric-and-model-selector` | QA、微单元生成 | 保存每一问的主模型、基线模型、验证计划和建议图表 |
| `paper_output/plan/rubric_alignment.json` | `modeling-paper-rubric-and-model-selector` | QA、微单元生成 | 保存评分点、证据形式和论文落点 |
| `paper_output/plan/data_plan.json` | `data-cleaning-and-visualization` | QA、微单元生成、后续代码生成 | 保存数据文件、字段画像、清洗任务和子问题链接 |
| `paper_output/plan/visualization_plan.json` | `data-cleaning-and-visualization` | QA、微单元生成、后续绘图代码 | 保存建议图表、图题、用途、候选字段和输出路径 |
| `paper_output/figure_index.json` | `data-cleaning-and-visualization` | QA、正文引用检查 | 保存计划图表索引，帮助检查图文是否断链 |
| `paper_output/results/model_results.json` | `model-code-and-result-generator` | QA、微单元生成 | 保存每问模型输出、参数、方案、预测值或排序结果 |
| `paper_output/results/run_manifest.json` | `model-code-and-result-generator` | workflow guard、evidence gate | 记录实际运行过的 `q*_model.py`、输入文件哈希和输出产物，防止手写伪造结果 |
| `paper_output/results/metrics.json` | `model-code-and-result-generator` | QA、微单元生成 | 保存误差、得分、约束满足率、稳定性等评价指标 |
| `paper_output/results/conclusions.json` | `model-code-and-result-generator` | QA、微单元生成 | 保存每问可回扣题目的结构化结论 |
| `paper_output/tables/table_index.json` | `model-code-and-result-generator` | QA、微单元生成、正文引用检查 | 保存表格索引、表题、用途和相对路径 |
| `paper_output/tasks.json` | `quality-assurance-auditor` | `paper-micro-unit-generator` | 保存微单元任务清单，以及正文生成所需的模型路线、评分证据和结果证据字段 |
| `paper_output/plan/paper_outline.json` | `paper-formal-writer` | Agent、Word 排版、格式门禁 | 保存正式论文章节、目标字数、图表表格公式和证据引用要求 |
| `paper_output/context/workflow_memory.json` | `context-memory-keeper` | 所有 skill | 保存长对话断点、当前阶段、下一步、推荐 skill、已完成产物和阻塞项 |

## 核心能力

这套流程包含 10 个 workflow skills，其中 9 个负责论文生产链路，`context-memory-keeper` 负责辅助记忆。

### 规划与模型选择

- `problem-doc-model-selector`：解析赛题 PDF/Word，抽取每一问的任务、约束、输入输出和模型方向。
- `modeling-paper-rubric-and-model-selector`：读取 `problem_analysis.json`，生成 `model_route.json`、`rubric_alignment.json` 和 `scoring_strategy.md`，补全“为什么这样建模能拿分”。

### 数据获取、清洗与可视化

- `authoritative-data-harvester`：定位权威公开数据源，优先 API 或官方批量下载。
- `data-cleaning-and-visualization`：提供数据清洗、图表生成和论文级可视化代码样板，并生成数据/图表计划，帮助 Agent 按更稳定的格式产出论文可用图表。
- `model-code-and-result-generator`：根据模型路线、数据计划和清洗数据生成结果、指标、结论和表格证据契约，并在 `paper_output/code/modeling/` 生成 `q1_model.py`、`q2_model.py` 等按子问题扩展的建模代码脚手架。它不是万能自动建模系统，真实赛题仍应由 Agent 基于当前数据二次修改专用建模代码。

### 论文生成与质量审计

- `quality-assurance-auditor`：作为证据门禁，优先读取模型路线、结果、指标、图表、表格和结论契约，通过 `evidence_gate.py` 检查每个子问题是否具备可支撑正文的真实证据；格式合格性由 `paper-formal-writer` 的 `check_paper_format.py` 负责。
- `paper-formal-writer`：证据门禁通过后生成正式 `paper_outline.json`，约束 `18000-25000` 字正式论文、`1 / 1.1 / 1.1.1` 标题、Word 排版和格式门禁。
- `paper-micro-unit-generator`：保留 CUMCM 微单元高质量提示词资产，提供局部扩写、结构辅助和低能力模型兜底草稿，不再作为正式论文主笔。
- `paper-workflow-orchestrator`：中心编排器，指导 Agent 按顺序串联题意、模型、数据、专用代码、结果证据、QA 和全局写作；其中 `scripts/quickstart_run.py` 只用于安装验证和 smoke test。

### 辅助记忆

- `context-memory-keeper`：维护长期准则、短期工作台、外部文献/数据源索引，以及 `workflow_memory.json` / `.md` 断点快照；长对话恢复时以 `workflow_guard.py --status` 的报告为准。

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

# 运行并复核 q1/q2/... 建模代码脚手架
python paper_output/code/modeling/run_modeling.py

# QA 与任务清单
python .trae/skills/quality-assurance-auditor/scripts/pipeline.py

# 正式证据门禁
python .trae/skills/quality-assurance-auditor/scripts/evidence_gate.py

# 正式论文 outline
python .trae/skills/paper-formal-writer/scripts/build_paper_outline.py

# 微单元草稿/局部材料生成
python .trae/skills/paper-micro-unit-generator/scripts/generate_all_offline.py

# 合并微单元验证草稿
python .trae/skills/paper-micro-unit-generator/scripts/merge.py

# 正式 Word 排版与格式门禁
python .trae/skills/paper-formal-writer/scripts/format_formal_docx.py
python .trae/skills/paper-formal-writer/scripts/check_paper_format.py
```

Claude Code 把 `.trae/skills/` 换成 `.claude/skills/`；Codex 把 `.trae/skills/` 换成 `skills/`。

## 可选：重新打包

维护者更新 skill 后，可以重新生成三端发布包：

```bash
python scripts/build_release_packages.py --clean
```

生成结果：

```text
dist/MathModel-Skill-Trae.zip
dist/MathModel-Skill-Claude-Code.zip
dist/MathModel-Skill-Codex.zip
```

打包脚本会排除 `__pycache__/`、`*.pyc`、`problem_files/`、`crawled_data/`、`paper_output/` 和 `data_requirements.json`，确保 zip 里只包含可分发的 skill 包、入口说明和依赖文件。

## 一句话总结

MathModel Skill 的价值不是“一个提示词写完整篇论文”，而是把数学建模比赛拆成可控、可检查、可重跑的完整 skill 工作流。Trae、Claude Code、Codex 用户都可以下载对应原生包，自主接入自己的 Agent 工作环境。
