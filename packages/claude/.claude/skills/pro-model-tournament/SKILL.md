---
name: pro-model-tournament
description: "为 MathModel Pro 的每个子问题建立 3-5 条实质不同模型路线，执行七维评分、基线比较、风险分析和实验竞赛。仅在检查点 1 新鲜批准后使用。"
---

# Pro Model Tournament

本 Skill 替代单路线模型选择。开始前运行 `pro_checkpoint.py validate`，确认检查点
1 为新鲜 `APPROVED`；否则回到 `pro-workflow-orchestrator`。

## 输入

- `paper_output_pro/problem_consensus.json`
- `paper_output_pro/source_ledger.json`
- `paper_output_pro/input_manifest.json`
- 用户已确认的目标、限制和评价偏好

## 生成候选

对每个子问题生成 3-5 条实质不同路线，默认 4 条。必须包含可解释基线。只改变
超参数、随机种子或优化器不算新路线。每条路线记录模型族、假设、数据需求、
约束、失败模式、实验计划、预期证据和实施风险。

先声明七维权重且总和为 1，再按任务适配、数据可行性、验证能力、稳健性、
可解释性、创新价值和实施风险分别给 0-10 分。不得为迎合偏好事后调权。

## 输出

写入 `candidate_routes.json` 和 `tournament_report.json`。每个子问题必须有：

- 一条推荐路线和一条不同的备选路线；
- 对其余每条路线的具体淘汰理由；
- 预注册式实验计划、预期证据和停止/扩展条件；
- 基线、独立复算、敏感性、压力测试与消融安排；
- 失败候选保留策略。

运行：

```bash
python .claude/skills/pro-model-tournament/scripts/validate_tournament.py
```

Codex 使用 `.agents/skills/`。验证失败时修复契约，不得进入计算。验证通过后回到
总入口展示路线，等待用户确认检查点 2。

详细评分定义见 [references/tournament-rubric.md](references/tournament-rubric.md)。
