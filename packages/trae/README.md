# MathModel Skill Standard 2.3.0 · Trae

这是 MathModel 的 **Trae 独立 Skill 包**，采用 Standard 2.3.0 的 S0–S8 工作流：从赛题分析、模型选择和真实计算，推进到有结果证据支持的论文写作、Word 排版与 PDF 渲染检查。

当前仓库还在开发 Codex Plugin `0.5.0-alpha.1`。本目录保留的是历史 Standard 版本，入口、依赖和产物目录均按 Standard 使用。

[项目主页](../../README.md) · [当前 Codex 插件说明](../../plugins/mathmodel/README.md) · [Standard 2.3.0 Release](https://github.com/yushui2022/MathModel-Skill/releases/tag/v2.3.0)

## 安装完整包

优先下载固定版本的 [MathModel-Skill-Trae.zip](https://github.com/yushui2022/MathModel-Skill/releases/download/v2.3.0/MathModel-Skill-Trae.zip)，可用同次发布的 [SHA256SUMS.txt](https://github.com/yushui2022/MathModel-Skill/releases/download/v2.3.0/SHA256SUMS.txt) 核对文件。这个完整包包含 Skill 正文、脚本、参考资料、依赖清单和版本记录；只复制 `SKILL.md` 无法安装完整工作流。

在独立比赛项目的根目录解压，目录结构应为：

```text
你的比赛项目/
├─ .trae/skills/
├─ requirements.txt
├─ docs/
├─ VERSION
├─ MATHMODEL_BUILD.json
├─ LICENSE
└─ problem_files/          # 自行放入题面和官方附件
```

该发布包不创建或覆盖项目级指令文件。每个比赛项目只安装一套 MathModel；已有其他版本或其他平台入口时，先检查并处理重复安装。

使用解压包内的 `requirements.txt` 安装依赖，建议在项目自己的 Python 虚拟环境中执行：

```bash
python -m pip install -r requirements.txt
python -m pip check
```

正式交付的 PDF 渲染检查还需要安装 LibreOffice。将赛题文档与官方附件放入 `problem_files/` 后，在 Trae 中打开这个比赛项目。

**不要把当前插件分支根目录的依赖或 Pro 源码当作 Standard 安装材料。** GitHub 的仓库源码 ZIP 也不等同于上述平台发布包。需要研究 Standard 源码时，请使用 [Standard 分支](https://github.com/yushui2022/MathModel-Skill/tree/standard) 或固定的 `v2.3.0` 历史版本，并遵循对应版本的说明。

## 开始与继续建模

在 Trae 对话中说明使用 `paper-workflow-orchestrator`：

> 请使用 paper-workflow-orchestrator 完成这个数学建模项目。题面和官方附件在 problem_files/。先执行预检并读取工作流状态，按 Standard 的 S0–S8 推进，将本题代码与产物保存在 paper_output/。真实结果通过证据检查后，再使用 paper-formal-writer 撰写、全篇修订并生成正式 Word，完成所需的 PDF 渲染检查。

预检和状态查询也可在比赛项目根目录手动运行：

```bash
python .trae/skills/paper-workflow-orchestrator/scripts/preflight_check.py
python .trae/skills/paper-workflow-orchestrator/scripts/workflow_guard.py --status
```

继续已有项目时，让 Agent 先读当前状态报告，再从首个未通过的阶段继续。修改了数据、代码或结果后，应重新检查受影响的证据与论文；以当前文件及其哈希为准。

## Standard 的工作流程

| 阶段 | 主要工作 |
|---|---|
| S0 | 检查输入、依赖、版本与项目布局 |
| S1 | 分析题意、各小问、附件及约束 |
| S2 | 确定模型路线与论文要求 |
| S3 | 清洗数据，规划和生成图表 |
| S4 | 编写当前赛题的可复现建模代码 |
| S5 | 真实执行并记录结果、指标和运行证据 |
| S6 | 核验当前结果证据，决定是否可以正式写作 |
| S7 | 使用 `paper-formal-writer` 撰写完整章节、审查并全篇修订 |
| S8 | 检查 Word 格式、公式与 PDF 渲染结果 |

正式写作应在 S6 通过后进行。`paper-micro-unit-generator` 只在修复队列要求时处理局部问题，或用于明确请求的历史脚手架。Quickstart 是安装冒烟测试，输出保存在 `paper_output/quickstart/`，不能替代正式 S7/S8 验收。

## 产物在哪里

赛题专用代码与产物集中保存在 `paper_output/`，通用 Skill 保留在 `.trae/skills/`：

| 路径 | 内容 |
|---|---|
| `paper_output/input_manifest.json` | 输入清单与哈希 |
| `paper_output/step1/`、`paper_output/plan/` | 题意分析、模型路线和写作计划 |
| `paper_output/code/` | 当前赛题的数据处理与建模代码 |
| `paper_output/results/` | 结构化结果、指标与运行清单 |
| `paper_output/qa/` | 工作流、证据和草稿检查报告 |
| `paper_output/drafts/` | 章节草稿及汇编稿 |
| `paper_output/final_paper_source.md` | 全篇修订后的正式稿源 |
| `paper_output/final_paper.docx` | 正式 Word 文档，公式按要求生成可编辑格式 |
| `paper_output/qa/rendered/final_paper.pdf` | 格式检查阶段生成的 PDF |
| `paper_output/format_check_report.json` | 最终格式和渲染检查结果 |

## 与当前 Codex 插件的区别

| 项目 | 本 Trae Skill 包 | 当前 Codex Plugin |
|---|---|---|
| 版本与核心 | Standard 2.3.0 | 插件 0.5 Alpha，基于 Pro 核心 |
| 安装方式 | 比赛目录内的 `.trae/skills/` 完整包 | Codex 插件安装与运行环境配置 |
| 工作流 | S0–S8 | P0–P9 |
| 主要产物目录 | `paper_output/` | `paper_output_pro/` |
| 运行接口 | Skill 与随包脚本 | Skill、MCP 工具与项目运行服务 |

Pro 原有的多角色审题、多路线比较和批准检查点，与插件新增的按小问恢复、作业管理、有限范围 LP/MILP 数学检查、修改影响分析和独立重放能力，不属于本 Trae Standard 包。插件还提供可选的本地证据页面；安装本包不会获得这些功能，也不会自动迁移为 Pro 项目。当前 Alpha 的工程验证不代表已证明真实比赛论文质量提升。

使用 Trae Standard 时以固定发布包内文档为准；了解当前 Codex 插件，请阅读[插件说明](../../plugins/mathmodel/README.md)。其他版本与平台入口见[项目主页](../../README.md)。
