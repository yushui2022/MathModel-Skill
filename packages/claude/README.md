# MathModel Skill Pro · Claude Code 独立技能包

这是当前分支的 **Pro 3.3.0-pro.1** Claude Code 技能包，入口为 `pro-workflow-orchestrator`，采用 P0–P9 工作流。它把审题、选模、实验、证据核验和正式论文交付组织成可持续推进的建模流程。

这里的 `.claude/skills/` 是独立 Skill 安装内容，也是本仓库 Pro 核心的唯一维护源。包身份以 `pro-workflow-orchestrator/MATHMODEL_EDITION.json` 为准；仓库根的历史 Standard `VERSION` 不代表这个包的版本。

[仓库首页](../../README.md) · [Codex Plugin 使用说明](../../plugins/mathmodel/README.md) · [Pro 工作流契约](../../docs/pro-contracts.md)

## 安装到比赛项目

1. 准备一个独立比赛目录，把题面和附件放入 `problem_files/`。
2. 将本目录的完整 `.claude/skills/` 复制到比赛目录的 `.claude/skills/`。保留脚本、参考文件和模板，不要只复制 `SKILL.md`。不要覆盖项目已有的 `CLAUDE.md`。
3. 在比赛项目中建立 Python 虚拟环境，并使用当前源码根目录的 [requirements.txt](../../requirements.txt) 安装依赖。建议 Python 3.11 或 3.12；正式 Word/PDF 交付还需要 LibreOffice。若使用独立发行包，以该包随附的依赖文件为准。
4. 在 Claude Code 中打开比赛目录，确认能够发现 `pro-workflow-orchestrator`，然后指定它作为完整任务入口。

安装后的基本结构：

```text
my-contest/
├── .claude/skills/                 # 完整 Pro 技能目录
├── problem_files/                  # 用户提供的题面与附件
└── paper_output_pro/               # 工作流运行后生成
```

一个比赛项目只使用一个平台入口和一套 MathModel 安装。不要叠加 Standard、Lite 或另一份 Pro 技能，也不要把旧版本的输出或其他项目的批准记录当作当前 Pro 的已通过证据。需要稳定的历史 Standard 包时，请使用[固定的 Standard 2.3.0 Release](https://github.com/yushui2022/MathModel-Skill/releases/tag/v2.3.0)。

## 开始与继续

在 Claude Code 中发送：

> 请使用 pro-workflow-orchestrator，从 P0 开始处理 problem_files/ 中的赛题与附件。先记录当前平台、实际模型、推理档位、工具与环境能力，再按 MathModel Pro 工作流推进。所有产物写入 paper_output_pro/；需要确认时向我展示具体题意、路线或结果。

继续已有项目时，使用同一入口，说明要继续的小问或待处理问题。模型选择以当前 Claude Code 实际支持的能力为准；不能切换推理档位或使用某项工具时，应记录限制。独立审题、复算和审稿需要真实隔离执行，不能只给同一会话中的文字换上角色名称。

Pro 在三个正式检查点请求确认：题意与论文范围、模型路线与实验计划、数值结果与不确定性。确认后继续相应阶段；证据通过并冻结后，由 `paper-formal-writer` 完成正式写作、全局修订与论文检查。

## 正式产物与交付判断

全部 Pro 产物位于比赛项目的 `paper_output_pro/`：

| 路径 | 内容 |
|---|---|
| `code/`、`experiments/<run_id>/` | 建模代码、运行规格、真实执行回执、日志与结果 |
| `experiment_manifest.json`、`evidence_freeze.json` | 实验索引与冻结证据记录 |
| `final_paper_source.md` | 唯一正式论文源稿 |
| `final_paper.docx`、`final_paper.pdf` | 从同一源稿生成的 Word 与 PDF |
| `pro_gate_report.json` | Pro 最终门禁报告 |

正式交付取决于当前证据、独立审稿、Word/PDF 渲染和最终门禁，不取决于是否已经出现一个论文文件。工程样例或短报告也应明确其交付范围。

## 与 Codex Plugin 的关系

这个包供 **Claude Code 独立使用**。复制 `.claude/skills/` 不会安装 Codex Plugin，也不会启动其 MCP 服务、持久作业管理或工作台。

[Codex Plugin 0.5.0-alpha.1](../../plugins/mathmodel/README.md) 是同一 Pro 核心面向 Codex 的另一种交付方式，增加按小问恢复上下文、真实作业与日志管理、修改影响分析和独立重放包，并接入有限范围的 LP/MILP 数学检查。该检查器也随当前分支的 Pro 核心分发。需要使用插件时，请按插件文档在 Codex 中安装，并先处理比赛项目中的重复入口。

三路审题、多路线比较、独立复算、三个确认点、证据冻结、双向结论映射和五角色审稿属于 Pro 已有能力。插件保留这些要求；当前 Alpha 的工程验证不代表已证明真实比赛论文质量提升，也不等于 Claude Code 已接入插件的运行服务。

维护说明：Pro 核心在此目录维护，再由同步脚本生成 Codex 技能和插件核心。请勿分别修改生成副本。
