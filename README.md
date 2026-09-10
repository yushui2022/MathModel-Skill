<div align="center">
  <img src="./assets/mathmodel-banner.png" alt="MathModel：从赛题分析到可复现的数学建模论文" width="100%" />

# MathModel for Codex

在 Codex 里，把赛题、模型、实验与论文接成一条可继续的工作流

MathModel Pro 核心 · Codex Plugin `0.5.0-alpha.1`

[![License](https://img.shields.io/badge/license-MIT-16a34a)](./LICENSE)
[认识插件](#mathmodel-plugin-是什么) · [安装与使用](./plugins/mathmodel/README.md#安装与环境) · [版本选择](#选择适合你的使用方式) · [实施记录](./docs/plugin-upgrade-validation.md)

</div>

MathModel 是面向数学建模比赛的 Agent 工作流项目，帮助你从赛题分析、模型比较和代码实现，推进到实验验证、论文写作与交付。

当前 `feat/codex-plugin` 分支维护 **MathModel Plugin**：将 Pro 的 P0–P9 流程、专业 Skills、本地计算服务和可选工作台整合进 Codex。讨论仍然在对话里进行，判断与结果保存在比赛项目中，让后续会话能根据实际文件接着工作。

> 当前版本为 **Alpha**。本页介绍已实现的功能；真实赛题相对 Pro 的论文质量对照、部分宿主接入与角色执行适配仍在完善。各项验证的实际范围见[实施记录](./docs/plugin-upgrade-validation.md)。

## MathModel Plugin 是什么

它是一个安装到 Codex 的第三方开源插件，围绕数学建模比赛组织三部分能力：

| 组成 | 在比赛中负责什么 |
|---|---|
| **专业 Skills** | 指导审题、选模、数据处理、编程、验证、写作与审稿，按 Pro 的阶段和检查点推进 |
| **本地运行服务与 MCP 工具** | 读取项目事实、管理实验与日志、检查结果、分析修改影响，供 Codex 调用 |
| **可选的右侧工作台** | 查看项目文件、真实图表、运行记录、验证问题和论文，把需要讨论的上下文带回对话 |

插件把相关能力作为一个整体安装和维护。多个 Skill 本身不会扩大模型上下文，也不会自动变成多个独立 Agent；专业判断仍由 Codex 和用户完成。它的实际价值在于：将比赛进展变成可读取、可检查、可恢复的项目记录。

## 在比赛中怎么用

| 比赛中的情况 | 你可以对 Codex 说 | 插件提供的帮助 |
|---|---|---|
| 刚拿到题目与附件 | “开始建模，先梳理每一问。” | 识别比赛目录与当前安装，按 Pro 进入审题和路线讨论 |
| 换了会话，继续一半的工作 | “继续第二问，先说明当前状态。” | 从项目契约恢复题意、假设、选中与淘汰路线、实验及未决问题，附原始来源 |
| 计算时间较长 | “看看这批实验跑到哪里了。” | 返回真实作业状态、日志与退出结果；可取消或重试已知任务 |
| 数据或代码有改动 | “第二问的数据改了，哪些要重算？” | 解释受到影响的实验、结论和章节，提示旧证据失效 |
| 开始整理论文 | “这句话的数字来自哪次实验？” | 连接结论、指标、运行回执、代码和输入版本；没有记录的部分明确保持未知 |
| 准备移交给队友 | “导出可复算的关键结果。” | 在当前证据冻结通过后，打包允许分发的输入、代码、依赖和独立重放入口 |

这些都是自然语言入口示例。Codex 会先读取当前项目和必要前置条件；“继续”不会跳过失效证据或尚未批准的模型路线。

## 插件比直接安装 Pro Skill 增加什么

| 能力 | Pro 已经提供 | 本插件增加 |
|---|---|---|
| 继续建模 | 阶段记忆、检查点、哈希与失败摘要 | 按小问组织题意、选模理由、回执、结论和写作定位；事实带来源与版本，恢复包可分页 |
| 管理实验 | 真实执行脚本、输入输出回执 | 项目运行服务、持久作业、幂等提交、日志游标、取消与重试；页面和 MCP 共享服务 |
| 数学检查 | 独立复算、稳健性与证据门禁 | 在显式启用的 LP/MILP 范围内，独立重算目标、约束、上下界和整数性，并检查可验证的最优界证书 |
| 修改后继续 | 哈希变化使批准或下游检查失效 | 解释哪些实验、结论和章节受到影响，列出依赖顺序；缺依赖声明时扩大核验范围 |
| 交付复算 | 记录解释器、环境、参数和结果 | 导出冻结代码、显式允许分发的输入、依赖版本及独立 runner，在新目录生成一致性报告 |

三路审题、多路线比较、路线淘汰理由、独立复算、三个用户确认点、证据冻结、双向结论映射和五角色审稿都是 **Pro 原有能力**。插件保留这些要求；进程退出成功、页面显示完成或重放一致，都不能替代正式门禁。

## 使用插件

1. 获取完整的[插件 ZIP](./dist/MathModel-Codex-Plugin.zip)或 [`plugins/mathmodel/`](./plugins/mathmodel/) 目录，按[安装说明](./plugins/mathmodel/README.md#安装与环境)完成本地安装和首次环境准备。
2. 在 Codex 打开独立的比赛目录，将题面和附件放入 `problem_files/`。安装或更新插件后，新建一个任务加载新版 Skills 与工具。
3. 对 Codex 说：

> 请使用 MathModel 开始这个数学建模项目。赛题和附件在 problem_files/。先检查实际安装、模型和推理档位，再按 Pro 工作流推进；需要我确认时给出当前具体对象。

之后按对话推进。Pro 保留三个需要真实决定的确认点：题意与范围、模型路线、结果与不确定性。其余已授权工作继续执行，已有有效批准不重复索取。

比赛目录按职责保留文件：

```text
my-contest/
├── problem_files/          题目、附件和原始数据
├── paper_output_pro/      模型、实验、证据、评审和正式论文
│   ├── code/
│   ├── experiments/
│   ├── final_paper_source.md
│   ├── final_paper.docx
│   └── final_paper.pdf
└── .mathmodel/             项目服务、持久任务和恢复快照
```

需要看结果时说“打开 MathModel 工作台”。右侧提供总览、流程、实验、代码与交付五个视图，可预览实际图表、CSV、带行号代码、Markdown 和 PDF，并操作检查、取消与重试。关闭页面后，独立计算仍可继续；异常中断的计算保留记录，是否能接着求解取决于具体程序。

右侧页面使用本地服务和 Codex 的浏览器面板能力。普通浏览器也能打开该页面；具体宿主是否支持自动打开由其能力决定。安装依赖、MCP 配置、恢复和重放命令见[插件使用说明](./plugins/mathmodel/README.md)。

## 选择适合你的使用方式

| 方式 | 适合的需求 | 入口 |
|---|---|---|
| **Codex Plugin · Alpha** | 希望在 Codex 中统一使用 Pro、项目恢复、实验管理和证据工作台 | [插件说明](./plugins/mathmodel/README.md) |
| **Pro 独立 Skill 包** | 已有自己的项目和执行习惯，主要需要完整建模方法与质量流程 | [Pro 分支](https://github.com/yushui2022/MathModel-Skill/tree/pro)；本分支平台源码说明见 [Codex](./packages/codex/README.md)、[Claude Code](./packages/claude/README.md) |
| **Standard / Lite** | 继续既有版本项目，或需要较轻的独立工作流 | 下方历史分发入口 |

### 第三方插件如何分发

本项目通过 GitHub 提供源码和插件 ZIP。作者自建 marketplace 表示提供一个可添加的分发目录，**不会让插件自动出现在所有人的官方插件列表里**。用户仍需获取插件或添加对应来源，并完成本地安装与环境准备。当前实际安装路径和版本边界写在插件 README 中。

### 当前范围

当前已接入按小问恢复、持久计算、LP/MILP 规格检查、修改影响分析、独立重放和实际产物预览。数学检查仅覆盖声明的线性/混合整数规格及相应证书；一般非线性问题和预测数据泄漏检查尚不在已实现范围内。宿主独立角色执行记录的自动收集、完整宿主兼容性与真实赛题盲评仍是后续工作。

工程样例、进程退出成功、门禁通过和论文质量评价是不同层面的结果。当前 Alpha 不将测试项数或样例论文作为优于 Pro、适合正式提交或能够获奖的证明。

## 历史版本与分发入口

一个比赛项目只使用一个 MathModel 版本和一个平台入口。已有 Standard 项目继续使用它自己的安装包与 `paper_output/`；安装 Pro 插件不会自动迁移旧批准。项目内另装了一套 MathModel Skill 时，先处理重复入口。

| 版本 | 分发入口 | 说明 |
|---|---|---|
| Standard 2.3.0 | [固定 Release](https://github.com/yushui2022/MathModel-Skill/releases/tag/v2.3.0) · [Standard 分支](https://github.com/yushui2022/MathModel-Skill/tree/standard) | S0–S8，保留独立的 Codex、Claude Code、Trae 包 |
| Pro | [Pro 分支](https://github.com/yushui2022/MathModel-Skill/tree/pro) | 本插件以 `3.3.0-pro.1`、提交 `da520d49c62c8f5dc3755eb16bedefd78e77b466` 为比较基线 |
| Lite | [Lite 分支](https://github.com/yushui2022/MathModel-Skill/tree/lite) | 独立的轻量工作流 |
| LaTeX 实验分支 | [LaTeX 分支](https://github.com/yushui2022/MathModel-Skill/tree/Latex) | 历史 TeX/PDF 路径，不是当前插件的切换模式 |

Standard 2.3.0 直接下载：[Codex](https://github.com/yushui2022/MathModel-Skill/releases/download/v2.3.0/MathModel-Skill-Codex.zip) · [Claude Code](https://github.com/yushui2022/MathModel-Skill/releases/download/v2.3.0/MathModel-Skill-Claude-Code.zip) · [Trae](https://github.com/yushui2022/MathModel-Skill/releases/download/v2.3.0/MathModel-Skill-Trae.zip) · [SHA256SUMS.txt](https://github.com/yushui2022/MathModel-Skill/releases/download/v2.3.0/SHA256SUMS.txt)。按下载包内的说明安装其依赖。GitHub 的仓库源码 ZIP 与这些固定发布包不同。

历史 Standard 文档：[安装指南](./docs/agent-install-guide.md) · [正式写作](./docs/formal-paper-authoring.md) · [启动与恢复](./docs/starter-prompts.md)。这些文档描述 Standard；当前插件以本页、插件 README 和 Pro 契约为准。

## 开发与验证

单一源码链为 `packages/claude/.claude/skills` → `packages/codex/.agents/skills` → `plugins/mathmodel/skills`。插件入口 `mathmodel-plugin-entry` 独立保留，生成目录中的核心文件不要直接修改。

```bash
python -B scripts/sync_platform_packages.py
python -B plugins/mathmodel/scripts/sync_plugin_skills.py
python -B plugins/mathmodel/scripts/sync_plugin_skills.py --check
python -B scripts/run_baseline_tests.py --edition standard
python -B scripts/run_baseline_tests.py --edition pro
python -B scripts/build_plugin_package.py
python -B scripts/build_plugin_package.py --verify
```

固定基线测试在隔离目录中执行：Standard 原断言和历史 ZIP 不被重写；Pro 原测试布局覆盖当前核心源码后执行。需要完整 Git 历史，CI 使用 `fetch-depth: 0`。启用 `REQUIRE_LIBREOFFICE=1` 并安装 LibreOffice 后才能覆盖 Pro 的完整渲染流水线。插件附加测试与本机实测结果见[验证记录](./docs/plugin-upgrade-validation.md)。本分支不要直接运行旧 Standard 发布脚本去重建历史 ZIP。

## 作者

Orlando Liu（奥兰多），小红书号 [`xiaoyushui2022`](https://www.xiaohongshu.com/user/profile/610d282b0000000001004ffb)。

<p align="center"><a href="https://www.xiaohongshu.com/user/profile/610d282b0000000001004ffb"><img src="./assets/orlando-liu-social.jpg" alt="Orlando Liu 小红书主页与二维码" width="360" /></a></p>

[MIT License](./LICENSE)，Copyright (c) 2026 yushui2022.
