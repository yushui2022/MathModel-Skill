---
name: data-cleaning-and-visualization
description: "MathModel Pro 数据读取、清洗、可视化和数据质量验证。严格遵守 P0 附件分类并为实验 manifest 生成可哈希产物。"
---

# Pro Data And Visualization

只读取 `problem_files/`、已授权的 `crawled_data/` 和 Pro 契约，只写
`paper_output_pro/`。只把 `raw_data` 用于建模，结果模板、题面和参考材料不可机械
清洗为训练数据。

- 保留原始文件，只在 `data_cleaned/` 写新产物；记录编码、sheet、字段、单位、缺失、
  异常、重复、时区和解析决策。
- 每个转换记录脚本、参数、输入/输出哈希和行列变化；禁止静默丢行或填补。
- 对预测任务防止时间/目标泄漏，对图任务核对节点边语义，对优化任务核对单位和约束。
- 私有数据只在用户授权范围内使用，不得上传或伪装为公开来源。
- 图表必须由真实数据和可复现脚本生成，并记录 claim、输入哈希、标题、单位和状态。

占位图、空图、损坏图不能进入证据冻结。保留的通用脚本可以辅助读取和绘图，但需
按当前赛题调整，所有产物必须登记到 `experiment_manifest.json`。
