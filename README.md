<div align="center">
  <img src="./assets/mathe-skill-logo.svg" alt="MathModel Skill" width="120" height="120" />

# MathModel Skill Standard

### 强模型使用的可复现数学建模与正式论文工作流

[![Version](https://img.shields.io/badge/version-2.2.0-0f766e)](./VERSION)
[![Workflow](https://img.shields.io/badge/workflow-S0--S8-2563eb)](#standard-22-主线)
[![Platforms](https://img.shields.io/badge/platforms-Codex%20%7C%20Claude%20Code%20%7C%20Trae-111827)](#安装)
[![License](https://img.shields.io/badge/license-MIT-16a34a)](./LICENSE)

</div>

这是 MathModel Skill 的默认 `master` 分支。Standard 适合上下文较长、复杂推理与工具调用稳定的强模型，用于完成正式竞赛论文，同时控制流程复杂度与计算成本。

Standard 2.2 保留 S0-S6 可复现证据链与 S8 Word/PDF 门禁，重点重建 S7 写作：完整章节是默认写作单位，微单元只在单章连续失败后进行局部修复。所有章节通过后，必须先确定性合并，再由 Agent 做一次全文统一改写，不能把章节或微单元简单拼接后直接交付。

## 版本选择

| 模型与目标 | 推荐版本 | 分支 |
|---|---|---|
| Claude Fable 5、GPT-5.6 Sol Ultra 等最高档模型，允许高成本、多路线与独立复算 | Pro | [`pro`](https://github.com/yushui2022/MathModel-Skill/tree/pro) |
| 强模型、长上下文、稳定工具调用、正式竞赛论文 | **Standard 2.2（当前分支）** | [`master`](https://github.com/yushui2022/MathModel-Skill/tree/master) |
| 普通或较旧模型、短上下文、优先简单稳定 | Lite | [`lite`](https://github.com/yushui2022/MathModel-Skill/tree/lite) |

**一个比赛项目只安装一个版本。** 不要把 Standard、Lite、Pro 解压到同一目录。三版 preflight 都会扫描现代与历史 Skill 路径并阻止混装。

## Standard 2.2 主线

```text
S0 输入与安装预检
-> S1 题意结构化
-> S2 模型与评分路线
-> S3 数据和图表计划
-> S4 赛题专用代码
-> S5 真实运行与结果契约
-> S6 证据门禁
-> S7 自适应正式写作
-> S8 Word/PDF 格式门禁
```

S7 只有一条正式主线：

```text
证据门禁 PASS
-> writing_plan.json
-> 完整章节草稿
-> 逐章审计
-> 必要时局部微单元修复
-> assembled_draft.md
-> Agent 全文统一改写
-> final_paper_source.md 审计
-> final_paper.docx
-> LibreOffice PDF 渲染门禁
```

### 自适应模式

| 模式 | 使用条件 | 行为 |
|---|---|---|
| `section` | 正常竞赛论文，默认 | 按完整章节写作、审计、修复和合并 |
| `global` | 正文目标不超过 6000 有效字符，或用户明确要求短报告 | 先写完整短稿；同类失败连续两次后降为 `section` |
| `micro-repair` | 单个章节同类失败连续两次 | 只修复 `repair_queue.json` 指定位置，不接管全文 |
| `legacy` | 安装测试、旧模型紧急兜底 | 输出非正式 scaffold，不得使用正式文件名 |

单章同类问题第三次仍失败时，S7 标记 `BLOCKED` 并说明原因。系统可以建议用户改用 Lite，但不会自动切换分支或版本。

## 安装

从 GitHub Release 下载与你的平台对应的一个 ZIP，并解压到数学建模项目根目录：

| 平台 | 安装包 | 解压后的 Skill 目录 |
|---|---|---|
| Codex | `MathModel-Skill-Codex.zip` | `.agents/skills/` |
| Claude Code | `MathModel-Skill-Claude-Code.zip` | `.claude/skills/` |
| Trae | `MathModel-Skill-Trae.zip` | `.trae/skills/` |

安装包不会创建或覆盖项目根目录的 `AGENTS.md`、`CLAUDE.md`。每个 ZIP 都包含 `VERSION`、`MATHMODEL_BUILD.json`、逐文件 SHA-256、平台 README、依赖与启动提示词。

安装依赖：

```bash
python -m pip install -r requirements.txt
python -m pip check
```

正式 S8 需要 LibreOffice，用于把 DOCX 渲染为 PDF 并检查页数和可提取文本。没有 LibreOffice 时可以开发和生成草稿，但不能通过最终 `--render required` 门禁。

创建输入目录：

```text
your-project/
├── problem_files/       # 赛题、官方附件、数据
├── requirements.txt
└── <平台 Skill 目录>/
```

## 首次提示词

安装后直接对 Agent 说：

```text
请使用 $paper-workflow-orchestrator 完成这个数学建模项目。
赛题和官方附件已放在 problem_files/。
先运行 preflight 和 workflow_guard --status，再严格按 S0-S8 继续。
所有赛题专用代码写入 paper_output/code/，所有结果、证据和论文写入 paper_output/。
S6 证据门禁通过后，按 Standard 2.2 的章节写作主线执行 S7；只有修复队列明确要求时才使用微单元。
全部章节通过后先确定性合并，再进行一次全文统一改写，然后生成正式 DOCX 并执行 required PDF 渲染门禁。
任何门禁失败都不要把产物称为最终稿。
```

更多可复制提示词见 [docs/starter-prompts.md](docs/starter-prompts.md)。

## 常用命令

以下以 Claude Code 路径为例。Codex 将 `.claude/skills` 替换为 `.agents/skills`，Trae 替换为 `.trae/skills`。

检查或恢复阶段：

```bash
python .claude/skills/paper-workflow-orchestrator/scripts/preflight_check.py
python .claude/skills/paper-workflow-orchestrator/scripts/workflow_guard.py --status
```

证据门禁：

```bash
python .claude/skills/quality-assurance-auditor/scripts/evidence_gate.py --mode official
```

S7 正式写作：

```bash
python .claude/skills/paper-formal-writer/scripts/build_paper_outline.py
python .claude/skills/paper-formal-writer/scripts/prepare_authoring.py --mode auto
python .claude/skills/paper-formal-writer/scripts/validate_authoring.py --section <section-id>
python .claude/skills/paper-formal-writer/scripts/assemble_sections.py
python .claude/skills/paper-formal-writer/scripts/validate_authoring.py --assembled
python .claude/skills/paper-formal-writer/scripts/validate_authoring.py --final
```

Word 与 S8：

```bash
python .claude/skills/paper-formal-writer/scripts/format_formal_docx.py
python .claude/skills/paper-formal-writer/scripts/check_paper_format.py --render required
```

`quickstart_run.py` 只验证安装和基础脚本。它的全部草稿都写入 `paper_output/quickstart/`，不会产生正式命名文件。

## 关键契约

```text
paper_output/
├── preflight_report.json
├── input_manifest.json
├── step1/problem_analysis.json
├── plan/
│   ├── model_route.json
│   ├── rubric_alignment.json
│   ├── paper_outline.json
│   └── writing_plan.json
├── code/                         # 当前赛题专用代码
├── results/
│   ├── run_manifest.json
│   ├── model_results.json
│   ├── metrics.json
│   └── conclusions.json
├── qa/
│   ├── evidence_gate_report.json
│   ├── draft_audit.json
│   └── repair_queue.json
├── context/
│   ├── authoring_state.json
│   └── workflow_memory.json
├── drafts/
│   ├── sections/
│   ├── repairs/
│   ├── legacy/
│   └── assembled_draft.md
├── final_paper_source.md
├── final_paper.docx
└── format_check_report.json
```

所有机器契约都使用输入 SHA-256 判断新鲜度。证据、计划、已审计章节、合并稿或最终源稿发生变化后，下游 PASS 自动失效。

## 10 个 Skills

| Skill | 职责 |
|---|---|
| `paper-workflow-orchestrator` | S0-S8 总入口、路由、恢复 |
| `problem-doc-model-selector` | 题面、附件、子问题和约束结构化 |
| `modeling-paper-rubric-and-model-selector` | 模型路线与评分证据 |
| `authoritative-data-harvester` | 必要的公开权威数据 |
| `data-cleaning-and-visualization` | 数据读取、清洗、图表计划与索引 |
| `model-code-and-result-generator` | 赛题专用代码、运行账本与结果契约 |
| `quality-assurance-auditor` | S6 证据门禁 |
| `paper-formal-writer` | 唯一正式主笔、S7/S8 |
| `paper-micro-unit-generator` | 排队后的局部修复；legacy/quickstart scaffold |
| `context-memory-keeper` | 长任务断点与恢复状态 |

## 验证与打包

本地回归：

```bash
python -m compileall -q packages scripts tests
python scripts/sync_platform_packages.py --check
python -u tests/run_tests.py
python scripts/build_release_packages.py --verify
```

CI 覆盖 Windows/Ubuntu、Python 3.11/3.12，并在 Ubuntu 3.11 安装 LibreOffice 执行强制渲染测试。打包器固定 ZIP 时间戳、文本 LF 与文件顺序；`dist/SHA256SUMS.txt` 用于发布资产校验。

## 示例说明

`examples/cumcm2024-b-demo/` 保留原有 B 题工程产物，未在本次升级中重生成。它可用于查看历史 Word、证据和代码组织方式，但不代表已经通过 Standard 2.2 新增的 `writing_plan.json`、`authoring_state.json` 与章节哈希门禁。新赛题应完整执行当前 S0-S8。

## 分支边界

- `master`：Standard 2.2，默认分支。
- `lite`：独立 Lite 产品，不与 Standard 同装或合并工作流。
- `pro`：独立高成本 Pro 产品，不与 Standard 同装或合并工作流。
- `Latex`：可选 LaTeX 输出实验分支，不改变主分支 Word 默认交付。

## License

[MIT](LICENSE), Copyright (c) 2026 yushui2022.
