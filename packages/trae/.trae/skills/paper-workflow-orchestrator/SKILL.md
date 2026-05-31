---
name: "paper-workflow-orchestrator"
description: "MathModel Skill 总入口。触发词：数学建模、生成论文、分析赛题、CUMCM、MathorCup、华数杯、美赛、ICM、MathModel。任何数学建模任务先读本 skill 再路由子 skill。"
---

# 论文生成全流程编排器

## 启动门（必须第一步执行）

进入任何后续步骤之前，**必须**用 Bash 运行预检脚本：

```bash
python .trae/skills/paper-workflow-orchestrator/scripts/preflight_check.py
```

读取退出码和 `paper_output/preflight_report.json`：

- 退出码非 0 或 `status != "PASS"` → **立刻停止生成任何内容**。把报告中的 `errors` 原文反问用户，等用户修复 `problem_files/` 后重新运行预检；
- 不允许跳过预检；不允许"先凑合写一稿"；不允许凭印象判断附件状态；
- 预检通过后，按下方阶段路由表逐步推进。

## Quickstart 用途说明

`scripts/quickstart_run.py` 仅用于安装验证。它产出的占位草稿写入 `paper_output/quickstart/`，并写入名为 `quickstart_draft.docx` 的草稿文件，**不会**通过证据门禁，不得对外宣称为最终稿。

正式赛题任务禁止调用 quickstart。若用户说"先快速看个样子"，先反问："你需要正式稿还是只验证安装？" 不要默认走 quickstart。

`scripts/run_all.py` 是已废弃命令的兼容提示，仅用于保护旧文档/旧脚本调用者，正式流程不再调用。

## 执行契约
- 上游输入：`problem_files/` 中的赛题与附件数据；可选读取 `crawled_data/` 中的补充权威数据。
- 必须输出：`paper_output/OUTPUT_LAYOUT.md`、`problem_analysis.json`、`model_route.json`、`rubric_alignment.json`、`scoring_strategy.md`、数据/图表计划、结果证据、证据门禁报告、`paper_outline.json`、`final_paper_source.md`、`final_paper.docx` 与格式检查报告。
- 下游交接：本技能是总入口，负责判断当前阶段并路由到其他 skill；用户不知道从哪个 skill 开始时优先调用它。
- 失败回退：`problem_files/` 为空时阻塞；模型路线、数据计划或图表生成失败时打印 warning 并继续，让 QA 按可用契约回退。

## 目标
- 本技能是正式入口，不是“一键脚本说明书”。正式赛题应由 Agent 先读题、拆题、判断附件性质，再生成或修改当前赛题专用代码，运行真实结果，最后基于完整证据链全局写作。
- 保持本项目的核心思路：以 skill 为主线，把“赛题解析 → 模型选择 → 数据处理 → 结果证据 → QA 门禁 → Agent 全局写作 → 最终 QA”串成一套可执行工作流。
- `scripts/quickstart_run.py` 只用于 quickstart、安装验证和 smoke test；它生成的是验证草稿，不代表正式比赛论文质量。
- `scripts/run_all.py` 已废弃，只保留迁移提示，不再作为正式论文或 quickstart 的执行入口。

## 入口路由规则
- 当用户说“开始生成数学建模论文”“帮我做这个数学建模题”“分析赛题”“使用 MathModel Skill”或不知道该调用哪个 skill 时，先读取本技能。
- 先判断用户目标：正式论文走 Agent-native 全流程；只要题意、模型、数据、QA 或正文时，路由到对应子 skill。
- 不要让用户理解或选择多个 skill 的顺序；由本技能负责说明下一阶段，并在阶段完成后回到本技能判断下一步。
- 如用户只是验证安装或跑 quickstart，可调用：
  - `python .trae/skills/paper-workflow-orchestrator/scripts/quickstart_run.py`
- 正式赛题不要先跑 quickstart 脚本；应先读取题面和附件，再按当前赛题生成专用数据处理、建模和绘图代码。

## 阶段路由表
| 当前目标 | 优先调用 |
|---|---|
| 刚开始、只给了赛题或不知道用哪个 skill | `problem-doc-model-selector` |
| 已有 `problem_analysis.json`，需要模型路线和评分闭环 | `modeling-paper-rubric-and-model-selector` |
| 需要外部权威数据 | `authoritative-data-harvester` |
| 需要处理附件数据、生成数据/图表计划或图表样板 | `data-cleaning-and-visualization` |
| 需要生成模型结果、评价指标、结论和表格证据 | `model-code-and-result-generator` |
| 进入正文生成前，需要任务清单和门禁检查 | `quality-assurance-auditor` |
| 证据门禁通过，需要正式成稿、规范格式、Word 排版 | `paper-formal-writer` |
| 需要微单元提示词资产、局部扩写或低能力模型兜底草稿 | `paper-micro-unit-generator` |
| 已有 `final_paper_source.md` 或 `final_paper.docx`，需要最终把关 | `quality-assurance-auditor` + `paper-formal-writer` |

## 适用时机
- 用户已经在项目根目录下按约定放好了赛题 PDF/Word 和附件数据，需要“从零到万字论文”的一条龙自动流程时。
- 已经完成部分计算或占位符填充，但希望检查整体步骤是否完整、顺序是否合理，或想重跑核心流程时。

## 约束（必须遵守）

- **Memory Interaction (必做)**:
  - **全流程中**：作为总控，应当在每个关键步骤（清洗完、QA完、生成完）结束后，主动调用 `context-memory-keeper` 更新进度，确保如果流程中断，Memory 中留有断点记录。
- 本技能是全项目唯一“入口路由 skill”。用户只要提出“生成完整论文/跑完整流程”，优先读取本技能而不是让多个技能分散运行。
- 若 `problem_files/` 为空，必须先补齐赛题与附件数据，再运行流程。
- 当前赛题专用代码必须写入 `paper_output/code/`：数据处理放 `data_processing/`，绘图放 `visualization/`，建模放 `modeling/`，检查放 `qa/`。不要把 `q1_model.py`、绘图脚本或清洗脚本写回 `skills/*/scripts/`。
- 必须先判断附件性质：原始数据、结果模板、说明文档、参考材料要分开处理。像官方要求填写的 `result*.xlsx` 结果模板，不能被当作原始输入数据机械清洗，也不能据此伪造真实建模结果。
- 当任一子问题的 `evidence_status` 为 `missing`、`needs_real_modeling` 或 `scaffold_result_needs_review` 时，不得把 Word 称为最终稿；必须先补齐赛题专用代码、真实图表、表格、指标和结论。
- 若用户分开调用了其他技能，最终仍应回到本技能或按本技能的顺序完成：清洗与出图 → QA 任务清单 → 微单元生成 → 合并。

## 正式交付门禁标准（以此判断是否“论文生产完整”）

- **必须通过：`quality-assurance-auditor/scripts/evidence_gate.py` 的 official 模式**
- **必须通过：`paper-formal-writer/scripts/check_paper_format.py` 的正式格式门禁**
- 必须存在：`paper_output/final_paper.docx`，但只有证据门禁和格式门禁都通过后才能称为正式稿。
- 必须存在：`paper_output/OUTPUT_LAYOUT.md`（当前项目输出位置说明）
- 必须存在：`paper_output/plan/paper_outline.json`（正式论文大纲契约）
- 必须存在：`paper_output/final_paper_source.md`（Agent 全局写作的正式 Markdown 源稿）
- 必须存在：`paper_output/step1/problem_analysis.json`（结构化题意分析）
- 必须存在：`paper_output/plan/model_route.json`（模型路线契约）
- 必须存在：`paper_output/plan/rubric_alignment.json`（评分点映射契约）
- 必须存在：`paper_output/plan/data_plan.json` 与 `visualization_plan.json`（数据与图表证据链契约）
- 必须存在：`paper_output/figure_index.json`（图表计划索引）
- 推荐存在：`paper_output/results/model_results.json`、`metrics.json`、`conclusions.json`（结果证据契约）
- 推荐存在：`paper_output/tables/table_index.json` 与 `paper_output/tables/`（论文表格证据）
- 推荐存在：`paper_output/code/README.md` 与 `paper_output/code/*/README.md`（当前赛题代码工作区说明）
- 推荐存在：`paper_output/tasks.json`
- 推荐存在：`paper_output/ref_check.md`
- 推荐存在：`paper_output/micro_units/`（作为提示词资产和验证草稿，不作为正式主流程）
- 建议存在：`paper_output/figures/` 与 `paper_output/data_cleaned/`（用于数据预处理与结果分析配图）

## 脚本清单（本技能实际会用到的）
- `scripts/prepare_output_layout.py`：输出位置准备器。
  - 何时用：完整流程开始前、quickstart、安装验证或用户问“代码/图表/微单元放哪里”时。
  - 做什么：创建 `paper_output/OUTPUT_LAYOUT.md`、`paper_output/code/`、`data_cleaned/`、`figures/`、`tables/`、`results/`、`micro_units/` 等目录，并写入代码工作区 README。
- `scripts/quickstart_run.py`：quickstart / smoke test 执行器。
  - 何时用：quickstart、安装验证、调试，或用户明确要求只验证 workflow 链路。
  - 做什么：先准备输出目录规划 → 再跑 `problem-doc-model-selector/scripts/analyze_problem.py` 生成 `problem_analysis.json` → 再跑 `modeling-paper-rubric-and-model-selector/scripts/build_model_route.py` 生成模型路线与评分点契约 → 再生成数据/图表证据链契约并做清洗与可视化 → 再生成模型结果、指标、结论和表格证据契约 → 再跑 QA 生成动态 `paper_output/tasks.json` → 再离线生成微单元 → 再合并成 `paper_output/final_paper.md` 和 `paper_output/final_paper.docx`。
  - 注意：输出是验证草稿，不代表正式比赛论文。
- `scripts/run_all.py`：废弃迁移提示。
  - 何时用：旧命令误触时提示用户改用 `quickstart_run.py` 或正式 Agent-native workflow。
  - 做什么：只打印迁移提示，不执行生成流程。

## 前置约定
- 目录结构建议为：
  - 根目录：`<项目根目录>`
  - 赛题与附件：`problem_files/`（把赛题 PDF/Word 与附件数据直接放这里；QA 会检查该目录不为空）
  - 补充数据：`crawled_data/`（可选，爬虫或外部公开数据放这里）
  - 输出目录：`paper_output/`（脚本自动生成任务清单、微单元与合并稿）
  - 当前赛题专用代码：`paper_output/code/`（只放当前题目的数据处理、绘图、建模和检查代码）
  - 技能目录：`skills/...`
- Python 可用即可。

## 输入
- 必填：
  - 将赛题 PDF/Word 与附件数据放入 `problem_files/`。
- 可选：
  - 将补充数据放入 `crawled_data/`。

## 输出
- 中间文件：
  - `paper_output/OUTPUT_LAYOUT.md`：当前项目输出位置说明。
  - `paper_output/code/README.md`：当前赛题专用代码工作区说明。
  - `paper_output/code/data_processing/`：当前赛题数据处理代码。
  - `paper_output/code/visualization/`：当前赛题绘图和格式化图表代码。
  - `paper_output/code/modeling/`：当前赛题 q1/q2/q3 建模代码。
  - `paper_output/code/qa/`：可选的当前赛题检查代码。
  - `paper_output/step1/problem_analysis.json`：结构化赛题分析，连接后续 QA 与正文生成。
  - `paper_output/step1/A_题意对齐.md`、`B_论文大纲.md`、`C_评分点对齐表.md`、`D_模型路线.json`。
  - `paper_output/plan/model_route.json`：每一问的模型路线、验证计划和建议图表。
  - `paper_output/plan/rubric_alignment.json`：评分点与证据映射。
  - `paper_output/plan/scoring_strategy.md`：评分闭环说明。
  - `paper_output/plan/data_plan.json`：数据文件、字段画像、清洗任务与子问题链接。
  - `paper_output/plan/visualization_plan.json`：建议图表、图题、用途、候选字段与输出路径。
  - `paper_output/figure_index.json`：图表计划索引，供 QA 和正文引用核对。
  - `paper_output/results/model_results.json`：每问模型输出、参数、方案或预测结果的证据契约。
  - `paper_output/results/metrics.json`：每问评价指标、误差、得分或约束满足情况。
  - `paper_output/results/conclusions.json`：每问可回扣原题的结构化结论。
  - `paper_output/tables/table_index.json`：论文表格索引、表题、用途和路径。
  - `paper_output/tasks.json`：微单元任务清单。
  - `paper_output/micro_units/*.txt`：每个微单元一个文件。
  - `paper_output/generate_log.json`：生成日志。
- 最终交付：
  - `paper_output/final_paper.md`：合并后的 Markdown 论文草稿。
  - `paper_output/final_paper.docx`：Word 草稿，作为主要交付物。
  - `paper_output/ref_check.md`：交叉引用与编号断链报告。

## 工作流程（对应 workflow_full 分步）

### 正式实现：Agent-native 工作流（推荐）
0. 读取赛题与附件，判断附件是原始数据、结果模板、说明文档还是参考材料。
1. 生成题意分析、模型路线、评分闭环、数据计划和图表计划。
2. 在 `paper_output/code/` 中生成或修改当前赛题专用数据处理、建模和绘图代码。
3. 运行专用代码，产出真实图表、表格、指标、结论，并写回 `paper_output/results/` 与 `paper_output/tables/`。
4. 运行 `quality-assurance-auditor/scripts/evidence_gate.py`；未通过时继续补证据，不进入正式成稿。
5. 证据门禁通过后，运行 `paper-formal-writer/scripts/build_paper_outline.py` 生成 `paper_output/plan/paper_outline.json`。
6. Agent 读取 `paper_outline.json`、完整证据链和提示词资产，全局撰写 `paper_output/final_paper_source.md`。
7. 运行 `paper-formal-writer/scripts/format_formal_docx.py` 生成正式 Word，再运行 `paper-formal-writer/scripts/check_paper_format.py`。
8. 证据门禁与格式门禁均通过后，再次调用 `quality-assurance-auditor` 做最终一致性检查。

### Quickstart 验证流程（不是正式论文生产流程）
0. **输出目录规划**:
   - 调用 `paper-workflow-orchestrator/scripts/prepare_output_layout.py`，生成 `paper_output/OUTPUT_LAYOUT.md` 和 `paper_output/code/` 工作区说明。
   - 这一步只建立落点规范，不执行黑盒建模。
1. **赛题结构化分析**:
   - 调用 `problem-doc-model-selector/scripts/analyze_problem.py`，生成 `paper_output/step1/problem_analysis.json`。
   - 将每一问的任务类型、推荐模型、验证计划和建议图表固化为后续 skill 可读取的数据契约。
2. **模型路线与评分闭环**:
   - 调用 `modeling-paper-rubric-and-model-selector/scripts/build_model_route.py`，生成 `paper_output/plan/model_route.json`、`rubric_alignment.json` 和 `scoring_strategy.md`。
   - 若该步骤失败，流程继续，QA 回退到 `problem_analysis.json`。
3. **外部资源获取 (Optional)**:
   - 调用 `authoritative-data-harvester` 或 `g-sci` (若存在) 填充 `crawled_data/`。
   - **Memory Update**: 将获取的文献/数据源更新至 `memoryskill.md`。
4. 调用 `data-cleaning-and-visualization/scripts/run_pipeline.py`：先生成 `data_plan.json`、`visualization_plan.json` 与 `figure_index.json`，再扫描 `problem_files/` 与 `crawled_data/`，产出清洗数据与图表到 `paper_output/`。
5. 调用 `model-code-and-result-generator/scripts/build_result_contracts.py`：根据模型路线、清洗数据和图表计划生成 `model_results.json`、`metrics.json`、`conclusions.json` 与 `table_index.json`。真实赛题中应继续让 Agent 在 `paper_output/code/modeling/` 二次生成或修改专用建模代码，并补齐真实结果。
6. 调用 `quality-assurance-auditor/scripts/pipeline.py`：检查 `problem_files/`，优先根据模型路线、评分点、数据图表和结果证据生成动态 `paper_output/tasks.json`。
7. 调用 `paper-micro-unit-generator/scripts/generate_all_offline.py`：生成 `paper_output/micro_units/*.txt` 与 `paper_output/generate_log.json`。
8. 调用 `paper-micro-unit-generator/scripts/merge.py`：生成 `paper_output/final_paper.md` 与 `paper_output/ref_check.md`，**并直接生成 `paper_output/final_paper.docx`**。
9. **[Mandatory] Word 交付验证**:
   - 检查 `paper_output/final_paper.docx` 是否存在。
   - 优先使用 `scripts/merge.py` 直接生成的 Word 版本（原生 python-docx 生成，不依赖 Pandoc）。
   - 仅在直接生成失败时，才尝试调用 Pandoc 作为兜底方案。
   - 确保公式、图表、目录在 Word 中显示正常。

### 分步运行（需要时才用）

0. **外部资源获取**:
   - 若需要补充文献或数据，先运行 `authoritative-data-harvester` 或其他搜索技能。

0.5. 仅准备输出目录规划：
```bash
python .trae/skills/paper-workflow-orchestrator/scripts/prepare_output_layout.py
```

1. 仅做数据清洗与可视化：
```bash
python .trae/skills/data-cleaning-and-visualization/scripts/run_pipeline.py
```

1.5. 仅生成结果证据契约：
```bash
python .trae/skills/model-code-and-result-generator/scripts/build_result_contracts.py
```

2. 仅做赛题结构化分析：
```bash
python .trae/skills/problem-doc-model-selector/scripts/analyze_problem.py
```

3. 仅生成模型路线与评分闭环：
```bash
python .trae/skills/modeling-paper-rubric-and-model-selector/scripts/build_model_route.py
```

4. 仅生成任务清单（会检查 `problem_files/` 不为空，并优先读取 `model_route.json`）：
```bash
python .trae/skills/quality-assurance-auditor/scripts/pipeline.py
```

5. 仅生成微单元：
```bash
python .trae/skills/paper-micro-unit-generator/scripts/generate_all_offline.py
```

6. 仅合并生成论文：
```bash
python .trae/skills/paper-micro-unit-generator/scripts/merge.py
```

7. 仅生成正式论文大纲契约：
```bash
python .trae/skills/paper-formal-writer/scripts/build_paper_outline.py
```

8. 仅格式化正式 Word：
```bash
python .trae/skills/paper-formal-writer/scripts/format_formal_docx.py
```

9. 仅检查正式论文格式：
```bash
python .trae/skills/paper-formal-writer/scripts/check_paper_format.py
```

## 常见问题

- 报错“problem_files 为空”：把赛题 PDF/Word 与附件数据放进 `problem_files/` 后重跑。
- 想要看题意拆解：查看 `paper_output/step1/problem_analysis.json` 和 `paper_output/step1/A_题意对齐.md`。
- 想要看模型路线：查看 `paper_output/plan/model_route.json` 和 `paper_output/plan/scoring_strategy.md`。
- 想要看论文产出：最终文件是 `paper_output/final_paper.docx`，中间稿是 `paper_output/final_paper.md`。
- 想要看输出位置规划：查看 `paper_output/OUTPUT_LAYOUT.md`。
- 想要看赛题专用代码：查看 `paper_output/code/`，不要到 skill 包目录里找当前赛题代码。
- 想要看数据与图表：清洗数据在 `paper_output/data_cleaned/`，图表在 `paper_output/figures/`。
- 想要看结果证据：查看 `paper_output/results/` 与 `paper_output/tables/table_index.json`；其中草稿状态的结果需要结合真实建模代码补齐。
