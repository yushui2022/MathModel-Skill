---
name: MathModel Skill Standard
description: "数学建模全流程技能包：赛题与附件预检、题意与模型路线、数据与图表计划、真实运行建模代码、证据门禁、分章节正式写作与 Word/PDF 渲染检查，产出可复现的竞赛论文和全套证据。当用户要做完整篇数学建模竞赛论文时使用。"
license: MIT
compatibility: "Python 3.11-3.12 与 requirements.txt；最终 PDF 渲染检查需要 LibreOffice；优化求解可选 scipy/HiGHS。"
---

# MathModel Skill Standard

这是 MathModel Skill 标准档（Standard 2.4 开发版）的商店条目。包内是**十个协作技能加一个入口路由技能**，按 S0-S8 阶段用文件和 SHA-256 交接：先真实计算，再正式成文，最后过 Word/PDF 渲染检查。

它不是一个"一键生成论文"的提示词。Agent 必须运行真实代码、保存结果证据，并通过证据门禁后才允许进入正式写作。

## 包内结构

```text
SKILL.md                      本条目说明（商店展示用）
install.py                    安装器
requirements.txt              基础依赖
requirements-modeling.txt     优化求解可选依赖
VERSION
skills/
├── paper-workflow-orchestrator/              入口：S0-S8 路由
├── problem-doc-model-selector/               S1 题意分析
├── modeling-paper-rubric-and-model-selector/ S2 模型路线与评分对齐
├── data-cleaning-and-visualization/          S3 数据清洗与图表
├── model-code-and-result-generator/          S4/S5 建模代码与真实运行
├── quality-assurance-auditor/                S6 证据门禁
├── paper-formal-writer/                      S7/S8 正式写作与格式渲染检查
├── paper-micro-unit-generator/               单章局部修复（非正式草稿）
├── context-memory-keeper/                    中断续跑记忆
└── authoritative-data-harvester/             必要的公开外部数据
docs/                         安装、写作、契约、输出目录等说明
```

## 安装

方式一（推荐，支持托管升级）：解压到独立目录，准备好另一个赛题项目目录，然后执行

```text
python "<解压目录>/install.py" --project-root "<赛题目录>" --platform codex --check
python "<解压目录>/install.py" --project-root "<赛题目录>" --platform codex
```

`--platform` 取 `codex`（安装到 `.agents/skills/`）、`claude`（`.claude/skills/`）或 `trae`（`.trae/skills/`）。安装器只复制技能并记录哈希，不联网，不覆盖项目根配置、依赖文件、赛题或旧结果。

方式二（手动，不纳入托管升级）：把 `skills/` 下的十个目录**整体**复制到上面某一个位置，不能只复制 `SKILL.md`。

依赖在赛题项目的 Python 环境里单独安装：

```text
python -m pip install -r "<解压目录>/requirements.txt"
python -m pip check
```

## 使用

1. 在赛题项目根目录建立 `problem_files/`，放入赛题、官方附件与数据。
2. 对 Agent 说：

```text
请使用 paper-workflow-orchestrator 完成这个数学建模项目。
赛题和官方附件已放在 problem_files/。
先预检输入，再按 S0-S8 执行，必须真实运行代码并保留结果证据。
采用完整章节写作，允许分多轮完成，最后统一全文，不要只输出摘要或拼接微单元。
请核对当年赛题的篇幅和格式规则，不自行降低为短报告。
所有赛题产物写入 paper_output/；证据、写作与 Word/PDF 检查未通过，不要称为最终稿。
```

主要产物：`paper_output/final_paper.docx`、`final_paper_source.md`、`qa/rendered/final_paper.pdf`，以及 `code/`、`results/`、`figures/`、`format_check_report.json`。

## 边界（请先读）

- 需要 Python 3.11 或 3.12。最终 PDF 渲染检查需要 LibreOffice；缺少它可以先做前期工作，但不能称为最终稿。
- 检查通过代表证据、写作与格式门禁通过，**不代表论文优秀或竞赛获奖**。
- 一个赛题项目只安装一个 MathModel 版本，不要混装 Lite、Flash、Standard、Pro。
- 默认篇幅门槛（完整稿至少 14000 有效字符、渲染页至少 18 页）是防止极短稿的项目默认值，不是所有比赛的统一规定，页数上限仍需按当年赛题核对。
- 图表、数值结论和最优性表述都必须能追溯到本次运行的机器可读证据；手工改指标或结论会使证据门禁失败。
