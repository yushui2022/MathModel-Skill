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

**版本分工：低负担 → 速度优先 → 标准交付 → 旗舰验证**

Lite、Flash、Standard、Pro 的定位不同，分别在独立 Git 分支维护，不是安装后的切换模式。Flash 是速度优先路线，不表示它在质量档位上高于 Lite：

| 档位与版本 | 推荐模型示例 | 流程与交付能力 |
|---|---|---|
| **速度优先** [**Flash（预发布）**](https://github.com/yushui2022/MathModel-Skill/tree/flash) | **DeepSeek/Gemini/GLM 等 Flash 类模型**；优先快速出稿 | **基础长文草稿**：真实实验、图表、结果和约 18–22 页目标的 Word；不含严格终稿门禁。 |
| **1 · 入门档** [**Lite**](https://github.com/yushui2022/MathModel-Skill/tree/lite) | **DeepSeek 等模型**；优先低负担运行 | **基础建模报告**：一个入口、六步流程，真实计算与基础 Word 导出；不含严格引文、原生 Word 公式和 PDF 验收。 |
| **2 · 标准档** [**Standard（默认）**](https://github.com/yushui2022/MathModel-Skill/tree/standard) | **[GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol) / [Claude Opus 5.5](https://platform.claude.com/docs/en/models/opus-5-5/overview)** 等；兼顾能力与投入，旧款强模型仍可用 | **正式竞赛论文**：完整章节写作、证据与写作检查、原生公式 Word 和 PDF 渲染检查，流程复杂度可控。 |
| **3 · 旗舰档** [**Pro（预发布）**](https://github.com/yushui2022/MathModel-Skill/tree/pro) | **[GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra) / [Claude Fable 5.1](https://platform.claude.com/docs/en/models/fable-5-1/overview)**，以及 **Opus 5.5 / GPT-6.1 Sol**；接受高计算投入 | **高强度研究与验证**：多路线比较、独立复算、稳健性实验、五角色审稿和 Word/PDF 检查；有三个用户确认点。 |

模型推荐更新于 **2026-10-07**：已核对 Opus 5.5、Fable 5.1、GPT-6.1 Sol 的官方配置资料，尚未完成这些模型的完整赛题长文实测。**档位区分的是工作流，不是模型使用权限**：同一个模型可选 Standard 控制投入，也可选 Pro 加深验证；GPT-5.5、GPT-5.6 Sol 等旧款强模型仍可使用 Standard。

这不是对同品牌所有模型的固定排名，也不是质量认证。模型名称、API 档位与宿主实际能力须分开核对；中转站的显示名不能证明底层型号。

另有 [**LaTeX（实验性预发布）**](https://github.com/yushui2022/MathModel-Skill/tree/Latex)：旧版工作流的 TeX/PDF 导出分支，**不是另一个能力档位**，也不是当前 Standard 或 Pro 的 LaTeX 模式。

**一个项目只安装一个版本、一个安装位置，不要混装。** Flash 只追求快速基础稿；需要正式交付请选 Standard，需要最高验证深度请选 Pro。各版本的具体导入方法见下方快速使用说明。

## 小红书

作者：**Orlando Liu（奥兰多）**，小红书号：[`xiaoyushui2022`](https://www.xiaohongshu.com/user/profile/610d282b0000000001004ffb)。点击图片进入主页，也可以扫码找到我。

<p align="center">
  <a href="https://www.xiaohongshu.com/user/profile/610d282b0000000001004ffb">
    <img src="./assets/orlando-liu-social.jpg" alt="Orlando Liu 小红书主页与二维码" width="480" />
  </a>
</p>

## TokensFactory

<p align="center">
  <a href="https://tokensfactory.cc/">
    <img src="./assets/tokensfactory-logo.png" alt="TokensFactory Logo" width="96" />
  </a>
</p>

### TokensFactory

这是我的大学朋友 **Yeadon** 开的中转站，也非常感谢他当年带我走向 AI 的道路。[TokensFactory](https://tokensfactory.cc/) 支持 OpenAI、Claude、Gemini 等兼容接口，主打一个**量大管饱**，适合需要快速调用图片、视频或文本模型的个人开发者和团队。需要接入 Agent 时，可以查看 [TokensFactory Agent 快速接入](https://tokensfactory.cc/skills)。


## 快速导入使用

### 1. 下载一个通用包

当前分支版本为 **2.0.0-latex.1**。下载 [MathModel-Skill-LaTeX.zip](https://github.com/yushui2022/MathModel-Skill/raw/refs/heads/Latex/dist/MathModel-Skill-LaTeX.zip) 和 [SHA256SUMS.txt](dist/SHA256SUMS.txt)。这是分支构建，不是新建的正式 Release；历史 Release 平台包不作改动。

**同一份内容适用于不同宿主，不再分别下载 Claude、Codex、Trae 包。** ZIP 内有完整 `skills/`、安全安装器、依赖与启动说明。

### 2. 选择一个项目安装位置

先解压到独立下载目录，再执行（赛题目录必须已经存在）：

```bash
python "<解压目录>/install.py" --project-root "<赛题目录>" --platform codex --check
python "<解压目录>/install.py" --project-root "<赛题目录>" --platform codex
```

| 宿主 | 安装参数 | 项目内目标目录 |
|---|---|---|
| Codex | `--platform codex` | `.agents/skills/` |
| Claude Code | `--platform claude` | `.claude/skills/` |
| Trae | `--platform trae` | `.trae/skills/` |

一个项目只选一个位置。安装器仅使用 Python 3.11+ 标准库，不联网、不自动安装依赖，不覆盖 `AGENTS.md`、`CLAUDE.md`、其他 Skill、附件或已有论文。手动安装可完整复制 `skills/` 内全部目录到一个目标位置，不要只复制 `SKILL.md`。

无记录旧包、混装、用户修改和不完整安装会阻塞，不会自动清理。已托管且未改动的同主版本安装，先停止建模任务，再用 `--check --upgrade` 检查，确认后用 `--upgrade`；中断时用 `--recover` 回滚。安装器不重新批准任何旧证据。

### 3. 准备环境并启动

在选定的 Python 环境中手动安装依赖：

```bash
python -m pip install -r "<解压目录>/requirements.txt"
python -m pip check
```

把题面和原始附件放到赛题目录的 `problem_files/`，用宿主打开该赛题目录并刷新 Skill 列表。让 Agent 读取实际安装位置中的 **paper-workflow-orchestrator/SKILL.md**，按[启动提示词](docs/starter-prompts.md)开始。

`<SKILL_ROOT>` 指实际加载的所有 Skill 的父目录，须替换为真实绝对路径；脚本从赛题根目录运行，不在安装目录生成结果。Pro 的平台参数仅记录宿主能力，不改变 payload。详细见[安装与恢复说明](docs/agent-install-guide.md)。

LaTeX 仍是旧版工作流的实验性导出分支，不等同于新版 Standard；生成 PDF 需要单独配置 XeLaTeX。通用安装不会改变论文门禁或替代 TeX 编译器。

## 原理介绍

### 本轮证据加固

本分支继续是实验性 LaTeX 导出分支，只回移证据安全修复，不升级成 Standard 或 Pro：

- S6 改为正向状态白名单，拒绝 FAIL、未知状态、冲突状态及非有限数值。
- 图表必须能实际读取，并登记在对应问题的运行输出中；拒绝探索草图、损坏图片、畸形表格、重复问题 ID 和路径逃逸。
- 新报告包含 `policy_version=2`，旧 PASS 不再直接用于正式导出；升级后重新执行证据门禁。
- 通用绘图预览只供探索，不自动生成敏感性结论；需读取原题核对图片、公式和问题边界。

LaTeX 仍保留旧式 `execution_provenance`，不是 Pro 的独立运行回执与复算认证。文件可读和路径关联不能证明计算正确；真实 XeLaTeX 编译、公式排版与数学结论仍需单独验收。


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

本轮通用包验证见[安装迁移验收记录](docs/universal-package-validation.md)，之前的门禁修复见[证据加固记录](docs/evidence-hardening-validation.md)。历史 CI 链接不代表本轮提交已在远端通过。

- 历史发布提交通过 16 项导出完整性、故障注入及确定性打包测试；[CI](https://github.com/yushui2022/MathModel-Skill/actions/runs/33940774139) 覆盖 Windows/Ubuntu、Python 3.11/3.12。
- **上述测试不等于真实 XeLaTeX 编译验收，也不是整套旧版工作流的全面认证。** 当前保持 Preview 状态。
- 历史 [B 题工程示例](examples/cumcm2024-b-demo/README.md) 未重生成，只用于查看历史产物，不证明满足新增门槛。原理与旧流程细节见 [工作流契约](docs/workflow-contracts.md)。
- 历史 Release 使用日期快照；新通用构建使用 VERSION 中的语义版本；分支 `dist/` 随提交更新，Release 标签与附件保持不变。

维护者可在仓库中执行：

```bash
python scripts/check_skills.py
python -S tests/test_installation.py
python tests/test_installed_workflow.py
python tests/test_latex_integrity.py
```
