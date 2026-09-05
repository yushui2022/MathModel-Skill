---
name: pro-workflow-orchestrator
description: "MathModel Skill Pro 总入口。用于 GPT-6 Astra、Claude Fable 5.1、Opus 5、Sonnet 5 等前沿模型执行高算力数学建模、多路线竞赛、独立复算、三次用户确认和 Word/PDF 双门禁。完整任务必须先调用本 skill。"
---

# MathModel Pro Workflow Orchestrator

本 Skill 是 Pro 分支唯一总入口。输出只能写入 `paper_output_pro/`。不得读取或
复用 `paper_output/`、Lite 输出、Standard 门禁或其他项目的批准记录。

## 启动

先运行平台对应命令：

```bash
python .agents/skills/pro-workflow-orchestrator/scripts/pro_preflight.py --platform claude-code --model "<用户声明模型>" --reasoning "<档位>" --multi-agent <available|unavailable|unknown> --network <available|unavailable|unknown> --parallel-tools <available|unavailable|unknown> --async-tools <available|unavailable|unknown>
```

Codex 将路径改为 `.agents/skills/`。首选模型为 GPT-6 Astra 与 Claude Fable 5.1；
Claude Opus 5、Sonnet 5、Fable 5 和 GPT-5.6 Sol 保持完整支持。其他模型仅显示
能力警告，仍执行完整 Pro 门禁，不降级、不缩减候选和验证。

若发现 Standard、Lite 或旧 Pro 混装，立即阻塞。`problem_files/` 为空也阻塞。

## 前沿模型执行契约

读取 `pro_config.json` 中的 `model_profile`、`reasoning_profile` 和
`execution_policy`。仅在平台支持时按阶段切换推理档位；不能切换时记录实际档位，
不得假装已经切换。模型档案过期或未识别且联网可用时，先核对厂商官方资料。

P0 生成 `instruction_manifest.json` 后，读取其中每个项目指令和 Pro `SKILL.md`，
写 `instruction_audit.json`。它必须覆盖全部当前哈希、解释冲突如何解决、没有未解决
冲突，并原样保留 `required_execution_contract`，否则检查点 1 不能批准。

三个正式检查点是正常流程中仅有的用户暂停点。其余已授权且可逆的工作持续完成；
只有缺少用户数据/授权、超出范围的不可逆外部操作或同类失败连续三次才额外停止。
独立工作在平台支持时同批并行发起，主 Agent 同时推进不依赖其结果的工作；无多代理
时仍以隔离上下文顺序执行。按模型读取
[frontier-model-guidance.md](references/frontier-model-guidance.md)，不要把厂商提示规则
复制到每个阶段 Skill。

## P0-P9

### P0 能力与输入预检

读取 `pro_config.json`、`input_manifest.json` 和指令审计。确认附件逐文件 SHA-256 和角色：
题面、原始数据、结果模板、参考材料或未分类附件。结果模板不得当作原始数据。
默认 `paper_delivery.mode=competition`，以约 20 页完整论文规划（18-24 页目标），
正文有效字符下限 8000 仅用于拦截极短稿，不表示优秀标准或字符到页数的换算。
按赛题选 `--contest cumcm-2026|mcm-2026|generic`，年份不同须核对规则，不套用旧上限。
短报告/工程测试必须显式使用 `--paper-mode short-report|smoke-test --scope-reason "<原因>"`。
自定义篇幅使用 `--target-pages <下限> <目标上限> --minimum-body-characters <下限>` 并说明原因。

### P1 多路审题

生成至少 3 份互不读取彼此输出的分析到 `analysis/independent/`。支持并行时一次
发起全部独立角色，主 Agent 同时准备综合框架。综合角色写
`problem_consensus.json`，包含共识、分歧、假设、子问题边界和附件用途。

到此展示题意、逐问任务、交付模式、页数计数范围和目标，让用户一并确认。
正常完整论文不得自行降为短报告；确认后运行：

```bash
python .agents/skills/pro-workflow-orchestrator/scripts/pro_checkpoint.py approve --checkpoint 1 --decision "<用户原意摘要>"
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

每次计算使用 `pro_run_experiment.py --spec code/<run-spec>.json`，由脚本记录真实命令、
退出码、输入输出哈希和环境。并行批次全部完成后运行该脚本的 `--refresh-manifest`。
报告引用实际 `run_id` 和指标键，禁止手工代写运行回执。比较规则在检查点 2 前确定。
公开来源用 `pro_capture_source.py` 保存原始响应和检索回执。

### P6 证据冻结

先展示数值结果、不确定性、失败记录和适用范围，并停下等待用户确认。批准检查点
3 后才生成 `evidence_freeze.json`。冻结代码、环境、输入、输出、种子、命令、
指标、图表、表格和双向 claim 链。批准后上游变化会自动使门禁失效。

### P7-P9 写作与评审

只基于新鲜冻结证据全局撰写 `final_paper_source.md`，不得用微单元拼接正式主稿。
先读正式写作 Skill 的 `references/competition-authoring.md`，再写 `paper_plan.json`，
绑定配置、共识和冻结哈希，明确逐问论证映射、章节类型、目标篇幅和冻结图表。
以完整章节组织内容，允许局部修订；主稿始终只有一个。关键结论段落加入
`<!-- claim:C1 -->` 等可移除证据标记，数值按证据声明的精度显示。
执行 `pro_paper_audit.py` 检查逐问覆盖、论证段落、正文篇幅、关键数值、图表和重复正文。
长篇正式写作默认采用模型档案的 `authoring` 档位；推理阶段只确定证据和结构，正文
分章节多轮写入唯一主稿并全局统一，避免在推理与正式输出中重复生成整篇论文；
单次输出限制不是缩短论文的理由。缺少证据必须回算，不靠文字填充。
调用 `pro-review-board` 执行数学、复现、来源、表达、对抗质疑五个隔离评审角色，
每个角色使用真实独立上下文并保存执行记录，审稿绑定当前主稿、计划和冻结证据哈希。
普通文字修改可先局部检查；最终交付前五个角色必须全部审阅同一最新版本，且无
未解决 Critical/Major。工具不可创建独立上下文时明确报告能力缺失，不得用五个标签
冒充五次独立执行。提示词和计数不能代替实际审阅。

从同一源稿生成 `final_paper.docx`，再用 LibreOffice 渲染：

```bash
python .agents/skills/pro-workflow-orchestrator/scripts/pro_render_pdf.py
python .agents/skills/pro-workflow-orchestrator/scripts/pro_format_check.py
python .agents/skills/pro-workflow-orchestrator/scripts/pro_gate.py
```

必须检查 PDF 页数、可提取文本、公式、图表、分页和 DOCX/PDF 引用一致性，再运行
最终 Pro gate。Word 或 PDF 任一门禁失败都不得称为正式交付。
页数按真实 PDF 章节位置计算，遵守比赛上限；不足已确认下限时补充实质内容或重新
确认范围。测试与短报告的 PASS 必须同时展示 acceptance_scope，不算完整竞赛长文验收。
渲染器生成 `render_manifest.json` 和每页 PNG；逐页实际打开检查后写
`visual_review.json`，逐页记录哈希、观察和未解决问题。不得自动填充视觉 PASS。

## 检查点规则

1. 题意与附件分类确认后才能研究和选模。
2. 模型路线确认后才能计算。
3. 数值结果与不确定性确认后才能冻结证据和写论文。

每次继续前运行 `pro_checkpoint.py validate`。若返回失效，回到最早失效阶段。拒绝
会使本检查点和全部下游失效。不得手工编辑 ledger 绕过确认。

## 多代理与失败策略

多代理可用时并行运行隔离角色并明确角色数、输入、产物和完成条件；不可用时用
相互隔离的上下文顺序执行相同角色，
不得退化为单路线或单评审。相同规范化失败连续 3 次，或缺少用户数据/授权时才
报告阻塞；其余情况继续修复。没有 Token、候选总量或运行时间预算。

详细字段、指令审计、哈希和停止条件见
[references/pro-contracts.md](references/pro-contracts.md)。
优秀论文的判断标准和各类问题的验证重点见
[references/paper-quality.md](references/paper-quality.md)。
