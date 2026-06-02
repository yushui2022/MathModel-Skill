---
name: "problem-doc-model-selector"
description: "解析赛题PDF/Word，抽取任务与数据条件并给出模型选型与验证路线。Invoke when用户提供赛题文档或题目文本，需要确定采用何模型/方法。"
---

# 赛题文档自动解析与模型选型

## 全局流程协作约束（长对话防漂移）

- 本 skill 不得作为孤立入口。用户要求完整论文、生成 Word、继续流程或不确定阶段时，先回到 `paper-workflow-orchestrator` 判断当前 S0-S8 阶段。
- 启动或继续本 skill 的正式任务前，必须运行：
  ```bash
  python skills/paper-workflow-orchestrator/scripts/workflow_guard.py --skill problem-doc-model-selector
  ```
- 如果输出 `[WORKFLOW FAIL]` 或报告 `status != "PASS"`，停止本 skill，按 `paper_output/qa/workflow_guard_report.json` 的失败项回补前置阶段，不得凭记忆继续。
- 本 skill 只写入自己契约范围内的 `paper_output/` 产物；完成后必须回到 `paper-workflow-orchestrator` 判断下一步，并用 `context-memory-keeper` 记录已完成产物、阻塞项和下一步。
- 长对话中如果上下文变长、阶段不确定或用户分开调用 skill，先运行：
  ```bash
  python skills/paper-workflow-orchestrator/scripts/workflow_guard.py --status
  ```
  再读取 `paper_output/qa/workflow_guard_report.json`、`paper_output/preflight_report.json`、`paper_output/input_manifest.json`、`paper_output/results/run_manifest.json` 和本 skill 的上游 JSON 契约，按报告里的 `recommended_skill` 与 `next_action` 继续。
- 继续流程前，必须把 `paper_output/context/workflow_memory.json` 视为长期断点记录；若其中的 `current_step`、`next_step`、`recommended_skill` 与 `workflow_guard.py --status` 不一致，以 guard 报告为准。
- 每次完成本 skill 的产物后，先回到 `paper-workflow-orchestrator` 或运行 `workflow_guard.py --status`，再更新 workflow memory：
  ```bash
  python skills/context-memory-keeper/scripts/update_workflow_memory.py
  ```
  更新后读取 `paper_output/context/workflow_memory.json` / `.md`，确认下一步和推荐 skill 已记录。

## 执行契约
- 上游输入：`problem_files/` 中的赛题 PDF/Word/TXT 和附件数据。
- 必须输出：`paper_output/step1/problem_analysis.json`，以及 `A_题意对齐.md`、`B_论文大纲.md`、`C_评分点对齐表.md`、`D_模型路线.json`。
- 下游交接：`modeling-paper-rubric-and-model-selector` 读取 `problem_analysis.json` 生成模型路线；完整 workflow 由 `paper-workflow-orchestrator` 串联。
- 推荐下一步：完成题意分析后进入 `modeling-paper-rubric-and-model-selector`；如果用户目标是完整论文，回到 `paper-workflow-orchestrator` 判断后续阶段。
- 失败回退：若 `problem_files/` 为空，应停止并提示补齐赛题；若部分文档无法解析，保留可解析内容并在输出中记录字段画像缺失。

## 目标
- 输入赛题 PDF/Word 文档或题面文本，自动抽取“每一问”的任务类型、数据条件与约束，并输出贴题的模型选型与验证路线。
- 生成评分友好型交付：一页纸题意对齐、论文大纲、评分点对齐表、模型路线（基线/改进/验证/风险）。


## 阶段流转
- 解析完成后，不要停留在“是否满意”的泛泛询问；应说明已生成的题意契约，并给出下一推荐阶段。
- 若用户意图是完整论文，在输出 A/B/C/D 后回到 `paper-workflow-orchestrator`，由总入口决定继续生成模型路线、数据计划、QA 和正文。
- **拒绝偷懒**: 必须输出完整的 A/B/C/D 四部分，不得省略。

## 适用时机
- 用户提供赛题 PDF/Word 或题面文本，需要快速判断各问应采用的模型/方法并制定实验验证计划时。
- 对题意理解不确定、模型路线拿不准或需要论文结构与评分点对齐建议时。

## 输入
- 赛题文档路径或题面全文（支持 PDF、DOCX、TXT）。
- 可选：附件数据文件路径、你希望强调的亮点或限制。

## 输出
- A 一页纸题意对齐：逐问给出输入/输出、评价指标、关键约束、可验证方式。
- B 论文大纲：摘要、问题重述、假设、符号、数据说明、模型、求解、结果、检验、结论、不足、参考。
- C 评分点对齐表：评分点 → 证据形式（图表/实验/检验）→ 论文位置。
- D 模型选型与路线：每问的任务类型、最小可用基线、改进路线、验证计划、风险与备选。
- E 数据需求配置 (可选)：若发现题目需要外部数据（如人口、气象、经济数据），自动生成或更新根目录下的 `data_requirements.json`，以便 `authoritative-data-harvester` 自动获取。
- 机器可读契约：`paper_output/step1/problem_analysis.json`，包含 `documents`、`data_files`、`questions`、`recommended_models`、`validation_plan`、`figure_suggestions` 等字段，供 QA、微单元生成和总编排器继续读取。

## 目录约定（与项目全局对齐）
- 赛题与附件统一放在 `problem_files/`。
- 建议把本技能的四类输出归档到 `paper_output/step1/`（例如 `paper_output/step1/A_题意对齐.md` 等），便于后续技能引用。
- 同步生成 `paper_output/step1/D_模型路线.json`，用于保留每一问的模型路线、验证方式和建议图表。

## 脚本入口（推荐）
本 skill 已内置结构化分析脚本：

```bash
python skills/problem-doc-model-selector/scripts/analyze_problem.py
```

该脚本会扫描 `problem_files/`，读取 TXT/Markdown/DOCX/PDF 赛题文本，并对 CSV/XLSX/XLS 附件做轻量字段画像。成功后会写入 `paper_output/step1/problem_analysis.json`，后续 `quality-assurance-auditor` 会优先用它生成动态 `tasks.json`。

## 前后衔接
- 后续通常先做：`data-cleaning-and-visualization`（数据清洗与可视化）。
- 若要继续到论文草稿：回到 `paper-workflow-orchestrator`。

## 约束（必须遵守）

- **Memory Interaction (必做)**: 
  - **开始前**，检查 `memoryskill.md` 中是否有外部文献/数据索引（如 g-sci 提供的参考文献），将其纳入模型选型依据。
  - **完成解析后**，必须调用 `context-memory-keeper`，将“核心任务类型”、“数据条件”与“模型选型结论”更新到 `memoryskill.md` 的 `Short-term Workbench` 中。这是后续产文技能获取上下文的关键。
- **外部数据检查 (必做)**:
  - 若解析发现题目依赖外部公开数据（如“搜集相关数据”、“附件数据不足”），必须生成 `data_requirements.json` 并写入根目录。
  - 配置内容应包含明确的 `url`（若已知）或 `manual_search` 提示，并将 `active` 设为 `true`。
- 本技能输出的题意对齐与模型路线，必须能被后续写作定位引用；建议固定归档到 `paper_output/step1/`。
- 若用户目标是“最终论文可提交”，本技能完成后不得直接进入产文阶段，必须先保证数据口径可用：进入 `data-cleaning-and-visualization` 或补充 `authoritative-data-harvester`。
- 若用户不想分步推进，必须回到 `paper-workflow-orchestrator` 执行完整 workflow，避免“解析完成但未生成正文”的断档。

## 工作流程
1. 文档读取
   - PDF：优先 PyMuPDF，否则 pdfplumber；保留图表标题与小节编号。
   - Word：python-docx；保留段落与表格结构。
   - 清理：去页眉页脚、合并断行、标准化单位（cm⁻¹、% 等）。
2. 题意解析
   - 规则抽取“问题1/问题2/问题3…”与“附件说明/单位/关键参数”。
   - 识别任务类型：预测/分类/评价/优化/聚类/仿真/机理建模。
   - 提取约束与边界：入射角、层次关系、单位口径、可行域。
3. 数据条件解析
   - 附件文件名与字段：列名、单位、样本量、范围、缺失值比例。
   - 结果口径：需要反射率、厚度、误差、排名或资源分配等。
4. 模型选型引擎（规则优先，结合提示式决策）
   - 预测类：移动平均/指数平滑/回归/ARIMA → 树模型/LSTM。
   - 分类类：逻辑回归/朴素贝叶斯 → 随机森林/梯度提升，不平衡用代价敏感。
   - 评价与排序：规范化+加权和 → 熵权/CRITIC/AHP/TOPSIS/VIKOR。
   - 优化与调度：线性/整数规划 → 多目标与启发式（遗传/退火）。
   - 聚类：K-means/层次 → GMM/DBSCAN（噪声与非凸形状）。
   - 机理/仿真：微分/差分/系统动力学；与数据驱动对照。
   - 物理/工程建模：根据领域知识建立方程（如热传导、流体力学、电路分析、光学传播），利用最小二乘或优化算法进行参数反演与模型修正。
5. 验证与鲁棒性
   - 指标：RMSE/MAE/AUC/F1/MAPE/轮廓系数/约束满足率。
   - 交叉验证/滚动回测/留出法；消融实验与敏感性分析。
   - 极端/边界情景与单位口径一致性检查。

## 判别逻辑速查
- 出现“预测/估计未来/趋势/参数估计”→ 预测类。
- 出现“分类/是否/风险等级/识别”→ 分类类。
- 出现“综合评价/排序/权重/打分”→ 评价与排序。
- 出现“资源分配/路径/选址/成本最小/收益最大”→ 优化与调度。
- 出现“分群/画像/相似性/模式发现”→ 聚类。
- 出现“机理/仿真/动力学/微分方程”→ 机理/仿真。
- 出现“物理过程/化学反应/信号传输/力学结构”→ 物理/工程建模。

## 输出模板
- A 题意对齐：逐问输入、输出、指标、约束、验证。
- B 大纲：按评分友好顺序列出章节与小节。
- C 评分对齐：评分点与证据映射表。
- D 模型路线：任务类型/基线/改进/验证/风险与备选。

## 使用示例
- 输入：赛题文件路径 `c:\path\to\赛题.pdf` 或题面文本全文。
- 行为：读取文档→抽取每问→识别任务类型与数据条件→输出 A/B/C/D 四类结果与建议模型。
- 自动建议：
  - 基线：选择最简单的经典模型（如线性回归、K-means、最短路算法）。
  - 改进：针对基线不足（如非线性、噪声、多目标）引入的高阶模型（如XGBoost、改进遗传算法、混合模型）。
  - 验证：指标计算、残差分析、交叉验证、灵敏度分析。

## 防跑偏检查
- 每问必须给出可量化输出与可验证指标。
- 符号与单位统一，指标口径一致。
- 至少一个基线对照与改进证据（提升或更合理）。
- 结论与图表逐问对应，不“做很多但没回答问题”。

## 何时不要用本技能
- 已经明确只需实现某个具体算法或改动单一代码片段时（直接实现更快）。
