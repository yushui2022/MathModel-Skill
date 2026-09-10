<div align="center">
  <img src="./assets/mathmodel-banner.png" alt="MathModel：从赛题分析到可复现的数学建模论文" width="100%" />

# MathModel for Codex

基于 MathModel Pro 的建模插件 · `0.5.0-alpha.1`

[![License](https://img.shields.io/badge/license-MIT-16a34a)](./LICENSE)
[插件使用说明](./plugins/mathmodel/README.md) · [实施与验证记录](./docs/plugin-upgrade-validation.md) · [Pro 契约](./docs/pro-contracts.md)

</div>

MathModel 帮助编程 Agent 分析赛题、比较模型、执行实验、追溯结论，再撰写和检查论文。这个插件分支将 **Pro 的 P0–P9 工作流**接入 Codex，并增加按问题恢复上下文、持久计算作业、修改影响分析和独立重放包。

当前为 Alpha 开发版本。工程测试验证了相应功能与门禁，不代表已经证明真实比赛论文质量优于 Pro，也不保证竞赛获奖。稳定的 Standard 历史版本仍可独立下载，入口保留在下方。

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

插件源码在 [`plugins/mathmodel/`](./plugins/mathmodel/)，构建包为 [`dist/MathModel-Codex-Plugin.zip`](./dist/MathModel-Codex-Plugin.zip)。按当前 Codex 宿主支持的插件安装方式启用后，在独立比赛目录放入 `problem_files/`，然后说：

> 请使用 MathModel 开始这个数学建模项目。赛题和附件在 problem_files/。先检查实际安装、模型和推理档位，再按 Pro 工作流推进；需要我确认时给出当前具体对象。

以后可以说“继续第二问”“第二问的数据改了，检查影响”“这句话的数字从哪来”。不需要先打开看板。主产物写入 `paper_output_pro/`，运行记录写入项目的 `.mathmodel/`，插件安装目录保存通用代码。

安装依赖、生成本机绝对 MCP 配置、恢复和重放命令见[插件使用说明](./plugins/mathmodel/README.md)。右侧页面需要宿主提供打开浏览器面板的能力；`open_workspace` 返回地址，不等于已经自动打开页面。本版本没有宣称 MCP Apps 或所有桌面宿主自动展示均已验收。

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
