---
name: model-code-and-result-generator
description: "MathModel Pro P3-P5 计算与验证。实现获选模型、独立复算、随机多种子、基线、敏感性、压力测试和消融，并生成可冻结机器契约。"
---

# Pro Experiment Runner

检查点 2 必须新鲜批准。所有赛题专用代码写入 `paper_output_pro/code/`，运行产物
写入 `paper_output_pro/experiments/`、`figures/` 和 `tables/`。Skill 自带脚本只能做
通用验证，不能预制赛题结论。

- 每个关键结论至少两条独立实现或复算路径；共享核心实现不算独立。
- 随机算法至少 10 个不同种子，报告均值、方差、置信区间；区间不稳定则增加运行。
- 执行可解释基线比较、关键参数敏感性、约束压力测试和适用消融。
- 离散结果精确一致；确定性数值使用预先声明容差；统计结果比较区间与分布。
- 所有候选和失败运行保留在 manifest，含命令、退出码、原因和输出哈希。
- 空指标、占位图表、手工改结果、损坏文件或无运行记录均视为失败。

用总入口的 `pro_run_experiment.py --spec code/<run-spec>.json` 执行每次运行；批次完成后
用 `--refresh-manifest` 汇总回执。独立实现不能只换文件名，需不同核心计算路径。
报告通过 `run_id`、`metric` 引用 `metrics.json`，数值比较由统一校验器重新计算。
比较容差及统计等效界限写入获批路线报告。随机样本需可追踪到不同种子的实际运行。

必须输出 `experiment_manifest.json`、`replication_report.json`、
`robustness_report.json`、`ablation_report.json` 和 `claim_evidence_map.json`。全部使用
schema `3.3` 公共元数据并 PASS 后，回到总入口展示数值、不确定性和失败记录，
等待检查点 3。不得在检查点 3 前写正式论文。

字段细节见 [references/pro-experiment-contracts.md](references/pro-experiment-contracts.md)。
