<div align="center">
  <img src="./assets/mathe-skill-logo.svg" alt="MathModel Skill Lite" width="120" height="120" />

# MathModel Skill Lite

### 一个入口、六步流程，完成基础数学建模报告

[![Version](https://img.shields.io/badge/version-2.2.1--lite.3-0f766e)](https://github.com/yushui2022/MathModel-Skill/releases/tag/v2.2.1-lite.3)
[![Platforms](https://img.shields.io/badge/platforms-Codex%20%7C%20Claude%20Code%20%7C%20Trae-111827)](#快速导入使用)
[![License](https://img.shields.io/badge/license-MIT-16a34a)](./LICENSE)

</div>

MathModel Skill 帮助编程 Agent 从赛题和附件出发，分析问题、运行建模代码、整理真实结果并生成论文或报告。**Lite 2.2.1-lite.3** 是其中面向普通、较旧或短上下文模型的简易版本，只提供一个 `mathmodel-lite` 入口，减少流程选择和中间文件负担。

Lite 会产出建模代码、计算结果、图表、Markdown 与基础 Word 报告，并检查输入和运行结果是否发生变化。它不提供原生 Word 公式、严格引文审计或 PDF 渲染验收，不能把基础报告检查通过当作约 20 页正式竞赛论文验收。

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

### 1. 下载一个 Lite 安装包

**一个项目只安装一个版本、一个平台包。** 普通模型、基础报告选择当前 Lite；正式竞赛写作可选 [Standard](https://github.com/yushui2022/MathModel-Skill/tree/master)，需要高计算投入和独立复算可选 [Pro 预发布版](https://github.com/yushui2022/MathModel-Skill/tree/pro)。

从 [Lite 2.2.1-lite.3 Release](https://github.com/yushui2022/MathModel-Skill/releases/tag/v2.2.1-lite.3) 下载：

| 平台 | 直接下载 | 解压后的 Skill 目录 |
|---|---|---|
| Codex | [Codex 安装包](https://github.com/yushui2022/MathModel-Skill/releases/download/v2.2.1-lite.3/MathModel-Skill-Lite-Codex.zip) | `.agents/skills/` |
| Claude Code | [Claude Code 安装包](https://github.com/yushui2022/MathModel-Skill/releases/download/v2.2.1-lite.3/MathModel-Skill-Lite-Claude-Code.zip) | `.claude/skills/` |
| Trae | [Trae 安装包](https://github.com/yushui2022/MathModel-Skill/releases/download/v2.2.1-lite.3/MathModel-Skill-Lite-Trae.zip) | `.trae/skills/` |

使用这些平台安装包，不要把 GitHub 的仓库源码 ZIP 当作安装包。可用 [SHA256SUMS.txt](https://github.com/yushui2022/MathModel-Skill/releases/download/v2.2.1-lite.3/SHA256SUMS.txt) 核对下载文件。

### 2. 解压并准备环境

在独立的建模项目目录中解压，保留完整 Skill 文件夹，不覆盖用户已有 `AGENTS.md` / `CLAUDE.md`。确认隐藏的 Skill 目录已解压，再用对应 Agent 打开项目。

使用 Python **3.11 或 3.12**，在项目根目录运行：

```bash
python -m pip install -r requirements.txt
python -m pip check
```

Lite 只使用精简 Python 依赖，**不需要 LibreOffice 或 TeX**。

### 3. 放入题目，启动 Agent

创建 `problem_files/`，放入赛题和附件。例如 Codex 项目：

```text
your-project/
├── .agents/skills/mathmodel-lite/
├── requirements.txt
└── problem_files/
    ├── 赛题.pdf
    └── 附件.xlsx
```

题面由 Agent 读取；遇到无法读取的扫描件或附件时，先补充可读文本或文件，不猜测内容。然后对 Agent 说：

```text
请使用 $mathmodel-lite，赛题和附件已经放在 problem_files/。
按固定六步完成：预检、计划、建模脚本、真实运行、写报告、检查并生成 Word。
所有产物写入 paper_output_lite/，不要读取其他版本的旧结果。
每个问题分别说明方法、关键数值、检验和局限，允许分多轮写完整基础稿。
除非我明确要求，不改成短报告或安装测试模式。
只有 lite_report.json 为 PASS 后，才交付对应范围的 paper.docx。
```

若 Agent 没有识别入口，让它先读取所安装目录中的 `mathmodel-lite/SKILL.md`。正常使用不需要逐条运行脚本；更多说明见 [Lite 启动提示词](docs/lite-starter-prompt.md)。

完成后查看 `paper_output_lite/paper.docx`、`paper.md` 和 `lite_report.json`；代码、结果和图表也保留在同一输出目录。

## 原理介绍

### 一条线性流程

```text
赛题与附件
→ 输入预检 → 最小计划 → 一个 model.py → 真实运行
→ 根据 results.json 写报告 → 最终检查与 Word 导出
```

三个用户命令分别是 `lite_preflight.py`、`lite_run.py` 和 `lite_finalize.py`。其他共享脚本服务于这些命令，不增加新的模型决策步骤或多 Skill 路由。

### 用脚本守住真实性底线

预检记录附件清单和 SHA-256，运行时绑定计划、代码、输入与输出。输入、计划或代码发生变化后必须重新预检或运行；每次运行清除旧 `results.json`，不能用空操作冒充新计算。

执行默认超时 300 秒，可根据算法显式调整；文件路径必须留在项目内。这些是运行与文件完整性保护，不是针对任意代码的安全沙箱。

### 基础报告不等于竞赛终稿

默认基础报告至少 1500 有效字符，每问独立标题下至少 150 字符，数值指标必须出现在对应问题的正文中。脚本还检查空答案、非有限指标、占位内容、重复正文和缺失证据。

图片必须对应运行记录，导出时真正嵌入 DOCX，之后重新打开核对。它不检查原生 Word OMML、严格正文引文或最终 PDF 排版。

只有用户明确要求时才声明短报告或测试范围，并说明理由。篇幅门槛用于拦截过短或不完整报告，不证明建模假设正确或论文优秀。

## 验证状态与详细文档

- 发布提交通过 15 项本地自动测试；[CI](https://github.com/yushui2022/MathModel-Skill/actions/runs/33940773858) 覆盖 Windows/Ubuntu、Python 3.11/3.12 与确定性安装包检查。
- [安装指南](docs/agent-install-guide.md) · [固定流程与范围说明](docs/lite-workflow.md) · [启动提示词](docs/lite-starter-prompt.md)
- 当前分支只维护 Lite，不包含 Standard 或 Pro 的工作流。分支 `dist/` 随提交更新，Release 保留固定发布快照。

开发者可在仓库中执行：

```bash
python scripts/sync_platform_packages.py --check
python tests/run_lite_tests.py
python scripts/build_release_packages.py --verify
```

[MIT License](LICENSE)，Copyright (c) 2026 yushui2022.
