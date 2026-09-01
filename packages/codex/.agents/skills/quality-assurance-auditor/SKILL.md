---
name: quality-assurance-auditor
description: "MathModel Pro 证据审计与冻结。检查运行溯源、复算、稳健性、来源、文件哈希和 claim 双向追踪，并在检查点 3 后冻结证据。"
---

# Pro Evidence Auditor

本 Skill 不生成模型结果，只审计现有证据。先运行 `pro_checkpoint.py validate`。
检查点 2 不新鲜时禁止接受计算；检查点 3 不新鲜时禁止冻结。

逐项重算 `experiment_manifest.json` 的脚本、输入和输出 SHA-256，拒绝运行后手工修改。
检查关键结果双路复算、随机多种子统计、基线、敏感性、压力测试、消融、失败候选、
公开来源和 claim 双向追踪。空指标、占位图表、损坏文件不能 PASS。

展示结果与不确定性并取得检查点 3 批准后运行：

```bash
python .agents/skills/pro-workflow-orchestrator/scripts/pro_freeze_evidence.py
```

`evidence_freeze.json` 是 P7-P9 唯一可用证据快照。之后任何上游文件变化都必须使
冻结和下游门禁失效并重新计算。不得复制旧项目冻结文件。
