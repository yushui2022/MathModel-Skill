<div align="center">
  <img src="./assets/mathmodel-banner.png" alt="MathModel Skill：豆包坐镇指挥，Fable 推导模型，Astra 编写代码" width="100%" />

# MathModel Skill Pro

### 高计算投入、独立复算与多角色审稿的数学建模工作流

[![Version](https://img.shields.io/badge/version-3.3.0--pro.1-0f766e)](https://github.com/yushui2022/MathModel-Skill/releases/tag/v3.3.0-pro.1)
[![Status](https://img.shields.io/badge/status-Preview-d97706)](https://github.com/yushui2022/MathModel-Skill/releases/tag/v3.3.0-pro.1)
[![Platforms](https://img.shields.io/badge/platforms-Codex%20%7C%20Claude%20Code-111827)](#快速导入使用)
[![License](https://img.shields.io/badge/license-MIT-16a34a)](./LICENSE)

</div>

MathModel Skill 帮助编程 Agent 从题意分析、建模与真实计算，一直推进到有证据支撑的数学建模论文。**Pro 3.3.0-pro.1 定位旗舰档**，首选 GPT-6 Astra、Claude Fable 5.1 等高能力、长上下文模型：增加多路线比较、独立复算、稳健性实验和五角色审稿，优先追求可验证质量，而非最低时间和费用。

Pro 输出正式 Markdown、原生公式 Word、渲染 PDF，以及代码、图表、证据与评审记录。正常流程有 **三个用户确认点**，其余已授权工作自动推进。当前为 **Preview 预发布**：工程测试通过，但真实多问赛题约 20 页长文的前向质量验收尚未完成，不承诺论文优秀或竞赛获奖。

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

### 1. 确认使用范围并下载

Pro 适合能稳定执行长任务、复杂工具调用和隔离评审的模型。若希望控制复杂度，选择 [Standard](https://github.com/yushui2022/MathModel-Skill/tree/standard)；普通或较旧模型优先选择 [Lite](https://github.com/yushui2022/MathModel-Skill/tree/lite)。

**一个项目只安装一个版本、一个平台包。** Pro 只支持 Codex 与 Claude Code，不提供 Trae 包。从 [Pro 3.3.0-pro.1 Release](https://github.com/yushui2022/MathModel-Skill/releases/tag/v3.3.0-pro.1) 下载：

| 平台 | 直接下载 | 解压后的 Skill 目录 |
|---|---|---|
| Codex | [Codex 安装包](https://github.com/yushui2022/MathModel-Skill/releases/download/v3.3.0-pro.1/MathModel-Skill-Pro-Codex.zip) | `.agents/skills/` |
| Claude Code | [Claude Code 安装包](https://github.com/yushui2022/MathModel-Skill/releases/download/v3.3.0-pro.1/MathModel-Skill-Pro-Claude-Code.zip) | `.claude/skills/` |

使用平台安装包，不要把 GitHub 仓库源码 ZIP 当作安装包。可用 [SHA256SUMS.txt](https://github.com/yushui2022/MathModel-Skill/releases/download/v3.3.0-pro.1/SHA256SUMS.txt) 核验下载。

### 2. 导入项目并准备环境

把安装包解压到独立建模项目，保留完整 Skill 目录，不覆盖用户已有的 `AGENTS.md` 或 `CLAUDE.md`，再用对应 Agent 打开项目。

使用 Python **3.11 或 3.12**，在项目根目录运行：

```bash
python -m pip install -r requirements.txt
python -m pip check
```

还需要 **LibreOffice** 执行 DOCX → PDF 渲染。使 `soffice` 或 `libreoffice` 可用；Windows 也会检测默认安装位置。模型推理、代码运行和独立角色可能消耗较多时间与额度，请在开始前确认可用环境。

### 3. 放入赛题与附件

例如 Codex 项目：

```text
your-project/
├── .agents/skills/
├── requirements.txt
└── problem_files/
    ├── 赛题.pdf
    └── 附件.xlsx
```

Claude Code 使用 `.claude/skills/`，输入目录同样为 `problem_files/`。不要复制 Standard/Lite 的旧结果与批准记录。

### 4. 启动并在三个检查点确认

把提示词中的模型名和档位换成当前实际配置：

```text
请使用 $pro-workflow-orchestrator，从 P0 开始执行 MathModel Skill Pro。
赛题和附件已放在 problem_files/，当前模型为 <模型名>，推理档位为 <档位>。
全部赛题产物只写入 paper_output_pro/，不读取其他版本的旧结果。
默认完整竞赛论文，按当年规则规划篇幅，允许分多轮成稿，不自行降为简报。
在题意与论文范围、模型路线、数值结果与不确定性三个检查点等待我确认。
检查点之间持续完成已授权工作；只自动使用公开来源，其他资源先征得授权。
必须真实计算、独立复算和隔离审稿，Word/PDF 检查未通过不要称为正式交付。
```

收到三个检查点的结果后，分别确认题意与范围、模型路线、数值与不确定性，Agent 才会继续相应阶段。若入口未识别，让 Agent 先读取安装目录中的 `pro-workflow-orchestrator/SKILL.md`。完整提示词见 [START_HERE](docs/pro-start-prompt.md)。

完成后查看：

| 产物 | 位置 |
|---|---|
| Word、PDF 与正式源稿 | `paper_output_pro/final_paper.docx`、`final_paper.pdf`、`final_paper_source.md` |
| 冻结证据 | `paper_output_pro/evidence_freeze.json` |
| 五角色审稿报告 | `paper_output_pro/review_board_report.json` |
| 最终检查报告 | `paper_output_pro/pro_gate_report.json` |

## 原理介绍

### P0-P9 与三个确认点

```text
P0 能力与输入预检
→ P1 三路隔离审题 → [确认题意、附件与论文范围]
→ P2 公开研究与多路线比较 → [确认模型路线]
→ P3-P5 独立实现、复算与稳健性实验 → [确认数值与不确定性]
→ P6 证据冻结 → P7 全局写作
→ P8 五角色审稿与修复 → P9 Word/PDF 检查
```

每问默认比较四条实质不同的路线，包含可解释基线；关键结论至少通过两条独立实现或复算路径。随机算法默认至少运行 10 个不同种子，并按适用性开展敏感性、压力与消融测试，失败候选也保留记录。

三个批准点绑定上游文件哈希。输入、代码、结果或论文版本改变后，相应批准与下游检查失效，不能沿用旧的 `PASS`。

### 模型适配与隔离评审

P0 记录用户声明的模型、档位、平台、运行环境、联网和多代理能力，使用维护中的能力档案路由；未知模型会提示核验，但不会自动降低工作要求。**配置兼容不等于真实赛题合格认证**，具体型号由安装包内的 `pro-workflow-orchestrator/references/model-profiles.json` 维护。

多代理不可用时可以顺序运行真正独立的上下文；不能提供隔离环境时应报告能力缺口，不得用五个角色名称冒充五次独立审稿。数学正确性、代码复现、来源、表达和对抗质疑五个角色须审查同一版论文，无未解决 Critical/Major 问题后才能交付。

### 从冻结证据生成完整论文

正式源稿依据冻结证据撰写，每问覆盖选模理由、推导、求解、结果、验证和局限。允许按章节分多轮写作，最终全局统一；不使用机械微单元拼接，也不把单次回复限制当作论文篇幅。

默认以约 20 页、通常 18-24 页规划完整稿，8000 有效字符只是防止极短稿的下限，不是字符到页数的换算。具体范围在检查点 1 确认，并遵守当年赛题规则；短报告或测试必须明确声明，不能中途自行降低范围。

DOCX 由同一正式源稿生成原生 OMML 公式，再经 LibreOffice 渲染 PDF，核对文本、公式、图表、引用、真实页数及逐页视觉检查。附录、代码、重复段落或放大排版不能代替正文论证。

### 公开研究与持续执行

自动研究仅限公开资源，优先使用原始论文、官方数据库与数据发布者，关键外部数据尽量双权威源核验。登录、付费、私有或有额外授权要求的资源先征求用户授权，来源与用途保留在账本中。

Pro 不设任务总 Token、候选总量或运行时间预算；正常检查点之外，缺少必要数据或授权、超出任务范围，或同类失败连续三次时应停止报告，而不是无限重复失败。

## 验证状态与详细文档

- 发布提交通过 81 项本地自动测试，包含真实 LibreOffice 渲染；[CI](https://github.com/yushui2022/MathModel-Skill/actions/runs/33940773875) 覆盖 Windows/Ubuntu/macOS、Python 3.11/3.12。
- 现有五页构造算例和合成分页测试验证工程机制，不是完整竞赛长文的质量证据。真实多问赛题长文前向验收仍未完成，因此当前 Release 标记为 Preview。
- 升级到 3.3 须重新预检、计算与审批，不能复用旧版结果和批准。
- [完整启动提示词](docs/pro-start-prompt.md) · [机器契约](docs/pro-contracts.md) · [前向验收要求](docs/forward-evaluation.md) · [3.2 历史验收与样例](docs/pro-3.2-validation.md)
- 分支 `dist/` 随提交更新，已发布的标签和安装包保持固定快照，不随本文档更新而覆盖。

开发者可在仓库中执行：

```bash
python scripts/sync_platform_packages.py --check
python tests/run_pro_tests.py
python scripts/build_release_packages.py --verify
```

完整渲染测试需设置 `REQUIRE_LIBREOFFICE=1`。

[MIT License](LICENSE)，Copyright (c) 2026 yushui2022.
