---
name: context-memory-keeper
description: "记录 MathModel Pro P0-P9 进度、三个检查点、失败签名、当前证据哈希和下一动作，用于长任务断点恢复。"
---

# Pro Context Memory

每个 P 阶段、检查点决定、实验批次、评审轮次和渲染尝试结束后更新
`paper_output_pro/context/workflow_memory.json` 与 `.md`。记录当前阶段、检查点状态、
当前模型档案与实际推理档位、指令审计、关键产物哈希、失败签名及连续次数、阻塞
授权、已完成角色和下一动作。上下文压缩时必须保留用户批准内容及其哈希、当前模型
档案、未完成角色、失败计数和下一条可执行动作。

恢复时先运行 `pro_checkpoint.py validate`，再重算关键产物哈希。ledger 和当前文件
优先于记忆；记忆不得授予检查点批准或覆盖门禁。相同规范化失败连续 3 次时才记录
为重复失败阻塞，缺少用户数据/授权可立即记录为外部阻塞。

```bash
python .agents/skills/context-memory-keeper/scripts/update_pro_memory.py --phase P3 --next-action "<下一动作>" --failure "<可选失败>"
```
