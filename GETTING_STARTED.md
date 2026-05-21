# 5 分钟开始使用 MathModel Skill

这份文档只讲第一次怎么用，不讲项目原理。想看完整设计，请读 `README.md`；想看正式生成效果，请打开 `examples/cumcm2024-b-demo/paper_output/final_paper.docx`。

## 你需要准备什么

- 一个 Agent：Codex、Claude Code 或 Trae。
- 一个数学建模比赛项目目录。
- 官方赛题 PDF/Word 和附件数据。
- Python 环境。

## 1. 选择你的平台包

从 `dist/` 下载或复制对应 zip：

```text
Codex       -> dist/MathModel-Skill-Codex.zip
Claude Code -> dist/MathModel-Skill-Claude-Code.zip
Trae        -> dist/MathModel-Skill-Trae.zip
```

## 2. 解压到比赛项目根目录

解压后，项目目录应类似下面这样。

Codex：

```text
your-project/
├── skills/
├── AGENTS.md
├── requirements.txt
└── problem_files/
```

Claude Code：

```text
your-project/
├── .claude/
├── CLAUDE.md
├── requirements.txt
└── problem_files/
```

Trae：

```text
your-project/
├── .trae/
├── requirements.txt
└── problem_files/
```

如果 `problem_files/` 不存在，手动创建。

## 3. 放入赛题和附件

把官方赛题和附件放进 `problem_files/`：

```text
problem_files/
├── 赛题.pdf
├── 附件1.xlsx
├── 附件2.csv
└── 其他官方材料
```

不要把生成结果、临时代码或旧论文放进 `problem_files/`。当前赛题生成物会统一写入 `paper_output/`。

## 4. 安装依赖

在你的比赛项目根目录运行：

```bash
pip install -r requirements.txt
```

Windows PowerShell 如果出现中文编码问题，先运行：

```powershell
$env:PYTHONIOENCODING="utf-8"
```

## 5. 复制这段话给 Agent

```text
我已经把赛题和附件放进 problem_files/。
请使用 MathModel Skill，从 paper-workflow-orchestrator 开始，不要先跑 quickstart。

请按正式比赛流程完成：
读题 -> 拆题 -> 模型路线 -> 附件性质判断 -> 生成并运行赛题专用代码 -> 产出真实结果、图表、表格、指标和结论 -> 证据门禁 -> paper-formal-writer 正式成稿 -> Word 排版 -> 格式门禁。

所有当前赛题代码写入 paper_output/code/。
所有结果、图表、表格、报告和论文产物写入 paper_output/。
证据门禁或格式门禁未通过时，不要把 Word 称为最终稿。
```

## 6. 看结果

完成后优先打开：

```text
paper_output/final_paper.docx
paper_output/final_paper_source.md
paper_output/qa/evidence_gate_report.md
paper_output/format_check_report.md
```

只有同时满足下面三点时，当前 Word 才能称为正式稿：

```text
paper_output/final_paper.docx 存在
paper_output/qa/evidence_gate_report.md 显示 PASS
paper_output/format_check_report.md 显示 PASS
```

## 失败了先看哪里

没有生成 Word：

```text
paper_output/qa/evidence_gate_report.md
```

通常说明某些子问题缺少真实结果、指标、图表、表格或结论回扣。

Word 生成了但不能称为最终稿：

```text
paper_output/format_check_report.md
```

通常说明字数不足、标题层级缺失、图表未引用、参考文献或附录不足。

代码没有跑通：

```text
paper_output/code/
```

让 Agent 修复这里的当前赛题专用代码，不要把当前赛题代码写回 `skills/`、`.claude/skills/` 或 `.trae/skills/`。

## 看正式样例

仓库已经提交 CUMCM 2024 B 题正式生成样例：

```text
examples/cumcm2024-b-demo/
```

重点看：

```text
examples/cumcm2024-b-demo/paper_output/final_paper.docx
examples/cumcm2024-b-demo/paper_output/final_paper_source.md
examples/cumcm2024-b-demo/paper_output/qa/evidence_gate_report.md
examples/cumcm2024-b-demo/paper_output/format_check_report.md
```

该样例不包含官方 `B题.pdf`。用户复现时需要自行准备官方赛题文件。
