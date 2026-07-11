# 正式论文生成流程与结果样例

本页说明仓库中的正式论文样例模块如何使用，以及它展示了 MathModel Skill 从赛题证据链到 Word 成稿的完整交付方式。

样例位置：

```text
examples/cumcm2024-b-demo/
```

核心 Word 成果：

```text
examples/cumcm2024-b-demo/paper_output/final_paper.docx
```

仓库不提交官方 `B题.pdf`。样例目录只提交生成产物、赛题专用代码、图表、表格、证据契约、格式报告和使用说明。

## 这个样例证明什么

这个样例用于证明正式 workflow 已经不只是“生成一篇 Markdown”，而是能形成完整比赛论文交付包：

| 能力 | 对应产物 |
|---|---|
| 题意结构化与模型路线 | `paper_output/step1/`、`paper_output/plan/model_route.json` |
| 赛题专用建模代码 | `paper_output/code/modeling/` |
| 模型结果、指标和结论 | `paper_output/results/model_results.json`、`metrics.json`、`conclusions.json` |
| 表格证据 | `paper_output/tables/`、`paper_output/tables/table_index.json` |
| 图证据 | `paper_output/figures/`、`paper_output/figure_index.json` |
| 证据门禁 | `paper_output/qa/evidence_gate_report.md` |
| 正式论文大纲 | `paper_output/plan/paper_outline.json` |
| 正式 Markdown 源稿 | `paper_output/final_paper_source.md` |
| 正式 Word | `paper_output/final_paper.docx` |
| 格式门禁 | `paper_output/format_check_report.md` |

当前 B 题样例的格式门禁为 `PASS`，有效字符数 `18007`，图索引 `5` 张，表索引 `8` 张；Word 中包含标题层级、正文段落、表格和图片。

## 生成链路

正式样例的生成链路如下：

```text
读题
-> 拆题
-> 模型路线
-> 判断附件性质
-> 生成/修改赛题专用代码
-> 运行代码
-> 真实图表、表格、指标、结论
-> evidence_gate.py
-> build_paper_outline.py
-> Agent 基于证据链全局写 final_paper_source.md
-> format_formal_docx.py
-> check_paper_format.py
-> final_paper.docx
```

其中，脚本只做确定性检查、契约生成和 Word 排版；正式正文仍由 Agent 读取完整 skill、证据契约、代码、图表和结果后整体写作。

## 复核命令

从仓库根目录运行：

```powershell
$env:PYTHONIOENCODING="utf-8"
Push-Location examples\cumcm2024-b-demo
python ..\..\packages\codex\skills\quality-assurance-auditor\scripts\evidence_gate.py
python ..\..\packages\codex\skills\paper-formal-writer\scripts\build_paper_outline.py
python ..\..\packages\codex\skills\paper-formal-writer\scripts\format_formal_docx.py
python ..\..\packages\codex\skills\paper-formal-writer\scripts\check_paper_format.py --render required
Pop-Location
```

不同平台只需要替换 skill 前缀：

```text
Trae        -> ..\..\packages\trae\.trae\skills\
Claude Code -> ..\..\packages\claude\.claude\skills\
Codex       -> ..\..\packages\codex\skills\
```

复核完成后检查：

```text
examples/cumcm2024-b-demo/paper_output/qa/evidence_gate_report.md
examples/cumcm2024-b-demo/paper_output/format_check_report.md
examples/cumcm2024-b-demo/paper_output/final_paper.docx
```

`evidence_gate_report.md` 和 `format_check_report.md` 都通过时，才可以把 `final_paper.docx` 称为正式稿样例。

## 新赛题怎么照着用

不要把 B 题样例内容复制为新赛题答案。正确用法是对照它的流程和交付结构。

1. 新建比赛项目目录。
2. 复制对应平台 skill 包到项目根目录。
3. 创建 `problem_files/`，放入官方赛题 PDF/Word 和附件。
4. 让 Agent 从 `paper-workflow-orchestrator` 开始，不要先跑 quickstart。
5. 要求 Agent 在 `paper_output/code/` 中生成当前赛题专用代码，并运行得到真实结果。
6. 先过 `quality-assurance-auditor/scripts/evidence_gate.py`。
7. 证据门禁通过后，再进入 `paper-formal-writer`：生成 `paper_outline.json`，写 `final_paper_source.md`，生成含可编辑原生公式的 `final_paper.docx`，运行 `check_paper_format.py --render required`。
8. 对照 B 题样例检查 Word 是否有正式标题层级、足够正文、图表前后解释、结果表、参考文献和附录代码说明。

推荐启动提示词：

```text
请使用 MathModel Skill，从 paper-workflow-orchestrator 开始。不要先跑 quickstart 脚本。请读取赛题和附件，生成模型路线，判断附件是原始数据还是结果模板，在 paper_output/code/ 中生成并运行当前赛题专用代码，产出真实图表、表格、指标和结论。证据门禁通过后，再调用 paper-formal-writer 生成 paper_output/plan/paper_outline.json，基于完整证据链全局撰写 paper_output/final_paper_source.md，并生成 paper_output/final_paper.docx。写作时标题采用 1 / 1.1 / 1.1.1，篇幅遵循 outline 的动态目标，禁止机械扩写；最终运行 check_paper_format.py --render required。证据门禁和格式门禁未同时通过时，不要把 Word 称为最终稿。
```

## 与 quickstart 的分工

`examples/quickstart/` 是安装验证样例，只证明 skill 包、路径和基础脚本能跑通。

`examples/cumcm2024-b-demo/` 是正式论文交付样例，重点展示：

- 证据链如何进入论文；
- 图表和表格如何进入 Word；
- 正文如何保持 `1 / 1.1 / 1.1.1` 的国赛论文层级；
- `paper-formal-writer` 如何把 Markdown 源稿转成正式 `final_paper.docx`；
- 证据门禁和格式门禁如何约束“能不能称为最终稿”。
