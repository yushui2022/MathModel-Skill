<div align="center">
  <img src="./assets/mathmodel-banner.png" alt="MathModel Skill：豆包坐镇指挥，Fable 推导模型，Astra 编写代码" width="100%" />

# MathModel Skill Flash

### 用高吞吐模型快速生成带真实实验的基础长篇数学建模论文

[![Version](https://img.shields.io/badge/version-2.0.0--flash.2-D97706)](./VERSION)
[![Platforms](https://img.shields.io/badge/platforms-Codex%20%7C%20Claude%20Code%20%7C%20Trae-111827)](#快速导入使用)
[![License](https://img.shields.io/badge/license-MIT-16a34a)](./LICENSE)

</div>

MathModel Skill 是面向数学建模竞赛的 Agent 工作流。它从赛题和附件出发，读取数据、运行建模代码、保存真实结果和图表，再生成可编辑的论文文档。**Flash 是独立的速度优先版本**：适合 DeepSeek、Gemini、GLM 等 Flash 类高吞吐模型，目标是在较短时间内完成一份有实验内容、结果数值和 Word 导出的基础长文草稿。

Flash 不承诺 Standard 的完整证据链、原生 Word 公式和 PDF 排版验收，也不承诺 Pro 的多路线竞赛、独立复算和五角色审稿。它适合作为快速起稿和方案探索版本；正式提交前应使用 Standard 或 Pro 复核。

## 版本选择

本项目每个版本在独立 Git 分支维护，**不是安装后的切换模式**。质量和速度不是单一的高低排序：Lite 优先降低模型负担，Flash 优先降低等待时间，Standard 优先正式交付，Pro 优先验证深度。

| 定位 | 版本与分支 | 适合谁 | 主要交付 |
|---|---|---|---|
| 速度优先 | [**Flash**](https://github.com/yushui2022/MathModel-Skill/tree/flash) | DeepSeek/Gemini/GLM 等 Flash 类高吞吐模型 | 真实实验、图表、结果和约 18–22 页目标的基础 Word 长文；不做严格终稿门禁 |
| 低负担 | [**Lite**](https://github.com/yushui2022/MathModel-Skill/tree/lite) | DeepSeek 等普通、较旧或短上下文模型 | 固定六步基础报告；篇幅和验证较轻 |
| 正式标准 | [**Standard**](https://github.com/yushui2022/MathModel-Skill/tree/standard) | [GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol)、[Claude Opus 5.5](https://platform.claude.com/docs/en/models/opus-5-5/overview) 等；旧款强模型仍可用 | 完整章节写作、证据检查、原生 Word 公式和 PDF 渲染检查 |
| 高强度旗舰 | [**Pro**](https://github.com/yushui2022/MathModel-Skill/tree/pro) | GPT-6 Astra、[Claude Fable 5.1](https://platform.claude.com/docs/en/models/fable-5-1/overview)、Opus 5.5、GPT-6.1 Sol 等前沿模型 | 多路线比较、独立复算、稳健性实验、五角色审稿和 Word/PDF 检查；预发布 |
| TeX 实验 | [**LaTeX**](https://github.com/yushui2022/MathModel-Skill/tree/Latex) | 需要旧版 TeX/PDF 流程的用户 | 独立实验性分支，不等同于 Standard 或 Pro 的当前能力 |

各版本 README 都保留这张版本表，便于从任意分支回到其他版本。**一个项目只安装一个版本、一个安装位置，不要混装。**

模型推荐更新于 **2026-10-07**：已核对 Opus 5.5、Fable 5.1、GPT-6.1 Sol 的官方配置资料，尚未完成这些模型的完整赛题长文实测。**档位区分的是工作流，不是模型使用权限**：同一个模型可选 Standard 控制投入，也可选 Pro 加深验证；GPT-5.5、GPT-5.6 Sol 等旧款强模型仍可使用 Standard。

这不是对同品牌所有模型的固定排名，也不是质量认证。模型名称、API 档位与宿主实际能力须分开核对；中转站的显示名不能证明底层型号。

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

当前分支版本为 **2.0.0-flash.4**。下载 [MathModel-Skill-Flash.zip](https://github.com/yushui2022/MathModel-Skill/raw/refs/heads/flash/dist/MathModel-Skill-Flash.zip) 和 [SHA256SUMS.txt](dist/SHA256SUMS.txt)。这是分支构建，不是新建的正式 Release；历史 Release 平台包不作改动。

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

把题面和原始附件放到赛题目录的 `problem_files/`，用宿主打开该赛题目录并刷新 Skill 列表。让 Agent 读取实际安装位置中的 **mathmodel-flash/SKILL.md**，按[启动提示词](docs/flash-starter-prompt.md)开始。

`<SKILL_ROOT>` 指实际加载的所有 Skill 的父目录，须替换为真实绝对路径；脚本从赛题根目录运行，不在安装目录生成结果。Pro 的平台参数仅记录宿主能力，不改变 payload。详细见[安装与恢复说明](docs/agent-install-guide.md)。

Flash 保持速度优先的基础长文流程。真实实验和基础 Word 导出检查保留，不承诺严格终稿质量。

## 原理介绍

### 本轮证据加固

- 顶层 `computed` 不再掩盖子问题的失败、未知或冲突状态；未单独声明子问题状态的旧格式仍兼容。
- 本轮生成的 PNG/JPEG 等位图必须能解码；CSV/TSV 必须为 UTF-8、具有唯一非空表头和等宽数据行，XLSX 每个工作表都需有效。
- 最终报告绑定实际输入和输出哈希，而非只记录运行清单。原始附件不会因输出表格规则被重写或强制转换。
- 这仍是 Flash 的基础交付检查，不增加多代理、用户检查点或 PDF 验收。升级后重新运行最终检查，不沿用旧 PASS 报告。


当前为 2.0.0-flash.4 开发版，新增实验输出隔离。本分支 [dist/](./dist/) 包含修复；尚未创建新 Release，上面的旧 Release 不含此修复。

```text
赛题与附件
→ 输入哈希预检
→ 单路线快速计划
→ 一个 model.py 真实运行
→ 保存 results / CSV / PNG
→ 生成有实验内容的长文
→ 基础一致性检查与 Word 导出
```

Flash 用少量固定脚本守住最低真实性底线：预检记录输入，运行器绑定计划、脚本和结果，终检检查每个问题、关键数值、图表和 DOCX 重开内容。它刻意不加入 Pro 的高成本研究闭环，以保持 Flash 模型的速度优势。

每次计算前将旧结果、图表、运行记录和 Word 归档到 `runs/<run_id>/previous/`，再创建空输出目录。证据只接受本轮清单绑定的输入或输出，旧版运行记录需重跑；不增加模型检查点。归档可能增长，清理前确认不再需要历史记录，一个项目同时只运行一个实验入口。

### 论文长度说明

默认目标是约 18–22 页，至少 9000 个有效字符，并按问题展开方法、算法、实验、结果、检验、敏感性和局限。脚本会给出粗略页数估计；不足目标只告警，不能靠复制正文通过。Word 页数会受到字体、页边距、表格和图片影响，因此 Flash 不把估算页数描述成排版保证。

### 明确限制

Flash PASS 不是数学正确性证明，也不是正式竞赛验收。没有严格引用审计、原生 OMML 公式、PDF 渲染门禁、独立双路径复算和多角色审稿时，应在提交前转入 [Standard](https://github.com/yushui2022/MathModel-Skill/tree/standard) 或 [Pro](https://github.com/yushui2022/MathModel-Skill/tree/pro)。

## 开发验证

本轮通用包验证见[安装迁移验收记录](docs/universal-package-validation.md)，之前的门禁修复见[证据加固记录](docs/evidence-hardening-validation.md)。历史 CI 链接不代表本轮提交已在远端通过。

```bash
python scripts/check_skills.py
python -S tests/test_installation.py
python tests/test_installed_workflow.py
python tests/run_flash_tests.py
python tests/test_fresh_outputs.py
python scripts/build_release_packages.py --verify
```

Flash 当前只维护 `mathmodel-flash` 一个入口，全部宿主共用根目录 skills/ 的唯一源码；分支内不包含 Standard、Lite 或 Pro 的工作流。
