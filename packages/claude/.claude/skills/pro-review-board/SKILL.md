---
name: pro-review-board
description: "对 MathModel Pro 冻结证据和正式论文执行数学正确性、代码复现、来源、表达、对抗质疑五角色隔离审稿与修复闭环。"
---

# Pro Review Board

仅在检查点 3 新鲜批准且 `evidence_freeze.json` 有效后运行。五个角色必须相互隔离
完成一整轮后才能汇总；多代理不可用时，用五个隔离上下文顺序执行，不得合并角色。

## 五个角色

1. `mathematical_correctness`
2. `code_reproducibility`
3. `source_provenance`
4. `paper_expression`
5. `adversarial_challenge`

每个 finding 记录 ID、级别、证据、修复要求、责任对象和处置状态。级别只能是
Critical、Major、Minor 或 Note。全部角色完成后统一修复，再重新运行完整五角色，
不能只复查提出问题的角色。

最终轮必须没有未解决 Critical/Major，才能将 `review_board_report.json` 标为 PASS。
同一规范化失败连续 3 轮出现时记录阻塞；否则继续修复，不设成本或时间预算。

验证：

```bash
python .claude/skills/pro-review-board/scripts/validate_review_board.py
```

Codex 使用 `.agents/skills/`。详细准则见
[references/review-rubric.md](references/review-rubric.md)。完成后回到总入口执行
DOCX/PDF 和最终 Pro gate。
