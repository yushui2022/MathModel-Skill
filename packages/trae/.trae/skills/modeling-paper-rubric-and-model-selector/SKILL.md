---
name: "modeling-paper-rubric-and-model-selector"
description: "按常见评分点生成建模论文结构与写作清单，并根据题目类型与数据条件给出模型选择与对照实验路线。Invoke when需要“论文格式/评分对齐/模型选型/路线不确定”。"
---

# 评分对齐论文结构与模型选型（Paper Rubric & Model Selector）

## 全局流程协作约束（长对话防漂移）

- 本 skill 不得作为孤立入口。用户要求完整论文、生成 Word、继续流程或不确定阶段时，先回到 `paper-workflow-orchestrator` 判断当前 S0-S8 阶段。
- 启动或继续本 skill 的正式任务前，必须运行：
  ```bash
  python .trae/skills/paper-workflow-orchestrator/scripts/workflow_guard.py --skill modeling-paper-rubric-and-model-selector
  ```
- 如果输出 `[WORKFLOW FAIL]` 或报告 `status != "PASS"`，停止本 skill，按 `paper_output/qa/workflow_guard_report.json` 的失败项回补前置阶段，不得凭记忆继续。
- 本 skill 只写入自己契约范围内的 `paper_output/` 产物；完成后必须回到 `paper-workflow-orchestrator` 判断下一步，并用 `context-memory-keeper` 记录已完成产物、阻塞项和下一步。
- 长对话中如果上下文变长、阶段不确定或用户分开调用 skill，先运行：
  ```bash
  python .trae/skills/paper-workflow-orchestrator/scripts/workflow_guard.py --status
  ```
  再读取 `paper_output/qa/workflow_guard_report.json`、`paper_output/preflight_report.json`、`paper_output/input_manifest.json`、`paper_output/results/run_manifest.json` 和本 skill 的上游 JSON 契约，按报告里的 `recommended_skill` 与 `next_action` 继续。
- ?? `paper_output/context/workflow_memory.json` ?????????????? `current_step`?`next_step`?`recommended_skill`????????????????????
- ? skill ???????????? `paper-workflow-orchestrator` ?? `workflow_guard.py --status`?????
  ```bash
  python .trae/skills/context-memory-keeper/scripts/update_workflow_memory.py
  ```
  ?? `paper_output/context/workflow_memory.json` / `.md`?????????????

## 执行契约
- 上游输入：优先读取 `paper_output/step1/problem_analysis.json`。
- 必须输出：`paper_output/plan/model_route.json`、`rubric_alignment.json`、`scoring_strategy.md`。
- 下游交接：`quality-assurance-auditor` 读取模型路线生成 `tasks.json`；`paper-micro-unit-generator` 通过 `tasks.json` 使用模型、验证和评分字段。
- 推荐下一步：若需要外部数据，进入 `authoritative-data-harvester`；否则进入 `data-cleaning-and-visualization`。完整论文目标应回到 `paper-workflow-orchestrator` 判断后续阶段。
- 失败回退：若 `problem_analysis.json` 缺失，先运行 `problem-doc-model-selector`；完整 workflow 中本步骤失败时，QA 应回退到 `problem_analysis.json`。

## 目标
把“能拿分”的写作结构与“贴题可落地”的模型选型融合成一套可复用流程，输出：
- 一份可直接套用的论文大纲（按题目问法定制）
- 评分点对齐表（每个评分点对应你论文中的证据位置）
- 模型选型与对照实验路线（含基线、改进、验证与解释）

## 何时调用
- 需要快速搭建符合评分标准的论文结构与写作顺序
- 不确定模型是否贴题、是否过度复杂或解释不足
- 已有方案但担心“答非所问/指标口径不对/验证不充分”

## 输入（尽量提供）
- 比赛名称/年份/题号（可选）
- 题面原文或关键要求（必须）
- 你对每问的理解（可选，但强烈建议）
- 数据情况：来源、字段、时间跨度、样本量、缺失比例（可选）
- 约束与输出：需要预测/优化/评价/分类/聚类/仿真/调度等（必须）
- 你想强调的亮点：创新点/可解释性/可复现性（可选）

## 输入契约（推荐）
执行前优先读取：

- `paper_output/step1/problem_analysis.json`

如果该文件存在，必须以其中的 `questions[]` 作为唯一子问题来源，不得自行臆造、合并或丢弃子问题。

## 输出契约（推荐）
本 skill 应生成：

- `paper_output/plan/model_route.json`：每一问的模型路线、验证计划、图表证据与章节落点。
- `paper_output/plan/rubric_alignment.json`：评分点、证据形式和 QA 规则映射。
- `paper_output/plan/scoring_strategy.md`：给人和 Agent 阅读的评分闭环说明。

这些 JSON 是项目自定义 workflow contracts，不是平台内置标准。详细规则见 `docs/workflow-contracts.md`。

## 脚本入口（推荐）
```bash
python .trae/skills/modeling-paper-rubric-and-model-selector/scripts/build_model_route.py
```

该脚本会读取 `paper_output/step1/problem_analysis.json`，并将模型路线与评分闭环写入 `paper_output/plan/`。若该文件不存在，应先运行 `problem-doc-model-selector`。

## 外部“论文结构提示词”资源（可选）
支持把你预先准备的论文结构提示词文件（或文本）附加到本技能中，用于生成与评估。

### 分层目录约定（推荐）
- `SKILL.md`：技能定义与用法说明
- `references/`：可复用的参考材料与提示词资源（默认模板、评分点清单等）

### 使用方式（任选其一）
1) 路径引用（推荐）
- 在调用时提供：`paper_prompt_path`
- 规则：若提供该路径，则优先读取其内容作为“论文结构提示词”；若未提供，则使用本技能自带的默认提示词文件。

2) 直接粘贴
- 在调用时提供：`paper_prompt_text`
- 规则：若提供该文本，则优先使用该文本；否则使用 `paper_prompt_path`；若两者都没有，则使用默认提示词文件。

### 调用示例
- 方式1（路径）：
  - `paper_prompt_path: <项目根目录>\paper_output\plan\paper_prompt.md`
- 方式2（粘贴）：
  - `paper_prompt_text: <把你的论文结构提示词全文粘贴在这里>`

### 运行时整合机制（推荐参考）
在生成 A/B/C/D 任一产出前，**建议读取** `references/paper_prompt_default.md` 作为“结构参考”：
1. **参考优先级**：此文件作为写作模板的参考，但**不强制阻塞**生成。生成的论文大纲应尽量对应此文件的章节要求，但允许模型根据实际语境发挥。
2. **防遗忘机制**：
   - 建议在 Prompt 中提及此文件的核心结构（如六段式摘要），引导模型生成。
   - 若用户提供了额外的 prompt，则以用户的要求为主，此文件为辅。
3. **鼓励扩写**：在保证逻辑通顺的前提下，**鼓励**使用学术化的“万金油”语句（如“随着…的发展”、“综上所述”）来丰富篇幅，增强文章的连贯性与体量感。

然后把 `PAPER_PROMPT` 作为强约束与写作风格来源，融入到：
- 论文大纲的章节命名、写作顺序、字数分配与语体要求
- 评分点对齐表中的“证据形态”（哪些图、哪些表、哪些检验）
- 模型路线与对照实验设计（尤其是“模型检验/鲁棒性/敏感性/可复现”要求）

### 向后兼容
不提供 `paper_prompt_path` / `paper_prompt_text` 时，本技能维持原有默认行为正常输出。

## 约束（必须遵守）

- **Memory Interaction (必做)**:
  - **开始前**，检查 `memoryskill.md` 中的 `External Resources / Literature`，若存在相关文献，必须将其融入“参考文献”章节及“模型建立”部分的背景综述中。
  - **完成后**，将生成的“论文大纲”与“模型路线”更新至 `memoryskill.md`。

## 产出（固定结构）
### A. 一页纸题意对齐
- 每一问：输入、输出、评价指标、关键约束、边界条件、可行验证方式

### B. 论文大纲（按评分友好顺序）
必须包含并按题目调整比重：
1. 摘要（中英文按要求）：问题、方法、结果、贡献、关键词
2. 问题重述：用你自己的话把每问变成可计算任务
3. 模型假设：必要且可辩护，逐条说明合理性与影响
4. 符号与变量说明：表格化，含单位与范围
5. 数据说明与预处理：来源、清洗规则、缺失/异常处理、可复现步骤
6. 模型建立（按问分小节）：目标函数/约束/损失、推导或结构说明
7. 求解方法与实现：算法步骤、复杂度/收敛、参数设置
8. 结果与分析：主结果、可视化、对比、误差/收益解释
9. 模型检验：对照实验、敏感性分析、鲁棒性测试、极端情景
10. 结论与建议：对应每问给结论与可执行建议
11. 不足与展望：诚实但不自毁，指出改进方向
12. 参考文献：规范引用题面、数据源与关键方法
13. 附录：关键代码、额外图表、符号补充（按比赛要求取舍）

### C. 评分点对齐表（以“证据”为核心）
输出一张表：评分点 → 你提供的证据 → 论文位置（章节/图表/表格/实验）。
常见评分点映射（按比赛可增删）：
- 题意理解准确：一页纸题意对齐 + 问题重述逐问可计算
- 模型合理性：目标/约束与题面一致，假设可辩护
- 方法创新/改进：在基线之上有明确改进点，并说明为何有效
- 结果可信：有验证、有对比、有误差分析或约束满足证明
- 表达清晰：符号统一、图表自解释、结论逐问对应
- 可复现：数据来源与处理、参数设置、算法步骤完整

### D. 模型选型与路线（先贴题再高级）
对每一问输出：
- 任务类型判定：预测/分类/聚类/评价/优化/仿真/机理建模
- 最小可用基线：能跑通、可解释、可对照
- 一到两条改进路线：提升精度/鲁棒/效率/解释
- 验证计划：指标、交叉验证/留出法/回测、消融、敏感性
- 风险点：数据不足、口径不一、过拟合、不可解释、计算超时

## 模型选型速查（按题目常见问法）
### 1) 预测类（时间序列/回归）
适用：给定历史，预测未来或估计参数。
- 基线：移动平均/指数平滑/线性回归/ARIMA（能解释趋势与季节）
- 改进：特征工程 + 树模型；或 LSTM/Transformer（样本量足够再上）
- 验证：滚动回测、MAPE/RMSE、置信区间/误差分解

### 2) 分类/判别
适用：判定类别、风险等级、是否发生。
- 基线：逻辑回归/朴素贝叶斯（可解释）
- 改进：随机森林/梯度提升；代价敏感学习（类别不平衡）
- 验证：AUC/F1/PR 曲线、混淆矩阵、阈值敏感性

### 3) 评价/排序/综合指数
适用：多指标打分、排序、择优。
- 基线：规范化 + 加权和（权重可来自题面或专家）
- 改进：熵权/CRITIC/AHP/TOPSIS/VIKOR（明确权重来源与意义）
- 验证：权重敏感性、排名稳定性、与已知事实对照

### 4) 优化/调度/选址/路径
适用：资源分配、成本最小/收益最大、满足约束。
- 基线：线性规划/整数规划（目标与约束写清楚）
- 改进：多目标（加权/ε-约束）、启发式（遗传/模拟退火）用于大规模
- 验证：可行性检查、对照基准策略、约束违背率、复杂度与时间

### 5) 聚类/分群/画像
适用：无标签分组、模式发现。
- 基线：K-means/层次聚类
- 改进：GMM/DBSCAN（噪声与形状复杂时）
- 验证：轮廓系数/稳定性、可解释的群体差异描述

### 6) 机理/仿真/系统动力学
适用：强调机制解释、情景推演。
- 基线：微分方程/差分方程/系统动力学
- 改进：参数校准 + 不确定性分析；与数据驱动模型对照
- 验证：历史拟合、情景一致性、参数敏感性

## 防跑偏硬规则（必须检查）
- 每一问至少给出一个“可量化输出”和一个“可验证指标/检验方式”
- 模型中的每个关键变量都能在题面/数据里找到定义与单位
- 图表和结论逐问对应，不出现“做了很多但没回答问题”
- 至少一个基线对照：证明你的方法相对简单方案有提升或更合理

## 最终交付（你需要让我生成时，我会给出）
- 可直接粘到论文里的大纲与小节标题（按题目问法编号）
- 评分点对齐表（含你该补的图表/实验清单）
- 每问模型路线：基线 + 改进 + 验证 + 风险与备选

## 默认提示词文件（可复用）
当未提供 `paper_prompt_path` / `paper_prompt_text` 时，默认从以下文件读取论文结构提示词：
- `references/paper_prompt_default.md`

## 目录约定（与项目全局对齐）
- 赛题与附件统一放在 `problem_files/`，补充数据放在 `crawled_data/`。
- 建议把本技能的输出（大纲/评分点对齐/模型路线）归档到 `paper_output/plan/`，供后续生成正文时引用。
- 上面的 `paper_prompts/...` 仅为历史路径示例；当前项目推荐把自定义提示词文件也归档到 `paper_output/plan/`，或直接使用本技能自带的 `references/paper_prompt_default.md`。

## 前后衔接
- 前置：无（拿到题面就能用）。
- 后续：`problem-doc-model-selector`（更细的逐问解析）或回到 `paper-workflow-orchestrator` 继续论文 workflow。

## 约束（必须遵守）

- **Memory Interaction (必做)**:
  - **完成规划后**，必须调用 `context-memory-keeper`，将“论文大纲结构”、“核心评分点”更新到 `memoryskill.md`。
- 本技能必须输出“评分点 → 证据 → 论文位置”的映射清单；后续产文时必须能逐条落到具体章节/图表/表格，否则视为未对齐。
- 若输出中要求“数据预处理/可视化证据”，后续必须调用 `data-cleaning-and-visualization` 产出 `paper_output/figures/`，否则该评分点缺证据。
- 若用户目标是“论文生产完整”，本技能结束后必须明确下一步：进入数据/图表阶段，或回到 `paper-workflow-orchestrator` 继续完整 workflow。
