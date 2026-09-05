<div align="center">
  <img src="./assets/mathmodel-banner.png" alt="MathModel Skill：Claude 与 GPT 协作研究数学建模赛题" width="100%" />

# MathModel Skill Standard

### 从赛题分析、真实计算到可复现的数学建模论文

[![Version](https://img.shields.io/badge/version-2.3.0-0f766e)](https://github.com/yushui2022/MathModel-Skill/releases/tag/v2.3.0)
[![Platforms](https://img.shields.io/badge/platforms-Codex%20%7C%20Claude%20Code%20%7C%20Trae-111827)](#快速导入使用)
[![License](https://img.shields.io/badge/license-MIT-16a34a)](./LICENSE)

</div>

MathModel Skill 是一套供编程 Agent 使用的数学建模 Skills。把赛题与附件放入项目后，Agent 按工作流分析问题、选择模型、编写并运行代码、整理图表和证据，再撰写与检查论文；它不只是让模型直接生成一篇文章的提示词。

当前是默认 `master` 分支的 **Standard 2.3.0**，适合长上下文、推理和工具调用稳定的强模型。它在流程复杂度与计算成本可控的前提下，提供完整章节写作、原生 Word 公式和 PDF 渲染检查。最终产物包括论文、赛题代码、计算结果、图表和验证记录；检查通过不等于保证论文优秀或竞赛获奖。

**版本速览**

目前提供 **4 个独立版本**，分别在不同 Git 分支维护，不是安装后的四种切换模式：

| 版本与分支 | 适合谁 | 作用与主要区别 |
|---|---|---|
| [**Standard（默认）**](https://github.com/yushui2022/MathModel-Skill/tree/master) | 强模型，希望兼顾正式写作与流程成本 | 完整章节写作、证据检查、原生公式 Word 与 PDF 渲染检查。 |
| [**Lite**](https://github.com/yushui2022/MathModel-Skill/tree/lite) | 普通、较旧或短上下文模型 | 一个入口、六步流程，生成基础建模报告；不含严格引文、原生 Word 公式和 PDF 验收。 |
| [**Pro（预发布）**](https://github.com/yushui2022/MathModel-Skill/tree/pro) | 高能力模型，愿意投入更多时间与计算 | 多路线比较、独立复算、五角色审稿及 Word/PDF 检查；有三个用户确认点。 |
| [**LaTeX（实验性预发布）**](https://github.com/yushui2022/MathModel-Skill/tree/Latex) | 需要 TeX 源文件、能自行配置 TeX 环境 | 旧版工作流的 LaTeX/PDF 导出分支，不等同于当前 Standard 或 Pro 的能力。 |

**一个项目只安装一个版本、一个平台包，不要混装。** 各版本的具体导入方法见下方快速使用说明。

## 小红书

作者：**Orlando Liu（奥兰多）**，小红书号：[`xiaoyushui2022`](https://www.xiaohongshu.com/user/profile/610d282b0000000001004ffb)。点击图片进入主页，也可以扫码找到我。

<p align="center">
  <a href="https://www.xiaohongshu.com/user/profile/610d282b0000000001004ffb">
    <img src="./assets/orlando-liu-social.jpg" alt="Orlando Liu 小红书主页与二维码" width="480" />
  </a>
</p>

## 快速导入使用

### 1. 下载 Standard 安装包

**一个比赛项目只安装一个版本、一个平台包。** 不要把 Standard、Lite、Pro 或 LaTeX 包混在同一目录。

从 [Standard 2.3.0 Release](https://github.com/yushui2022/MathModel-Skill/releases/tag/v2.3.0) 下载与你的 Agent 对应的一个安装包：

| 平台 | 直接下载 | 解压后的 Skill 目录 |
|---|---|---|
| Codex | [Codex 安装包](https://github.com/yushui2022/MathModel-Skill/releases/download/v2.3.0/MathModel-Skill-Codex.zip) | `.agents/skills/` |
| Claude Code | [Claude Code 安装包](https://github.com/yushui2022/MathModel-Skill/releases/download/v2.3.0/MathModel-Skill-Claude-Code.zip) | `.claude/skills/` |
| Trae | [Trae 安装包](https://github.com/yushui2022/MathModel-Skill/releases/download/v2.3.0/MathModel-Skill-Trae.zip) | `.trae/skills/` |

上面的安装包不同于 GitHub 的 `Code → Download ZIP` 仓库源码。需要核验下载时，使用 Release 中的 [SHA256SUMS.txt](https://github.com/yushui2022/MathModel-Skill/releases/download/v2.3.0/SHA256SUMS.txt)。

### 2. 导入项目并准备环境

在一个独立的数学建模项目目录中解压安装包，不要只复制 `SKILL.md`，也不要覆盖用户已有的 `AGENTS.md` 或 `CLAUDE.md`。确认隐藏目录里的 Skills 已完整解压，再用对应 Agent 打开这个项目。

使用 Python **3.11 或 3.12**，在项目根目录安装依赖：

```bash
python -m pip install -r requirements.txt
python -m pip check
```

正式交付还需要安装 **LibreOffice**，并使 `soffice` 或 `libreoffice` 可用。没有它可以进行前期工作，但不能通过最终 PDF 渲染检查。

### 3. 放入赛题与附件

在项目根目录创建 `problem_files/`，放入赛题、官方附件与数据。例如 Codex 项目：

```text
your-project/
├── .agents/skills/
├── requirements.txt
└── problem_files/
    ├── 赛题.pdf
    └── 附件.xlsx
```

Claude Code 或 Trae 使用上表中自己的 Skill 目录，输入目录保持不变。

### 4. 对 Agent 说

```text
请使用 $paper-workflow-orchestrator 完成这个数学建模项目。
赛题和官方附件已放在 problem_files/。
先预检输入，再按 S0-S8 执行，必须真实运行代码并保留结果证据。
采用完整章节写作，允许分多轮完成，最后统一全文，不要只输出摘要或拼接微单元。
请核对当年赛题的篇幅和格式规则，不自行降低为短报告。
所有赛题产物写入 paper_output/；证据、写作与 Word/PDF 检查未通过，不要称为最终稿。
```

正常使用不需要手工执行整套脚本。若 Agent 没有识别入口，让它先读取所安装目录中的 `paper-workflow-orchestrator/SKILL.md`。继续上次任务、修复章节的提示词见 [启动与恢复提示词](docs/starter-prompts.md)。

完成后先查看：

| 产物 | 位置 |
|---|---|
| 正式 Word | `paper_output/final_paper.docx` |
| 正式 Markdown 源稿 | `paper_output/final_paper_source.md` |
| 渲染 PDF | `paper_output/qa/rendered/final_paper.pdf` |
| 代码、结果与图表 | `paper_output/code/`、`results/`、`figures/`、`tables/` |
| 最终检查报告 | `paper_output/format_check_report.json` |

## 原理介绍

### 先计算、后成文

Standard 保留 S0-S8 单一工作流。不同 Skills 各自负责一个环节，用实际文件和证据交接，而不是仅依赖对话记忆。

```text
S0 输入与安装预检 → S1 题意分析 → S2 模型路线
→ S3 数据与图表计划 → S4 编写代码 → S5 真实运行
→ S6 证据检查 → S7 自适应正式写作 → S8 Word/PDF 检查
```

脚本、输入和输出都记录 SHA-256。证据或已审计文件变化后，依赖它们的通过状态会失效，必须重新计算或验证。安装目录只保存通用能力，当前赛题代码始终写到 `paper_output/code/`。

### 章节写作与局部修复

`paper-formal-writer` 是唯一正式主笔：先制定写作计划，再按完整章节写作与审计；全部章节通过后确定性合并，由 Agent 全文统一改写，最后生成 DOCX。

默认完整竞赛稿使用 `section` 模式。明确要求的短报告可使用 `global`，同类问题连续两次失败后转为章节写作。单章同类问题连续两次失败才启用局部 `micro-repair`；第三次仍失败则阻塞并报告原因，不自动切换版本。旧微单元与 quickstart 只保留为非正式草稿。

### 篇幅、证据与渲染检查

默认完整稿规划至少 14000 有效字符，检查主稿至少 8000 有效字符、附录前渲染页数至少 18 页。**这些是防止极短稿的项目默认值，不是所有比赛的统一规定，也不是优秀论文标准。** 具体比赛的页数上限和计页方式仍要单独核对。

每问需要实质性的建模、计算结果与解释；注释、代码块和附录不能用于填补主稿长度。范围调整或短报告必须明确说明理由，不用空页、放大排版或重复正文凑数。

正式稿要求新鲜的证据与写作检查、可编辑的 Word OMML 公式和真实 LibreOffice 渲染。完整稿和短报告不能通过 `--render skip` 完成最终检查；仅明确的安装测试允许豁免，并标记为 `SMOKE_TEST_ONLY`。

## 验证状态与详细文档

- 发布提交已通过原有 42 项回归和新增 14 项范围与渲染检查；[CI](https://github.com/yushui2022/MathModel-Skill/actions/runs/33940797268) 覆盖 Windows/Ubuntu、Python 3.11/3.12，并含 LibreOffice 渲染任务。
- 历史 B 题工程示例没有重新生成，可用于理解产物组织方式，不代表通过当前全部检查。真实赛题约 20 页终稿的质量验收仍未完成。
- [安装指南](docs/agent-install-guide.md) · [正式写作指南](docs/formal-paper-authoring.md) · [工作流契约](docs/workflow-contracts.md) · [输出目录](docs/output-layout.md)
- 分支 `dist/` 是随提交维护的构建包；上面的 Release 是固定版本快照，不会随 README 更新而被覆盖。

开发者可在仓库中执行：

```bash
python scripts/sync_platform_packages.py --check
python -u tests/run_tests.py
python tests/test_paper_scope.py
python scripts/build_release_packages.py --verify
```

[MIT License](LICENSE)，Copyright (c) 2026 yushui2022.
