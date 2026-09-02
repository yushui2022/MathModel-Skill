<div align="center">
  <img src="./assets/mathe-skill-logo.svg" alt="MathModel Skill Pro logo" width="132" height="132" />

# MathModel Skill Pro

### 不计成本、强调独立复算与可审计证据的高算力数学建模工作流

[![Version](https://img.shields.io/badge/version-3.0.0--pro.2-111827)](#安装)
[![Skills](https://img.shields.io/badge/skills-10-2563eb)](#技能组成)
[![Platforms](https://img.shields.io/badge/platforms-Codex%20%7C%20Claude%20Code-16a34a)](#安装)
[![Output](https://img.shields.io/badge/output-DOCX%20%2B%20PDF-b91c1c)](#交付门禁)

</div>

> 当前是永久独立的 `pro` 分支。推荐 **Claude Fable 5** 或
> **GPT-5.6 Sol Ultra** 使用。其他模型会收到能力警告但仍可运行，Pro 不会因此
> 降低候选数、复算、审稿或交付门禁。

| 模型与目标 | 建议版本 | 分支 |
|---|---|---|
| Fable 5 / GPT-5.6 Sol Ultra，允许高计算成本，追求最高可验证质量 | **Pro（当前分支）** | `pro` |
| 强模型、正式竞赛、希望控制复杂度 | Standard（默认分支） | [`master`](https://github.com/yushui2022/MathModel-Skill/tree/master) |
| 普通或较旧模型、短上下文、优先简单稳定 | Lite | [`lite`](https://github.com/yushui2022/MathModel-Skill/tree/lite) |

**一个比赛项目只安装一个版本。** 不要把 Pro、Standard 或 Lite 解压到同一目录。
Pro 预检发现混装时会阻止运行。Pro 使用独立 `paper_output_pro/`，不读取 Standard
或 Lite 的旧结果和批准记录。

## 三个检查点

Pro 在检查点之间自动执行，但必须等待用户确认：

1. **题意与附件分类**：三份隔离审题完成，用户确认共识、分歧和附件用途。
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

首版只支持 Codex 和 Claude Code，不提供 Trae 包：

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

```bash
python scripts/sync_platform_packages.py --check
python tests/run_pro_tests.py
python scripts/build_release_packages.py --clean
python scripts/build_release_packages.py --verify
```

CI 在 Windows、Ubuntu、macOS 的 Python 3.11/3.12 上验证契约、路径、检查点、门禁、
平台同步和确定性 ZIP。四类真实赛题的前向验收矩阵见
[Forward evaluation](docs/forward-evaluation.md)；真实模型运行结果应在首次 Pro Release
前单独归档，本分支首次推送不创建 Tag 或 Release。

## 许可证

MIT License，Copyright (c) 2026 yushui2022。
