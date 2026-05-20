# Agent 安装指南

MathModel Skill 按完整 skill 包分发。请选择你使用的 Agent 平台，优先下载对应 zip；也可以从源码目录复制对应平台包。

| Agent | 推荐下载包 | 源码复制来源 | 复制到项目内 | 原生入口 | 可选验证命令 |
|---|---|---|---|---|---|
| Trae | `dist/MathModel-Skill-Trae.zip` | `packages/trae/.trae/skills/` | `.trae/skills/` | `.trae/skills/*/SKILL.md` | `python .trae/skills/paper-workflow-orchestrator/scripts/quickstart_run.py` |
| Claude Code | `dist/MathModel-Skill-Claude-Code.zip` | `packages/claude/.claude/skills/` + `packages/claude/CLAUDE.md` | `.claude/skills/` + `CLAUDE.md` | `.claude/skills/*/SKILL.md` | `python .claude/skills/paper-workflow-orchestrator/scripts/quickstart_run.py` |
| Codex | `dist/MathModel-Skill-Codex.zip` | `packages/codex/skills/` + `packages/codex/AGENTS.md` | `skills/` + `AGENTS.md` | `skills/*/SKILL.md` | `python skills/paper-workflow-orchestrator/scripts/quickstart_run.py` |

## 推荐使用方式

安装后，普通用户不需要先手动运行 Python 命令。把赛题和附件放进 `problem_files/` 后，直接对 Agent 说：

```text
开始生成数学建模论文
```

Agent 应优先读取 `paper-workflow-orchestrator/SKILL.md`，再按流程调用其他 skill。表格里的命令主要用于安装验证、quickstart 演示或调试，不是 skill 的唯一入口。

更明确的可复制提示词见 [Starter Prompts](starter-prompts.md)。
完整生成位置规划见 [Output Layout](output-layout.md)。核心规则是：skill 包目录只放可复用能力，当前赛题生成或二次修改的代码统一写入 `paper_output/code/`。

如果用户不知道该从哪个 skill 开始，也不要让用户选择。默认先进入总控 skill：

```text
Trae        -> .trae/skills/paper-workflow-orchestrator/SKILL.md
Claude Code -> .claude/skills/paper-workflow-orchestrator/SKILL.md
Codex       -> skills/paper-workflow-orchestrator/SKILL.md
```

## 最小示例

安装后建议先跑仓库内置示例，确认 skill 包路径和 Python 依赖正常：

```text
examples/quickstart/problem_files/ -> your-project/problem_files/
```

完整演示步骤见 [Quickstart Demo Walkthrough](demo-walkthrough.md)。

## 输入目录

所有平台都使用相同输入目录：

```text
problem_files/      # 赛题 PDF/Word 和官方附件数据
crawled_data/       # 可选，外部补充数据
```

## 输出目录

所有平台都使用相同输出目录：

```text
paper_output/
├── OUTPUT_LAYOUT.md
├── step1/
│   ├── problem_analysis.json
│   ├── A_题意对齐.md
│   ├── B_论文大纲.md
│   ├── C_评分点对齐表.md
│   └── D_模型路线.json
├── plan/
│   ├── model_route.json
│   ├── rubric_alignment.json
│   ├── scoring_strategy.md
│   ├── data_plan.json
│   └── visualization_plan.json
├── figure_index.json
├── code/
│   ├── README.md
│   ├── data_processing/
│   ├── visualization/
│   ├── modeling/
│   └── qa/
├── results/
│   ├── model_results.json
│   ├── metrics.json
│   └── conclusions.json
├── tables/
│   ├── table_index.json
│   └── *.csv
├── final_paper.docx
├── final_paper.md
├── tasks.json
├── generate_log.json
├── ref_check.md
├── data_cleaned/
├── micro_units/
└── figures/
```

`problem_analysis.json` 是三端共同使用的结构化题意契约。总编排器会先生成它，再生成 `paper_output/plan/model_route.json` 与 `rubric_alignment.json`。数据清洗 skill 会补充 `data_plan.json`、`visualization_plan.json` 和 `figure_index.json`；结果证据 skill 会补充 `paper_output/results/` 与 `paper_output/tables/`；QA 再根据模型路线、评分证据、图表计划和结果证据生成动态 `tasks.json`。

`paper_output/code/` 用来存放当前赛题专用代码：`data_processing/` 放清洗和特征工程脚本，`visualization/` 放绘图脚本，`modeling/` 放 q1/q2/q3 建模脚本，`qa/` 放可选检查脚本。不要把这些赛题专用代码写回 skill 包里的 `scripts/`。

## Skill 包结构

每个 skill 都是完整文件夹，不是单个 Markdown：

```text
skill-name/
├── SKILL.md
├── scripts/
├── references/
├── assets/
└── 其他资源
```

其中 `scripts/`、`references/`、`assets/` 不是每个 skill 都必有，但如果原版存在，平台包中会完整保留。

## 更新方式

后续更新时，重新复制对应平台目录即可：

```text
Trae        -> packages/trae/.trae/skills/
Claude Code -> packages/claude/.claude/skills/
Codex       -> packages/codex/skills/
```

如果你修改过本地 skill，请先备份再覆盖。

## 重新生成发布包

维护者更新 skill 后，在仓库根目录运行：

```bash
python scripts/build_release_packages.py --clean
```

脚本会生成 `dist/` 下的三端 zip，并自动排除缓存、赛题输入、运行输出和本地爬取数据。
