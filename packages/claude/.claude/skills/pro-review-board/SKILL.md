---
name: pro-review-board
description: "对 MathModel Pro 冻结证据和正式论文执行数学正确性、代码复现、来源、表达、对抗质疑五角色隔离审稿与修复闭环。"
---

# Pro Review Board

仅在检查点 3 新鲜批准且 `evidence_freeze.json` 有效后运行。五个角色必须相互隔离
完成一整轮后才能汇总；多代理不可用时，用五个全新隔离会话顺序执行，不得合并角色。
同一会话中切换五个角色名称不算隔离。宿主无法提供独立上下文时报告能力阻塞。

## 五个角色

1. `mathematical_correctness`
2. `code_reproducibility`
3. `source_provenance`
4. `paper_expression`
5. `adversarial_challenge`

每个 finding 记录 ID、级别、证据、修复要求、责任对象和处置状态。级别只能是
`CRITICAL`、`MAJOR`、`MINOR` 或 `NOTE`。局部修改时可定向复查；最终一轮必须
让五个角色检查同一版本的主稿、写作计划和冻结证据，不能沿用旧稿审稿结论。

使用总入口的 `pro_collect_reviews.py --project-root <项目> --round 1 --prepare`
生成待审请求，按真实执行结果填写 `reviews/round-1/<role>.json`。每份报告必须保留
实际上下文 ID、模型、宿主执行记录路径及哈希、执行过的检查和有内容的评价。
完整竞赛模式下，每位评审都必须对每个确认子问题填写 `subproblem_assessments`：
题号、`ADEQUATE/INADEQUATE`、具体段落与证据说明。篇幅达标或锚点齐全不能代替
论证深度判断；缺答、推导跳步、结果没有解释、验证流于形式应列为 Major。
审稿结束后去掉 `--prepare` 收集验证。不得把空模板或自动测试的模拟记录作为正式审稿。

最终轮必须没有未解决 Critical/Major，才能将 `review_board_report.json` 标为 PASS。
同一规范化失败连续 3 轮出现时记录阻塞；否则继续修复，不设成本或时间预算。

验证：

```bash
python .claude/skills/pro-review-board/scripts/validate_review_board.py
```

Codex 使用 `.agents/skills/`。详细准则见
[references/review-rubric.md](references/review-rubric.md)。完成后回到总入口执行
DOCX/PDF 和最终 Pro gate。
