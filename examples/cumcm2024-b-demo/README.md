# CUMCM 2024 B 题正式论文生成样例

本目录是 MathModel Skill 按 Agent-native 正式流程生成的 CUMCM 2024 B 题展示样例，用来说明“从证据链到正式 Word”的完整交付形态。

仓库不包含官方 `B题.pdf`。如果要复现完整流程，请自行从官方渠道准备赛题文件，并放入自己的 `problem_files/` 目录。本样例提交的是生成产物、赛题专用代码、图表、表格、证据契约、格式检查报告和 Word 成稿。

## 你应该先看什么

| 文件 | 用途 |
|---|---|
| `paper_output/final_paper.docx` | 已提交的正式 Word 样例，重点看排版、标题层级、图表插入和正文组织方式。 |
| `paper_output/final_paper_source.md` | Agent 基于完整证据链写出的正式 Markdown 源稿。 |
| `paper_output/format_check_report.md` | 正式格式门禁报告，记录字数、标题、图表、表格和 Word 结构检查结果。 |
| `paper_output/qa/evidence_gate_report.md` | 证据门禁报告，确认每个子问题是否有结果、指标、图表、表格和结论回扣。 |
| `paper_output/plan/paper_outline.json` | 正式论文大纲契约，约束 `1 / 1.1 / 1.1.1` 标题、章节目标字数和证据引用。 |
| `paper_output/figures/figure_contact_sheet.png` | 图表总览，便于快速检查正文图片风格是否统一。 |
| `paper_output/code/modeling/` | 当前 B 题专用建模、写作增强和 Word 生成辅助代码。 |

当前样例的格式门禁结果为 `PASS`：正文有效字符数 `18007`，图索引 `5` 张，表索引 `8` 张，Word 中包含 `287` 个段落、`23` 个表格、`5` 张图片和 `60` 个标题段落。

证据门禁结果为 `PASS`：Q1 到 Q4 都具备模型结果、指标、结论、图证据和表证据。

## 生成流程

本样例不是由旧的一键正文脚本拼接出来的，而是按以下流程生成：

```text
题意解析
-> 模型路线
-> 赛题专用代码建模
-> 结果 / 指标 / 结论契约
-> 图表和表格证据
-> evidence_gate.py 证据门禁
-> build_paper_outline.py 正式大纲
-> Agent 全局写作 final_paper_source.md
-> format_formal_docx.py 生成 Word
-> check_paper_format.py 格式门禁
-> final_paper.docx
```

对应产物都沉淀在 `paper_output/` 中：

```text
paper_output/
├── final_paper_source.md          # 正式论文 Markdown 源稿
├── final_paper.docx               # 由 paper-formal-writer 生成的正式 Word
├── format_check_report.md         # 正式格式门禁报告
├── format_check_report.json       # 机器可读格式门禁结果
├── qa/evidence_gate_report.md     # 证据门禁报告
├── qa/evidence_gate_report.json   # 机器可读证据门禁结果
├── plan/paper_outline.json        # 正式论文大纲契约
├── results/                       # 模型结果、指标和结论
├── tables/                        # 论文表格和 table_index.json
├── figures/                       # 论文图片和图表总览
├── step1/                         # 题意解析、论文大纲、评分点和模型路线初稿
└── code/                          # 当前赛题专用代码
```

## 如何复核这个样例

从仓库根目录执行以下 PowerShell 命令：

```powershell
$env:PYTHONIOENCODING="utf-8"
Push-Location examples\cumcm2024-b-demo
python ..\..\packages\codex\skills\quality-assurance-auditor\scripts\evidence_gate.py
python ..\..\packages\codex\skills\paper-formal-writer\scripts\build_paper_outline.py
python ..\..\packages\codex\skills\paper-formal-writer\scripts\format_formal_docx.py
python ..\..\packages\codex\skills\paper-formal-writer\scripts\check_paper_format.py
Pop-Location
```

如果你使用 Trae 或 Claude Code，把脚本前缀替换为对应平台路径：

```text
Trae        -> ..\..\packages\trae\.trae\skills\
Claude Code -> ..\..\packages\claude\.claude\skills\
Codex       -> ..\..\packages\codex\skills\
```

复核后重点查看：

- `paper_output/qa/evidence_gate_report.md` 是否仍为 `PASS`。
- `paper_output/format_check_report.md` 是否仍为 `PASS`。
- `paper_output/final_paper.docx` 是否存在，且图片、表格、标题层级完整。

## 如何用它指导新赛题

这个目录是样例，不是新题模板答案。新赛题应按下面方式使用：

1. 新建你的比赛项目目录。
2. 按平台复制 skill 包：Codex 复制 `packages/codex/skills/`，Claude Code 复制 `packages/claude/.claude/skills/`，Trae 复制 `packages/trae/.trae/skills/`。
3. 在新项目中创建 `problem_files/`，放入官方赛题 PDF/Word 和附件数据。
4. 对 Agent 说：

```text
请使用 MathModel Skill，从 paper-workflow-orchestrator 开始。不要先跑 quickstart 脚本。请读取赛题和附件，生成模型路线，判断附件是原始数据还是结果模板，在 paper_output/code/ 中生成并运行当前赛题专用代码，产出真实图表、表格、指标和结论。证据门禁通过后，再调用 paper-formal-writer 生成正式 outline，基于完整证据链全局撰写 final_paper_source.md，并生成 final_paper.docx。证据门禁和格式门禁未同时通过时，不要把 Word 称为最终稿。
```

5. 新题生成后，对照本样例检查 `paper_output/` 是否具备同类交付物：证据报告、正式大纲、Markdown 源稿、Word、图表、表格、结果契约和赛题专用代码。

不要把本样例的 B 题正文、参数或结果复制成其他赛题答案。它的价值在于展示流程、文件结构、正式论文范式和 Word 交付质量。

## 与 quickstart 的区别

`examples/quickstart/` 只验证安装和链路能否跑通，产物是验证草稿。

本目录展示正式论文交付：证据门禁先确认每问有真实结果和图表表格，`paper-formal-writer` 再约束正式大纲、长文写作、Word 排版和格式检查。用户评估论文效果时，应以本目录的 `final_paper.docx` 和 `format_check_report.md` 为参考。
