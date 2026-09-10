# MathModel Skill Pro · Codex 独立技能包

这是当前分支的 **Pro 3.3.0-pro.1** Codex 技能包，入口为 `pro-workflow-orchestrator`，采用 P0–P9 工作流。它适合把 MathModel 安装到一个独立比赛项目中，通过 Codex 对话完成审题、选模、实验、证据核验和论文交付。

这里的 `.agents/skills/` 是独立 Skill 安装内容，不包含 Codex Plugin 的 MCP 服务、持久作业管理或工作台。包身份以 `pro-workflow-orchestrator/MATHMODEL_EDITION.json` 为准；仓库根的历史 Standard `VERSION` 不代表这个包的版本。

[仓库首页](../../README.md) · [Codex Plugin 使用说明](../../plugins/mathmodel/README.md) · [Pro 工作流契约](../../docs/pro-contracts.md)

## 安装到比赛项目

1. 准备一个独立比赛目录，把题面和附件放入 `problem_files/`。
2. 将本目录的完整 `.agents/skills/` 复制到比赛目录的 `.agents/skills/`。保留所有脚本、参考文件和模板，不要只复制 `SKILL.md`。不要覆盖项目已有的 `AGENTS.md`。
3. 在比赛项目中建立 Python 虚拟环境，并使用当前源码根目录的 [requirements.txt](../../requirements.txt) 安装依赖。建议 Python 3.11 或 3.12；正式 Word/PDF 交付还需要 LibreOffice。若使用独立发行包，以该包随附的依赖文件为准。
4. 在 Codex 中打开比赛目录，确认能够发现 `pro-workflow-orchestrator`，然后从它启动。

安装后的基本结构：

```text
my-contest/
├── .agents/skills/                 # 完整 Pro 技能目录
├── problem_files/                  # 用户提供的题面与附件
└── paper_output_pro/               # 工作流运行后生成
```

一个比赛项目只使用一套 MathModel 入口。已有 Standard、Lite、其他 Pro 安装或已启用 MathModel Plugin 时，先处理重复入口；不要直接把不同版本的输出与批准记录合并。需要稳定的历史 Standard 包时，请使用[固定的 Standard 2.3.0 Release](https://github.com/yushui2022/MathModel-Skill/releases/tag/v2.3.0)。

## 开始与继续

在 Codex 中发送：

> 请使用 $pro-workflow-orchestrator，从 P0 开始处理 problem_files/ 中的赛题与附件。先记录实际模型、推理档位、工具与环境能力，再按 MathModel Pro 工作流推进。所有产物写入 paper_output_pro/；需要确认时向我展示具体题意、路线或结果。

继续已有项目时，仍调用同一入口，并说明要继续的小问或待处理问题。模型和推理档位以当前宿主实际支持的能力为准；预检会记录真实环境。需要独立角色的审题、复算和审稿必须有真实隔离执行，不能用一段对话模拟多个角色来满足门禁。

Pro 在三个正式检查点请求确认：题意与论文范围、模型路线与实验计划、数值结果与不确定性。确认后继续执行相应阶段；证据通过并冻结后，由 `paper-formal-writer` 完成正式写作和修订。

## 正式产物与交付判断

全部 Pro 产物位于比赛项目的 `paper_output_pro/`：

| 路径 | 内容 |
|---|---|
| `code/`、`experiments/<run_id>/` | 建模代码、运行规格、真实执行回执、日志与结果 |
| `experiment_manifest.json`、`evidence_freeze.json` | 实验索引与冻结证据记录 |
| `final_paper_source.md` | 唯一正式论文源稿 |
| `final_paper.docx`、`final_paper.pdf` | 从同一源稿生成的 Word 与 PDF |
| `pro_gate_report.json` | Pro 最终门禁报告 |

文件生成或脚本退出成功不等于正式交付。论文还需通过当前项目的证据、独立审稿、Word/PDF 渲染及最终门禁；工程样例与短报告应明确其交付范围。

## 与 Codex Plugin 如何选择

独立 Skill 适合在比赛项目内安装并直接调用工作流。若希望跨会话按小问恢复上下文、查看真实作业与日志、取消或重试计算、分析修改影响、导出独立重放包，可使用 [Codex Plugin 0.5.0-alpha.1](../../plugins/mathmodel/README.md)。插件还有可选的本地证据页面，并接入有限范围的 LP/MILP 数学检查；该检查器也随当前分支的 Pro 核心分发。

三路审题、多路线比较、独立复算、三个确认点、证据冻结、双向结论映射和五角色审稿属于 Pro 已有能力。插件增加使用与执行管理功能，仍受这些门禁约束；当前 Alpha 的工程验证不代表已证明真实比赛论文质量提升。

维护说明：本包核心由 `packages/claude/.claude/skills/` 同步生成。修改核心时从 Claude 目录中的唯一维护源开始，再同步到 Codex 和插件，避免三套副本发生分歧。
