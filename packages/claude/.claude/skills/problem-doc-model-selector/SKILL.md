---
name: problem-doc-model-selector
description: "MathModel Pro P1 审题技能。读取赛题和附件，执行至少三份隔离审题并综合为 problem_consensus.json。"
---

# Pro Problem Consensus

仅在 P0 预检 PASS 后运行。读取 `paper_output_pro/input_manifest.json`，不得重新按
文件名猜附件用途，也不得读取 Standard/Lite 输出。

## 隔离审题

建立至少三个角色，各自只能读取题面、附件 manifest 和用户要求，不能读取其他角色
输出。建议视角：数学结构与变量边界；数据、附件与可识别性；竞赛交付、约束与反例。

每份分析写入 `paper_output_pro/analysis/independent/analysis_<id>.json`，并包含 Pro
机器契约元数据、题意摘要、显式/隐式约束、子问题、假设、附件用途、未知项和风险。

## 综合

综合角色读取全部隔离分析，写 `paper_output_pro/problem_consensus.json`：

- `independent_analyses` 至少三个，并记录各自文件哈希；
- `consensus`、`disagreements`、`assumptions` 均不得省略；
- `subproblems` 为每问给出边界、输入、输出、约束和成功判据；
- `attachment_roles` 必须与 P0 manifest 一致；
- 未解决歧义写入 `questions_for_user`，不得擅自填补关键数据。

运行 `scripts/validate_problem_consensus.py`。通过后回到
`pro-workflow-orchestrator`，展示共识、分歧和附件分类，等待检查点 1 确认。
