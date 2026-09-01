---
name: pro-workflow-orchestrator
description: "MathModel Skill Pro 总入口。用于高算力数学建模、竞赛论文、Fable 5、GPT-5.6 Sol Ultra，以及需要多路线竞争、独立复算、三次用户确认和 Word/PDF 双门禁的任务。完整任务必须先调用本 skill。"
---

# MathModel Pro Workflow Orchestrator

本 Skill 是 Pro 分支唯一总入口。输出只能写入 `paper_output_pro/`。不得读取或
复用 `paper_output/`、Lite 输出、Standard 门禁或其他项目的批准记录。

## 启动

先运行平台对应命令：

```bash
python .claude/skills/pro-workflow-orchestrator/scripts/pro_preflight.py --platform claude-code --model "<用户声明模型>" --reasoning "<档位>" --multi-agent <available|unavailable|unknown> --network <available|unavailable|unknown>
```

Codex 将路径改为 `.agents/skills/`。非 Fable 5 或 GPT-5.6 Sol Ultra 仅显示能力
警告，仍执行完整 Pro 门禁，不降级、不缩减候选和验证。

若发现 Standard、Lite 或旧 Pro 混装，立即阻塞。`problem_files/` 为空也阻塞。

## P0-P9

### P0 能力与输入预检

读取 `pro_config.json` 与 `input_manifest.json`。确认附件逐文件 SHA-256 和角色：
题面、原始数据、结果模板、参考材料或未分类附件。结果模板不得当作原始数据。

### P1 多路审题

生成至少 3 份互不读取彼此输出的分析到 `analysis/independent/`。综合角色写
`problem_consensus.json`，包含共识、分歧、假设、子问题边界和附件用途。

到此必须停下，请用户确认。确认后运行：

```bash
python .claude/skills/pro-workflow-orchestrator/scripts/pro_checkpoint.py approve --checkpoint 1 --decision "<用户原意摘要>"
```

### P2 研究与模型竞赛

只自动访问公开来源。登录、付费、私有或额外授权资源先取得用户授权。关键外部
数据尽量由两个独立权威来源交叉验证，并写入 `source_ledger.json`。调用
`pro-model-tournament`，每问生成 3-5 条实质不同路线，默认 4 条，必须含可解释
基线、备选和明确淘汰理由。

展示推荐路线与实验计划后必须停下。用户确认后批准检查点 2。

### P3-P5 计算与验证

在 `code/` 和 `experiments/` 中实现获选路线及独立复算路径。关键结论至少两条
实现或复算路径。随机方法至少 10 个不同种子；区间不稳定时继续增加。必须执行
基线比较、关键参数敏感性、约束压力测试和适用消融。保留失败候选、命令、退出码
和原因，不得只展示胜者。

生成 `experiment_manifest.json`、`replication_report.json`、
`robustness_report.json` 和 `ablation_report.json`。离散结果精确比较；确定性数值
按声明容差；统计结果按区间和分布一致性判断。

### P6 证据冻结

先展示数值结果、不确定性、失败记录和适用范围，并停下等待用户确认。批准检查点
3 后才生成 `evidence_freeze.json`。冻结代码、环境、输入、输出、种子、命令、
指标、图表、表格和双向 claim 链。批准后上游变化会自动使门禁失效。

### P7-P9 写作与评审

只基于新鲜冻结证据全局撰写 `final_paper_source.md`，不得用微单元拼接正式主稿。
调用 `pro-review-board` 执行数学、复现、来源、表达、对抗质疑五个隔离评审角色，
修复后整轮重审，直到无 Critical/Major。

从同一源稿生成 `final_paper.docx`，再用 LibreOffice 渲染：

```bash
python .claude/skills/pro-workflow-orchestrator/scripts/pro_render_pdf.py
python .claude/skills/pro-workflow-orchestrator/scripts/pro_format_check.py
python .claude/skills/pro-workflow-orchestrator/scripts/pro_gate.py
```

必须检查 PDF 页数、可提取文本、公式、图表、分页和 DOCX/PDF 引用一致性，再运行
最终 Pro gate。Word 或 PDF 任一门禁失败都不得称为正式交付。

## 检查点规则

1. 题意与附件分类确认后才能研究和选模。
2. 模型路线确认后才能计算。
3. 数值结果与不确定性确认后才能冻结证据和写论文。

每次继续前运行 `pro_checkpoint.py validate`。若返回失效，回到最早失效阶段。拒绝
会使本检查点和全部下游失效。不得手工编辑 ledger 绕过确认。

## 多代理与失败策略

多代理可用时并行运行隔离角色；不可用时用相互隔离的上下文顺序执行相同角色，
不得退化为单路线或单评审。相同规范化失败连续 3 次，或缺少用户数据/授权时才
报告阻塞；其余情况继续修复。没有 Token、候选总量或运行时间预算。

详细字段、哈希和停止条件见 [references/pro-contracts.md](references/pro-contracts.md)。
