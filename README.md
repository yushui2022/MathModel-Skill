<div align="center">
  <img src="./assets/mathmodel-banner.png" alt="MathModel Skill：豆包坐镇指挥，Fable 推导模型，Astra 编写代码" width="100%" />

# MathModel Skill Lite

### 一个入口、六步流程，完成基础数学建模报告

[![Version](https://img.shields.io/badge/version-2.2.1--lite.6-0f766e)](./VERSION)
[![Platforms](https://img.shields.io/badge/platforms-Codex%20%7C%20Claude%20Code%20%7C%20Trae-111827)](#快速导入使用)
[![License](https://img.shields.io/badge/license-MIT-16a34a)](./LICENSE)

</div>

MathModel Skill 帮助编程 Agent 从赛题和附件出发，分析问题、运行建模代码、整理真实结果并生成论文或报告。**Lite 2.2.1-lite.6 开发版定位入门档**，建议 DeepSeek 等模型或需要低负担运行的用户从此版本开始。它只提供一个 `mathmodel-lite` 入口，减少流程选择和中间文件负担，也适合较旧或短上下文模型。

Lite 会产出建模代码、计算结果、图表、Markdown 与基础 Word 报告，并检查输入和运行结果是否发生变化。它不提供原生 Word 公式、严格引文审计或 PDF 渲染验收，不能把基础报告检查通过当作约 20 页正式竞赛论文验收。

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

当前分支版本为 **2.2.1-lite.6**。下载 [MathModel-Skill-Lite.zip](https://github.com/yushui2022/MathModel-Skill/raw/refs/heads/lite/dist/MathModel-Skill-Lite.zip) 和 [SHA256SUMS.txt](dist/SHA256SUMS.txt)。这是分支构建，不是新建的正式 Release；历史 Release 平台包不作改动。

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

把题面和原始附件放到赛题目录的 `problem_files/`，用宿主打开该赛题目录并刷新 Skill 列表。让 Agent 读取实际安装位置中的 **mathmodel-lite/SKILL.md**，按[启动提示词](docs/lite-starter-prompt.md)开始。

`<SKILL_ROOT>` 指实际加载的所有 Skill 的父目录，须替换为真实绝对路径；脚本从赛题根目录运行，不在安装目录生成结果。Pro 的平台参数仅记录宿主能力，不改变 payload。详细见[安装与恢复说明](docs/agent-install-guide.md)。

Lite 保持一个入口、六步流程和基础 Word 报告，不加入 Pro 的多代理和检查点。

## 原理介绍

### 本轮证据加固

- 顶层 `computed` 不再掩盖子问题的失败、未知或冲突状态；未单独声明子问题状态的旧格式仍兼容。
- 本轮生成的 PNG/JPEG 等位图必须能解码；CSV/TSV 必须为 UTF-8、具有唯一非空表头和等宽数据行，XLSX 每个工作表都需有效。
- 最终报告绑定实际输入和输出哈希，而非只记录运行清单。原始附件不会因输出表格规则被重写或强制转换。
- 这仍是 Lite 的基础交付检查，不增加多代理、用户检查点或 PDF 验收。升级后重新运行最终检查，不沿用旧 PASS 报告。


本次输出隔离修复位于开发构建 [dist/](./dist/)，尚未创建新 Release；上面的旧 Release 不含此修复，版本不会被覆盖。

### 一条线性流程

```text
赛题与附件
→ 输入预检 → 最小计划 → 一个 model.py → 真实运行
→ 根据 results.json 写报告 → 最终检查与 Word 导出
```

三个用户命令分别是 `lite_preflight.py`、`lite_run.py` 和 `lite_finalize.py`。其他共享脚本服务于这些命令，不增加新的模型决策步骤或多 Skill 路由。

### 用脚本守住真实性底线

预检记录附件清单和 SHA-256，运行时绑定计划、代码、输入与输出。每次运行先将旧结果、图表、运行记录和 Word 归档到 `runs/<run_id>/previous/`，再从空图表目录计算。本轮证据必须绑定本轮输入或输出，不能把残留旧表格重新记为新结果；旧版运行记录需重跑。

输入、计划或代码变化后重新预检或运行。归档保留用于复核，清理前确认不再需要历史记录；一个项目同时只运行一个实验入口。

执行默认超时 300 秒，可根据算法显式调整；文件路径必须留在项目内。这些是运行与文件完整性保护，不是针对任意代码的安全沙箱。

### 基础报告不等于竞赛终稿

默认基础报告至少 1500 有效字符，每问独立标题下至少 150 字符，数值指标必须出现在对应问题的正文中。脚本还检查空答案、非有限指标、占位内容、重复正文和缺失证据。

图片必须对应运行记录，导出时真正嵌入 DOCX，之后重新打开核对。它不检查原生 Word OMML、严格正文引文或最终 PDF 排版。

只有用户明确要求时才声明短报告或测试范围，并说明理由。篇幅门槛用于拦截过短或不完整报告，不证明建模假设正确或论文优秀。

## 验证状态与详细文档

本轮通用包验证见[安装迁移验收记录](docs/universal-package-validation.md)，之前的门禁修复见[证据加固记录](docs/evidence-hardening-validation.md)。历史 CI 链接不代表本轮提交已在远端通过。

- 历史发布提交通过 15 项本地自动测试；[CI](https://github.com/yushui2022/MathModel-Skill/actions/runs/33940773858) 覆盖 Windows/Ubuntu、Python 3.11/3.12 与确定性安装包检查。
- [安装指南](docs/agent-install-guide.md) · [固定流程与范围说明](docs/lite-workflow.md) · [启动提示词](docs/lite-starter-prompt.md)
- 当前分支只维护 Lite，不包含 Standard 或 Pro 的工作流。分支 `dist/` 随提交更新，Release 保留固定发布快照。

开发者可在仓库中执行：

```bash
python scripts/check_skills.py
python -S tests/test_installation.py
python tests/test_installed_workflow.py
python tests/run_lite_tests.py
python tests/test_fresh_outputs.py
python scripts/build_release_packages.py --verify
```

[MIT License](LICENSE)，Copyright (c) 2026 yushui2022.
