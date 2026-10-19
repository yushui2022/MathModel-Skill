# Modeling Result Guidelines

本参考文件用于指导 Agent 把数学建模结果沉淀为结构化证据，而不是把临时计算过程直接写进正文。

## 必须沉淀的证据

每个 `question_id` 尽量提供以下信息：

- 模型输出：预测值、最优方案、评价得分、分类结果、聚类标签、仿真曲线摘要等。
- 指标：误差、得分、目标函数值、约束满足率、稳定性指标、敏感性指标等。
- 表格：参数表、结果表、误差表、模型对比表、敏感性分析表或排序表。
- 结论：能直接回答原问题的结构化结论。

## 使用边界

`build_result_contracts.py` 会生成结果证据契约、基础数据画像和 q1/q2/q3 建模代码脚手架。它提供的是当前赛题专用代码起点，不承诺自动得到最终比赛结果。

真实赛题仍应由 Agent 根据当前数据字段、模型路线、约束和评分点修改 `paper_output/code/modeling/q*_model.py`，运行后把真实结果写回 `paper_output/results/` 和 `paper_output/tables/`。

不得把 `status=draft_contract`、`status=to_be_filled`、`evidence_status=needs_real_modeling` 或 `evidence_status=scaffold_result_needs_review` 的内容伪装成最终比赛结论。
