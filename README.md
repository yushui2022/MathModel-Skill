<div align="center">
  <img src="./assets/mathmodel-banner.png" alt="MathModel Skill：豆包坐镇指挥，Fable 推导模型，Astra 编写代码" width="100%" />

# MathModel Skill LaTeX

### 从有证据支撑的论文源稿导出 LaTeX 与 PDF

[![Status](https://img.shields.io/badge/status-Preview-d97706)](https://github.com/yushui2022/MathModel-Skill/releases/tag/latex-2026.09.05)
[![Snapshot](https://img.shields.io/badge/snapshot-2026.09.05-0f766e)](https://github.com/yushui2022/MathModel-Skill/releases/tag/latex-2026.09.05)
[![Platforms](https://img.shields.io/badge/platforms-Codex%20%7C%20Claude%20Code%20%7C%20Trae-111827)](#快速导入使用)

</div>

MathModel Skill 帮助编程 Agent 完成题意分析、建模代码、真实计算和论文写作。当前 `Latex` 分支在旧版工作流上提供额外的 LaTeX 导出：复用正式 Markdown 源稿与计算证据，生成 `.tex`，并可通过 XeLaTeX 编译 PDF。

**这是旧版实验性分支，不是当前 Standard 或 Pro 的 LaTeX 模式。** 本次发布为 `latex-2026.09.05` 日期快照，重点加固导出完整性；未完成真实 XeLaTeX 编译验收。普通正式论文任务优先使用 [Standard](https://github.com/yushui2022/MathModel-Skill/tree/standard)，高计算投入与独立复算选择 [Pro](https://github.com/yushui2022/MathModel-Skill/tree/pro)。

**能力档位：入门 → 标准 → 旗舰**

三个主版本按模型能力要求、流程复杂度与验证深度，从低到高分档；分别在独立 Git 分支维护，不是安装后的切换模式：

| 档位与版本 | 推荐模型示例 | 流程与交付能力 |
|---|---|---|
| **1 · 入门档** [**Lite**](https://github.com/yushui2022/MathModel-Skill/tree/lite) | **DeepSeek 等模型**；优先低负担运行 | **基础建模报告**：一个入口、六步流程，真实计算与基础 Word 导出；不含严格引文、原生 Word 公式和 PDF 验收。 |
| **2 · 标准档** [**Standard（默认）**](https://github.com/yushui2022/MathModel-Skill/tree/standard) | **[GPT-5.5](https://developers.openai.com/api/docs/models/gpt-5.5) / [GPT-5.6 Sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol)** 等；兼顾能力与投入 | **正式竞赛论文**：完整章节写作、证据与写作检查、原生公式 Word 和 PDF 渲染检查，流程复杂度可控。 |
| **3 · 旗舰档** [**Pro（预发布）**](https://github.com/yushui2022/MathModel-Skill/tree/pro) | **[GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra) / [Claude Fable 5.1](https://platform.claude.com/docs/en/models/fable-5-1/overview)** 等前沿模型；接受高计算投入 | **高强度研究与验证**：多路线比较、独立复算、稳健性实验、五角色审稿和 Word/PDF 检查；有三个用户确认点。 |

这是本项目的推荐搭配，不是对同品牌所有模型的固定排名，也不代表已完成实战认证；最终看具体型号、推理档位与工具能力。

另有 [**LaTeX（实验性预发布）**](https://github.com/yushui2022/MathModel-Skill/tree/Latex)：旧版工作流的 TeX/PDF 导出分支，**不是第四个能力档位**，也不是当前 Standard 或 Pro 的 LaTeX 模式。

**一个项目只安装一个版本、一个平台包，不要混装。** 各版本的具体导入方法见下方快速使用说明。

## 小红书

作者：**Orlando Liu（奥兰多）**，小红书号：[`xiaoyushui2022`](https://www.xiaohongshu.com/user/profile/610d282b0000000001004ffb)。点击图片进入主页，也可以扫码找到我。

<p align="center">
  <a href="https://www.xiaohongshu.com/user/profile/610d282b0000000001004ffb">
    <img src="./assets/orlando-liu-social.jpg" alt="Orlando Liu 小红书主页与二维码" width="480" />
  </a>
</p>

## 快速导入使用

### 1. 下载对应平台的实验包

从 [LaTeX 2026.09.05 Release](https://github.com/yushui2022/MathModel-Skill/releases/tag/latex-2026.09.05) 下载一个安装包：

| 平台 | 直接下载 | 解压后的 Skill 目录 |
|---|---|---|
| Codex | [Codex 安装包](https://github.com/yushui2022/MathModel-Skill/releases/download/latex-2026.09.05/MathModel-Skill-Codex.zip) | `skills/`（旧版路径） |
| Claude Code | [Claude Code 安装包](https://github.com/yushui2022/MathModel-Skill/releases/download/latex-2026.09.05/MathModel-Skill-Claude-Code.zip) | `.claude/skills/` |
| Trae | [Trae 安装包](https://github.com/yushui2022/MathModel-Skill/releases/download/latex-2026.09.05/MathModel-Skill-Trae.zip) | `.trae/skills/` |

**包名与 Standard 相同，但内容不同，必须从本 Release 下载。一个项目只安装一个版本、一个平台包。** 可用 [SHA256SUMS.txt](https://github.com/yushui2022/MathModel-Skill/releases/download/latex-2026.09.05/SHA256SUMS.txt) 核对文件。GitHub 的仓库源码 ZIP 不是平台安装包。

### 2. 导入并准备运行环境

把完整安装包解压到独立建模项目。不要覆盖用户已有 `AGENTS.md` / `CLAUDE.md`；包内的 `docs/AGENTS.example.md` 或 `docs/CLAUDE.example.md` 仅为旧版入口示例，不应整份替换用户配置。

建议使用本次完整性 CI 测试的 Python **3.11 或 3.12**。在项目根目录安装旧版工作流的依赖：

```bash
python -m pip install -r requirements.txt
```

只导出 `.tex` 不需要 TeX 发行版；编译 PDF 需要安装带 CTeX 中文支持的 TeX Live、MiKTeX 或 MacTeX，并确保 `xelatex` 在 PATH 中。可先运行：

```bash
xelatex --version
```

### 3. 放入题目并生成论文源稿

创建 `problem_files/`，放入赛题与附件，再让 Agent 读取当前平台的入口文件：

| 平台 | 要读取的入口 |
|---|---|
| Codex | `skills/paper-workflow-orchestrator/SKILL.md` |
| Claude Code | `.claude/skills/paper-workflow-orchestrator/SKILL.md` |
| Trae | `.trae/skills/paper-workflow-orchestrator/SKILL.md` |

Codex 这里使用旧版路径，不能假定会像现代包一样自动发现；直接让 Agent 读取上表文件。启动提示词：

```text
请读取当前平台的 paper-workflow-orchestrator/SKILL.md，使用这个 LaTeX 分支。
赛题和附件已放在 problem_files/，全部当前赛题产物写入 paper_output/。
先分析题意、编写并运行代码、核验证据，再完成正式 Markdown 源稿与旧版 Word 工作流。
之后从同一源稿导出 LaTeX；需要 PDF 时实际编译并执行 --require-pdf 检查。
缺少依赖或检查失败时报告原因，不得把旧 PDF 或 SOURCE_ONLY 当作 PDF 交付通过。
```

### 4. 导出 LaTeX，检查 PDF

以下以 Claude Code 为例；Codex 将整个 `.claude/skills/` 前缀替换为 `skills/`，Trae 替换为 `.trae/skills/`。

只需要 TeX 源文件时：

```bash
python .claude/skills/paper-formal-writer/scripts/format_formal_latex.py
python .claude/skills/paper-formal-writer/scripts/check_latex_format.py
```

需要 PDF 时：

```bash
python .claude/skills/paper-formal-writer/scripts/format_formal_latex.py --compile
python .claude/skills/paper-formal-writer/scripts/check_latex_format.py --require-pdf
```

完成后查看 `paper_output/final_paper.tex`、`final_paper.pdf` 和 `latex_check_report.json`。只生成 TeX 的检查状态是 `SOURCE_ONLY`，不代表 PDF 已验收。旧版 Word 文件仍在 `paper_output/final_paper.docx`。

## 原理介绍

### 同一源稿，多种输出

```text
赛题与附件 → 题意分析 → 模型与真实代码计算
→ 结果、图表与证据检查 → 正式 Markdown 与旧版 Word 工作流
→ Markdown 转 CTeX → XeLaTeX 编译 → PDF 完整性检查
```

LaTeX 不是另一套绕过计算的论文生成流程。导出读取 `final_paper_source.md`、正式大纲、图表与表格索引；正式导出必须有当前有效的证据报告。

### 为什么不能复用旧 PDF

证据输入、代码与结果建立快照，导出时记录源稿与 TeX 哈希，编译后记录 PDF 哈希。输入或产物变化会让当前导出不再有效；编译前清除旧的目标 PDF，避免失败时误交旧文件。

XeLaTeX 使用超时保护并禁用 shell escape。最终检查核对编译记录、文件哈希、页数和可提取文本；缺编译器、超时、空文件、损坏文件或失效证据都不能作为成功 PDF 交付。

### 篇幅与能力边界

完整稿默认检查至少 8000 主稿字符和 18 页总 PDF，这是拦截极短稿的默认门槛，不是所有比赛的统一规则。总页数不能证明正文充分，也不能替代人工检查摘要、正文、附录边界及当年的页数上限。

明确要求短报告或安装测试时，可在 `paper_outline.json.delivery` 中声明相应模式与理由。旧版导出检查不等于当前 Standard 的全部写作、公式与渲染检查，更不等于 Pro 的独立复算和五角色评审。

## 验证状态与详细文档

- 发布提交通过 16 项导出完整性、故障注入及确定性打包测试；[CI](https://github.com/yushui2022/MathModel-Skill/actions/runs/33940774139) 覆盖 Windows/Ubuntu、Python 3.11/3.12。
- **上述测试不等于真实 XeLaTeX 编译验收，也不是整套旧版工作流的全面认证。** 当前保持 Preview 状态。
- 历史 [B 题工程示例](examples/cumcm2024-b-demo/README.md) 未重生成，只用于查看历史产物，不证明满足新增门槛。原理与旧流程细节见 [工作流契约](docs/workflow-contracts.md)。
- 当前分支以日期快照发布；分支 `dist/` 随提交更新，Release 标签与附件保持不变。

维护者可在仓库中执行：

```bash
python scripts/sync_latex_hotfix.py --check
python tests/test_latex_integrity.py
```
