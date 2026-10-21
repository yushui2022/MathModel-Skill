<div align="center">
  <img src="./assets/mathmodel-banner.png" alt="MathModel Skill：豆包坐镇指挥，Fable 推导模型，Astra 编写代码" width="100%" />

# MathModel Skill Pro

### 高计算投入、独立复算与多角色审稿的数学建模工作流

[![Version](https://img.shields.io/badge/version-3.3.0--pro.4-0f766e)](https://github.com/yushui2022/MathModel-Skill/tree/pro)
[![Status](https://img.shields.io/badge/status-Preview-d97706)](https://github.com/yushui2022/MathModel-Skill/tree/pro)
[![Platforms](https://img.shields.io/badge/platforms-Codex%20%7C%20Claude%20Code-111827)](#快速导入使用)
[![License](https://img.shields.io/badge/license-MIT-16a34a)](./LICENSE)

</div>

MathModel Skill 帮助编程 Agent 从题意分析、建模与真实计算，一直推进到有证据支撑的数学建模论文。**Pro 3.3.0-pro.6 定位旗舰档**，推荐 GPT-6.1 Sol、Claude Opus 5.5、Claude Fable 5.1、GPT-6 Astra 等高能力、长上下文模型：增加多路线比较、独立复算、稳健性实验和五角色审稿，优先追求可验证质量，而非最低时间和费用。

Pro 输出正式 Markdown、原生公式 Word、渲染 PDF，以及代码、图表、证据与评审记录。正常流程有 **三个用户确认点**，其余已授权工作自动推进。当前为 **Preview 预发布**：工程测试通过，但真实多问赛题约 20 页长文的前向质量验收尚未完成，不承诺论文优秀或竞赛获奖。

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

当前分支版本为 **3.3.0-pro.6**。下载 [MathModel-Skill-Pro.zip](https://github.com/yushui2022/MathModel-Skill/raw/refs/heads/pro/dist/MathModel-Skill-Pro.zip) 和 [SHA256SUMS.txt](dist/SHA256SUMS.txt)。这是分支构建，不是新建的正式 Release；历史 Release 平台包不作改动。

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

把题面和原始附件放到赛题目录的 `problem_files/`，用宿主打开该赛题目录并刷新 Skill 列表。让 Agent 读取实际安装位置中的 **pro-workflow-orchestrator/SKILL.md**，按[启动提示词](docs/pro-start-prompt.md)开始。

`<SKILL_ROOT>` 指实际加载的所有 Skill 的父目录，须替换为真实绝对路径；脚本从赛题根目录运行，不在安装目录生成结果。Pro 的平台参数仅记录宿主能力，不改变 payload。详细见[安装与恢复说明](docs/agent-install-guide.md)。

Pro 的三次用户确认、独立复算和 Word/PDF 双门禁保持不变。安装到 Trae 或其他宿主不代表其多代理、联网或工具权限已验收；P0 必须记录实际能力，不具备隔离能力时不得伪造独立审稿。

## 原理介绍

本轮通用包验证见[安装迁移验收记录](docs/universal-package-validation.md)，之前的门禁修复见[证据加固记录](docs/evidence-hardening-validation.md)。历史 CI 链接不代表本轮提交已在远端通过。

### 本轮证据加固

Pro 3.3.0-pro.4 将图表检查前移到第三检查点，并在读取冻结证据时再次验证：损坏位图、空白图、畸形表格、探索草图以及未绑定成功实验的图表不能冻结。通用绘图预览不再自动标记为正式结果，也不从原始列直接推导敏感性图。

正式图表优先引用 `experiments/<run_id>/` 中的原始输出；复制到 `figures/` 或 `tables/` 时，需要在索引中提供 `run_id` 与 `output_path`，内容必须与运行回执哈希相同。详细格式见[图表证据契约](skills/pro-workflow-orchestrator/references/artifact-evidence.md)。

这是证据检查升级，不更改三个用户确认点，也不是新模型能力或论文获奖质量认证。旧项目需重新验证检查点与冻结，不能修改历史报告伪造通过。


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

| 当前模型 | API 标识 | 配置要点 |
|---|---|---|
| GPT-6.1 Sol | `gpt-6.1-sol` | 工具调用使用 Responses API；默认 `medium`，支持至 `max`，`ultra` 不是 API 档位。 |
| Claude Opus 5.5 | `claude-opus-5-5` | API 默认 `medium`；自适应思考常开，不能沿用关闭思考或强制工具的旧配置。 |
| Claude Fable 5.1 | `claude-fable-5-1` | API 默认 `high`；思考块绑定模型和会话，不能随意跨模型复制历史。 |

Pro 建议复杂建模与审稿从 `max`、正文写作从 `high` 开始实测，**不是已验证的最优档位**。P0 接受 `opus5.5`、`fable5.1`、`gptsol6.1` 等声明，但不会修改宿主配置、验证中转站底层模型或自动授予工具权限。旧模型档案保留；未知版本不再猜测为旧版本。依据与执行细节见[模型指南](https://github.com/yushui2022/MathModel-Skill/blob/pro/skills/pro-workflow-orchestrator/references/frontier-model-guidance.md)。

多代理不可用时可以顺序运行真正独立的上下文；不能提供隔离环境时应报告能力缺口，不得用五个角色名称冒充五次独立审稿。数学正确性、代码复现、来源、表达和对抗质疑五个角色须审查同一版论文，无未解决 Critical/Major 问题后才能交付。

### 从冻结证据生成完整论文

正式源稿依据冻结证据撰写，每问覆盖选模理由、推导、求解、结果、验证和局限。允许按章节分多轮写作，最终全局统一；不使用机械微单元拼接，也不把单次回复限制当作论文篇幅。

默认以约 20 页、通常 18-24 页规划完整稿，8000 有效字符只是防止极短稿的下限，不是字符到页数的换算。具体范围在检查点 1 确认，并遵守当年赛题规则；短报告或测试必须明确声明，不能中途自行降低范围。

DOCX 由同一正式源稿生成原生 OMML 公式，再经 LibreOffice 渲染 PDF，核对文本、公式、图表、引用、真实页数及逐页视觉检查。附录、代码、重复段落或放大排版不能代替正文论证。

### 公开研究与持续执行

自动研究仅限公开资源，优先使用原始论文、官方数据库与数据发布者，关键外部数据尽量双权威源核验。登录、付费、私有或有额外授权要求的资源先征求用户授权，来源与用途保留在账本中。

Pro 不设任务总 Token、候选总量或运行时间预算；正常检查点之外，缺少必要数据或授权、超出任务范围，或同类失败连续三次时应停止报告，而不是无限重复失败。

## 验证状态与详细文档

本轮通用包的安全安装、99 项回归及三种目录实际渲染验证见[迁移验收记录](docs/universal-package-validation.md)。下方版本数据为历史记录，不代表远端 CI 已验证本次迁移。

- 3.3.0-pro.2 分支更新新增模型识别、档位、独立核验日期和 Flash 混装回归覆盖；本地 90 项测试通过，含 LibreOffice 渲染。这是脚本与流程测试，不是三个新模型的在线实战测试。
- 历史发布提交通过 81 项本地自动测试，包含真实 LibreOffice 渲染；[CI](https://github.com/yushui2022/MathModel-Skill/actions/runs/33940773875) 覆盖 Windows/Ubuntu/macOS、Python 3.11/3.12。
- 现有五页构造算例和合成分页测试验证工程机制，不是完整竞赛长文的质量证据。真实多问赛题长文前向验收仍未完成，因此当前 Release 标记为 Preview。
- 升级到 3.3 须重新预检、计算与审批，不能复用旧版结果和批准。
- [完整启动提示词](docs/pro-start-prompt.md) · [机器契约](docs/pro-contracts.md) · [前向验收要求](docs/forward-evaluation.md) · [3.2 历史验收与样例](docs/pro-3.2-validation.md)
- 分支 `dist/` 随提交更新，已发布的标签和安装包保持固定快照，不随本文档更新而覆盖。

开发者可在仓库中执行：

```bash
python scripts/check_skills.py
python -S tests/test_installation.py
python tests/test_installed_workflow.py
python tests/run_pro_tests.py
python scripts/build_release_packages.py --verify
```

完整渲染测试需设置 `REQUIRE_LIBREOFFICE=1`。

[MIT License](LICENSE)，Copyright (c) 2026 yushui2022.
