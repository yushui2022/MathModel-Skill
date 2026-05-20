# Prompt Assets

MathModel Skill 的核心资产不是一键脚本，而是项目中长期沉淀的高质量提示词、评分闭环、模型选择逻辑、QA 审稿规则和微单元长文拆解模板。

本轮 Agent-native 重构只改变使用定位，不删除、不压缩、不降级这些提示词资产。

## 保留原则

- 不删除任何已有 `SKILL.md` 中的核心提示词内容。
- 不删除任何已有 `references/` 中的提示词文件。
- 不把长提示词改写成短摘要后丢掉原文。
- 如果为了可读性拆分文件，必须完整迁移原文到 `references/`，并在原 `SKILL.md` 中明确引用。
- `paper-micro-unit-generator` 的附录 A 不作为正式主流程，但作为高质量长文提示词资产保留。

## 资产类型

| 资产 | 主要位置 | 用途 |
|---|---|---|
| 赛题解析提示词 | `problem-doc-model-selector/SKILL.md` | 指导 Agent 把 PDF/Word 题面拆成结构化子问题 |
| 模型选择提示词 | `modeling-paper-rubric-and-model-selector/` | 指导每问选择主模型、基线模型、备选模型和公式要求 |
| 评分闭环提示词 | `modeling-paper-rubric-and-model-selector/references/` | 让模型路线、评分点和论文章节位置对齐 |
| 数据图表提示词 | `data-cleaning-and-visualization/` | 指导 Agent 参考脚本样板生成当前赛题专用清洗和绘图代码 |
| 结果证据提示词 | `model-code-and-result-generator/` | 指导 Agent 把真实建模输出写回结果、指标、结论和表格契约 |
| QA 审稿提示词 | `quality-assurance-auditor/SKILL.md` | 检查题意覆盖、证据链、模型一致性和图表引用 |
| 微单元长文提示词 | `paper-micro-unit-generator/SKILL.md` | 提供 CUMCM 风格的章节、段落、句级长文写作模板 |

## 正式写作时怎么用

正式论文不再由微单元脚本机械拼接。Agent 应先读取完整证据链：

```text
problem_analysis.json
model_route.json
rubric_alignment.json
data_plan.json
visualization_plan.json
figure_index.json
model_results.json
metrics.json
conclusions.json
table_index.json
tasks.json
```

然后按需引用提示词资产：

- 用模型选择提示词检查每问模型是否贴题。
- 用评分闭环提示词检查每个高分点是否有正文落点。
- 用数据图表提示词生成当前赛题专用图表，而不是机械套用固定列名。
- 用结果证据提示词确保结论来自真实代码输出。
- 用微单元提示词辅助摘要、问题重述、模型假设、结果分析和结论的局部扩写。

## Quickstart 和正式稿的区别

Quickstart 可以使用离线脚本生成验证草稿，目的是确认 skill 包安装成功、目录规划正确、JSON 契约链路可跑。

正式稿必须由 Agent 在证据门禁通过后整体写作。若结果仍标记为 `needs_real_modeling` 或 `scaffold_result_needs_review`，只能作为待补草稿，不能当成比赛最终稿。
