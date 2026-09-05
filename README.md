<div align="center">
  <img src="./assets/mathe-skill-logo.svg" alt="MathModel Skill Pro logo" width="132" height="132" />

# MathModel Skill Pro

### 不计成本、强调独立复算与可审计证据的高算力数学建模工作流

[![Version](https://img.shields.io/badge/version-3.3.0--pro.1-111827)](#安装)
[![Skills](https://img.shields.io/badge/skills-10-2563eb)](#技能组成)
[![Platforms](https://img.shields.io/badge/platforms-Codex%20%7C%20Claude%20Code-16a34a)](#安装)
[![Output](https://img.shields.io/badge/output-DOCX%20%2B%20PDF-b91c1c)](#交付门禁)

</div>

> 当前是永久独立的 `pro` 分支。首选 **GPT-6 Astra** 或
> **Claude Fable 5.1**；同时支持 Claude Opus 5、Sonnet 5、Fable 5 和
> GPT-5.6 Sol。其他模型会收到能力警告但仍可运行，Pro 不会因此降低门禁。

| 模型与目标 | 建议版本 | 分支 |
|---|---|---|
| GPT-6 Astra / Claude Fable 5.1 等前沿模型，允许高计算成本，追求最高可验证质量 | **Pro（当前分支）** | `pro` |
| 强模型、正式竞赛、希望控制复杂度 | Standard（默认分支） | [`master`](https://github.com/yushui2022/MathModel-Skill/tree/master) |
| 普通或较旧模型、短上下文、优先简单稳定 | Lite | [`lite`](https://github.com/yushui2022/MathModel-Skill/tree/lite) |

**一个比赛项目只安装一个版本。** 不要把 Pro、Standard 或 Lite 解压到同一目录。
Pro 预检发现混装时会阻止运行。Pro 使用独立 `paper_output_pro/`，不读取 Standard
或 Lite 的旧结果和批准记录。

<p align="center">
  <a href="./assets/orlando-liu-social.jpg">
    <img src="./assets/orlando-liu-social.jpg" alt="Orlando Liu social media profile" width="480" />
  </a>
</p>

## 前沿模型适配

Pro 使用可维护的模型能力档案，不再仅靠模型名称片段判断。P0 会记录规范模型 ID、
支持档位、推理档位别名、分阶段建议、官方来源和运行环境能力：

| 档位 | 模型 | Pro 策略 |
|---|---|---|
| 首选 | GPT-6 Astra、Claude Fable 5.1 | 建模与评审优先 `max`，长篇写作优先 `high` |
| 支持 | Claude Opus 5、Sonnet 5、Fable 5、GPT-5.6 Sol | 完整 P0-P9，不降低候选、复算或门禁 |
| 未识别 | 其他或更新型号 | 警告并核对官方能力，仍执行完整 Pro 工作流 |

能力档案于 `2026-09-04` 依据
[OpenAI GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra)、
[OpenAI 模型指南](https://developers.openai.com/api/docs/guides/latest-model)、
[Claude Fable 5.1](https://www.anthropic.com/claude/fable) 和
[Claude 模型状态](https://platform.claude.com/docs/en/about-claude/model-deprecations)
核验。这里的“支持”表示配置与门禁兼容；只有真实赛题前向测试通过后才标记为
Pro-qualified。

P0 同时生成项目指令与所有 Pro `SKILL.md` 的哈希清单。检查点 1 前必须完成
`instruction_audit.json`，解决指令冲突并锁定“三个检查点之外自动推进”的执行契约。
支持并行/异步工具时会批量发起独立任务；不支持时按隔离上下文顺序执行。

## 完整竞赛论文

**3.3 默认生成完整竞赛论文，不是五页简报。** 写作规划以约 20 页为目标，默认
18-24 页；正文至少 8000 有效字符只是防止极短稿的下限，不是优秀标准，也不是
字符到页数的换算。检查点 1 必须确认题意、论文范围和适用规则，不能写到一半自行降级。

- **逐问论证**：每问都要覆盖选模理由、推导、求解、结果、验证和局限，绑定真实正文
  段落与冻结证据；只有标题、算法名或一段结论不能算完成。
- **完整长文写作**：允许分章节、多轮写入唯一正式源稿，最后统一全文；不会因单次
  回复长度限制而自动缩成摘要，也不要求把每问机械拆成六个标题。
- **真实页数验收**：根据渲染 PDF 中的章节位置计数。附录、隐藏注释和代码不能替代
  正文；不足已确认范围时补充实质工作或请用户重新确认范围，不用排版和重复内容凑页数。
- **逐问审稿**：五个独立评审都需评价每问是否论证充分；篇幅和结构检查 PASS 不代表优秀。

| 模式 | 用途 | 验收标识 |
|---|---|---|
| `competition`（默认） | 完整竞赛论文 | `COMPETITION_REPORT_CHECKED` |
| `short-report` | 用户明确要求的短报告 | `SHORT_REPORT_ONLY` |
| `smoke-test` | 安装、计算和交付链测试 | `ENGINEERING_SMOKE_ONLY` |

短报告/测试模式和自定义篇幅都必须说明原因，并在检查点 1 由用户确认。
默认页数是可调整的项目规划，不是所有竞赛的硬规定。内置 `cumcm-2026` 按
[2026 国赛规则](https://www.mcm.edu.cn/html_cn/node/4cd596519c9eb9fbd866398f6df0caa3.html)
限制正文不超过 30 页；`mcm-2026` 按
[2026 美赛说明](https://www.contest.comap.com/undergraduate/contests/mcm/contests/2026/problems/2026_MCM_Problem_C.pdf)
限制解答报告不超过 25 页（含附录，不含末尾 AI 使用报告）。其他比赛/年份须先核对当届要求。

**现有五页构造算例仅验证工程交付链，不是完整竞赛长文验收。** 本次更新不宣称已完成
真实多问赛题约 20 页长文的前向验收；验收范围见 [前向测试要求](docs/forward-evaluation.md)。

3.3 已通过 **80 项本地自动测试**（Windows / Python 3.11，包含真实 LibreOffice 渲染）、
两个平台共 20 个 Skill 入口校验，以及安装包确定性验证。合成分页测试只检查计数，
不作为论文质量证据。

### 保留的证据与交付保障

- 实验由脚本实际执行并记录，独立复算读取真实指标；不再信任手填的 `PASS`。
- 原始附件、完整证据目录和论文版本绑定哈希；修改或新增上游文件会使批准失效。
- 正式写作增加章节、证据段落、关键数值、公式、重复正文与图表检查。
- 五角色必须来自真实独立上下文，且审查同一版论文；不能把五个角色名称当作五次独立审稿。
- DOCX 对照正式源稿重新构建校验，PDF 双向核对正文，并要求实际逐页查看渲染图。

**升级须重新预检、计算和审批。** 3.3 使用新机器契约，不能复用旧版的结果或批准。
机器门禁证明的是可追踪性和具体检查项，不保证建模假设正确、论文优秀或竞赛获奖。
真实题意、论证质量和适用边界仍须通过独立评审与赛题前向测试。

3.2 的54项历史回归与五页中文算例记录保留在
[验收记录与样例](docs/pro-3.2-validation.md)，其中区分真实执行和测试模拟。

## 三个检查点

Pro 在检查点之间自动执行，但必须等待用户确认：

1. **题意、附件与论文范围**：三份隔离审题完成，用户确认共识、分歧、附件用途、交付模式和篇幅规划。
2. **模型路线**：每问 3-5 条实质不同路线完成竞赛，用户确认推荐路线和实验计划。
3. **数值与不确定性**：双路复算、随机多种子、稳健性和消融完成，用户确认后冻结证据。

每次批准都绑定 SHA-256。批准后任一上游文件改变，该检查点和全部下游自动失效。

## 核心流程

```text
P0 能力/输入预检
 -> P1 三路隔离审题与共识
 -> [检查点 1]
 -> P2 公开研究 + 多路线模型竞赛
 -> [检查点 2]
 -> P3-P5 独立实现、复算、稳健性、消融
 -> [检查点 3]
 -> P6 证据冻结
 -> P7 全局写作
 -> P8 五角色隔离审稿与修复
 -> P9 DOCX/PDF 双门禁
```

随机算法默认至少 10 个不同种子；区间不稳定时自动扩展。关键结论至少两条独立
实现或复算路径。失败候选、退出码和原因全部保留。相同失败连续出现三次，或缺少
用户数据/授权时才停止；不设 Token、候选总量或运行时间预算。

## 公开研究

Pro 可自动检索公开资源，优先政府、国际组织、官方数据库、标准机构、原始论文和
数据发布者。关键外部数据尽量由两个独立权威发布者交叉验证。登录、付费、私有数据
或有额外授权要求的资源必须先获得用户明确授权。URL、发布者、访问时间、内容哈希、
用途和论文 claim 会写入 `source_ledger.json`。

## 安装

Pro 只支持 Codex 和 Claude Code，不提供 Trae 包：

| 平台 | 安装包 | 安装目录 |
|---|---|---|
| Codex | `dist/MathModel-Skill-Pro-Codex.zip` | `.agents/skills/` |
| Claude Code | `dist/MathModel-Skill-Pro-Claude-Code.zip` | `.claude/skills/` |

安装包不会写入或覆盖项目根目录的 `AGENTS.md`、`CLAUDE.md`。每个 ZIP 包含
`VERSION`、`LICENSE`、`MATHMODEL_EDITION.json`、`MATHMODEL_BUILD.json`
逐文件哈希、Pro README、依赖和启动提示词。

Python 需要 3.11 或 3.12。安装依赖：

```bash
python -m pip install -r requirements.txt
python -m pip check
```

最终 PDF 必须由 LibreOffice 渲染。安装并确保 `libreoffice` 或 `soffice` 可用；
Windows 默认也会检测 `C:\Program Files\LibreOffice\program\soffice.exe`。

## 启动

把赛题和附件放入 `problem_files/`，然后使用：

```text
请使用 $pro-workflow-orchestrator，从 P0 开始执行 MathModel Skill Pro。
用户声明模型为 <模型名>，推理档位为 <档位>。
所有产物只写入 paper_output_pro/，不要读取 Standard/Lite 旧结果。
在题意与附件分类、模型路线、数值结果与不确定性三个检查点分别停下等待我确认。
默认完整竞赛论文，按当届规则规划约 20 页；检查点 1 一并确认模式和篇幅，不自行降为简报。
除这三个检查点、缺少用户数据/授权或同类失败连续三次外，持续完成已授权工作。
读取 P0 模型档案和指令审计；支持并行时批量启动独立角色，主 Agent 继续其他工作。
只自动使用公开来源；登录、付费、私有或额外授权资源先询问我。
最终必须通过五角色审稿、DOCX 与 LibreOffice PDF 双门禁，未通过不要称为正式交付。
```

完整提示词见 [START_HERE](docs/pro-start-prompt.md)。

## 技能组成

| Skill | 责任 |
|---|---|
| `pro-workflow-orchestrator` | P0-P9 总控、检查点和最终 gate |
| `problem-doc-model-selector` | 三路隔离审题与共识 |
| `authoritative-data-harvester` | 公开权威研究与来源账本 |
| `pro-model-tournament` | 多路线模型竞赛 |
| `data-cleaning-and-visualization` | 数据质量、清洗和可复现图表 |
| `model-code-and-result-generator` | 独立实现、复算和稳健性实验 |
| `quality-assurance-auditor` | 证据审计与冻结 |
| `paper-formal-writer` | 全局写作、OMML Word 和 PDF |
| `pro-review-board` | 五角色审稿和修复闭环 |
| `context-memory-keeper` | 长任务恢复和失败计数 |

机器契约字段见 [Pro contracts](docs/pro-contracts.md)。

## 交付门禁

正式交付至少包含：

```text
paper_output_pro/final_paper_source.md
paper_output_pro/final_paper.docx
paper_output_pro/final_paper.pdf
paper_output_pro/evidence_freeze.json
paper_output_pro/review_board_report.json
paper_output_pro/pro_gate_report.json
```

最终必须无未解决 Critical/Major 审稿项，DOCX/PDF 均非空、可读取、公式/图表/分页/
引用一致，且所有冻结哈希仍新鲜。

## 开发验证

以下命令在代码仓库中运行；完整渲染测试需要设置 `REQUIRE_LIBREOFFICE=1`。

```bash
python scripts/sync_platform_packages.py --check
python tests/run_pro_tests.py
python scripts/build_release_packages.py --clean
python scripts/build_release_packages.py --verify
```

CI 在 Windows、Ubuntu、macOS 的 Python 3.11/3.12 上验证模型档案、指令审计、
契约、路径、检查点、门禁、平台同步和确定性 ZIP。四类真实赛题的前向验收矩阵见
[Forward evaluation](docs/forward-evaluation.md)；真实模型运行结果应在首次 Pro Release
前单独归档，本分支首次推送不创建 Tag 或 Release。

## 许可证

MIT License，Copyright (c) 2026 yushui2022。
