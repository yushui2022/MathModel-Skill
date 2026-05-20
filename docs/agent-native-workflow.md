# Agent-Native Workflow

MathModel Skill 的正式使用方式不是先运行一键脚本，而是让 Agent 读取总控 skill 后按当前赛题推进。脚本负责辅助、沉淀和检查；正式建模、代码生成、图表解释和论文写作由 Agent 在 skill 约束下完成。

## 正式流程

```text
读题
-> 拆题
-> 模型路线
-> 判断附件性质
-> 生成/修改赛题专用代码
-> 运行代码
-> 生成真实图表、表格、指标和结论
-> 证据门禁
-> Agent 全局写作
-> 最终 QA
```

## 使用方式

把赛题 PDF/Word 和附件放入：

```text
problem_files/
```

然后对 Agent 说：

```text
请使用 MathModel Skill，从 paper-workflow-orchestrator 开始。
不要先跑 quickstart 脚本。请读取赛题和附件，生成模型路线，判断附件是原始数据还是结果模板，在 paper_output/code/ 中生成并运行当前赛题专用代码，产出真实图表、表格、指标和结论。证据门禁通过后，再基于完整证据链全局撰写 final_paper.md 和 final_paper.docx。
写作时可以引用 paper-micro-unit-generator 中保留的微单元提示词资产，但不要机械拼接，要按当前题目的模型、结果和评分点整体成文。
```

## 附件判断

Agent 必须先判断附件性质：

| 类型 | 处理方式 |
|---|---|
| 原始数据 | 读取字段、单位、口径和样本粒度，生成清洗和建模代码 |
| 结果模板 | 只作为输出格式参考，不能当成输入数据机械清洗 |
| 说明文档 | 提取约束、公式、参数和格式要求 |
| 参考材料 | 提取背景、规则、定义和可引用信息 |

像官方要求填写的 `result*.xlsx` 通常是结果模板。它可以指导输出表格格式，但不能直接支撑真实建模结论。

## 代码落点

当前赛题专用代码只写入：

```text
paper_output/code/
├── data_processing/
├── visualization/
├── modeling/
└── qa/
```

不要把当前赛题的 `q1_model.py`、绘图脚本或清洗脚本写回 `.trae/skills/`、`.claude/skills/` 或 `skills/`。

## 证据门禁

正式成稿前运行：

```bash
python skills/quality-assurance-auditor/scripts/evidence_gate.py
```

Trae 和 Claude Code 用户按平台路径替换：

```bash
python .trae/skills/quality-assurance-auditor/scripts/evidence_gate.py
python .claude/skills/quality-assurance-auditor/scripts/evidence_gate.py
```

如果任一子问题仍是以下状态，不得把 Word 称为最终稿：

```text
missing
needs_real_modeling
scaffold_result_needs_review
draft_contract
to_be_filled
template
draft
```

## Quickstart 的定位

`quickstart_run.py` 只用于安装验证和 smoke test：

```bash
python skills/paper-workflow-orchestrator/scripts/quickstart_run.py
```

它可以验证目录、依赖、JSON 契约、任务清单、微单元和 Word 草稿链路是否能跑通，但输出的是验证草稿，不代表真实比赛论文质量。

旧命令 `run_all.py` 已废弃，只保留迁移提示。
