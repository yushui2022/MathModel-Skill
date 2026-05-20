---
name: "data-cleaning-and-visualization"
description: "自动清洗赛题或爬取的数据（处理缺失/异常/格式），并生成可视化图表。Invoke when 用户需要处理原始数据、清洗数据或生成数据分析图表。"
---

# 数据清洗与可视化 (Data Cleaning and Visualization)

## 执行契约
- 上游输入：优先读取 `paper_output/step1/problem_analysis.json` 与 `paper_output/plan/model_route.json`，并扫描 `problem_files/` 与 `crawled_data/` 中的数据文件。
- 必须输出：`paper_output/plan/data_plan.json`、`paper_output/plan/visualization_plan.json`、`paper_output/figure_index.json`；有可处理数据时同步输出 `paper_output/data_cleaned/` 与 `paper_output/figures/`。
- 下游交接：`quality-assurance-auditor` 读取数据/图表契约补全 `tasks.json`；`paper-micro-unit-generator` 通过任务清单引用图表证据。
- 推荐下一步：完成数据和图表计划后进入 `quality-assurance-auditor` 生成任务清单；完整论文目标应回到 `paper-workflow-orchestrator` 判断后续阶段。
- 失败回退：若没有可处理数据文件，仍尽量根据题意和模型路线生成计划文件；不得把模板图表直接当作最终真实结果。

本技能用于自动处理数学建模中的原始数据，执行标准化的清洗流程，并生成基础的数据探索性分析（EDA）图表。旨在减少手动处理数据的繁琐步骤，快速获取数据的统计特征和分布情况。

## 重要定位：脚本是代码级提示词

数学建模赛题的数据表结构、字段名称、单位口径和图表需求通常都不同，因此本技能的 `scripts/` 不应被理解为所有赛题通用的固定程序。它们的核心价值是提供高质量的数据处理与图表生成样板：包括输入输出目录、清洗步骤、图表尺寸、配色、标注、保存路径和论文引用口径。

真实赛题中，应先分析当前附件的数据格式和建模需求，再引用 `scripts/` 中的写法二次修改，或让 Agent 读取这些脚本后重新生成适配当前赛题的新代码。

## 功能特性

1.  **自动发现数据源**：自动扫描 `problem_files/`（赛题附件）或 `crawled_data/`（爬虫数据）目录。
2.  **数据与图表计划**：生成 `data_plan.json`、`visualization_plan.json` 与 `figure_index.json`，作为后续 QA 和正文生成的图表证据交接单。
3.  **智能清洗**：
    -   自动识别并转换数值列。
    -   处理缺失值（数值型填补均值/中位数，分类型填补众数）。
    -   去除全空行/列。
    -   简单的异常值标记/处理。
4.  **自动可视化**：
    -   数值变量：直方图、箱线图。
    -   分类变量：柱状图。
    -   多变量关系：相关性热力图、散点矩阵。
    -   论文级图表样板：预测对比图、残差分布图、方案/模型对比图、敏感性分析图、权重图、排序图、热力图、聚类散点图。
5.  **规范化输出**：所有清洗后的数据和图表统一保存到 `paper_output/` 目录下，方便后续论文写作调用。

## 脚本清单

本技能包含以下核心脚本，位于 `.claude/skills/data-cleaning-and-visualization/scripts/` 目录下：

-   `scripts/run_pipeline.py`
    -   **何时用**：用户提供赛题数据或完成爬虫后，需要自动完成清洗和绘图时。这是最常用的辅助脚本。
    -   **做什么**：依次生成数据/图表计划、调用清洗和绘图脚本，并在 `paper_output/` 下生成完整结果。

-   `scripts/build_data_visualization_plan.py`
    -   **何时用**：已有 `problem_analysis.json` 或 `model_route.json`，需要先明确“哪些数据支撑哪些问题、哪些图表放在哪里”时。
    -   **做什么**：读取赛题分析、模型路线和现有数据文件，输出 `paper_output/plan/data_plan.json`、`paper_output/plan/visualization_plan.json` 与 `paper_output/figure_index.json`。

-   `scripts/clean_data.py`
    -   **何时用**：只需要清洗数据，不需要绘图，或者需要自定义清洗逻辑时。
    -   **做什么**：读取原始数据，输出清洗后的 CSV/Excel 文件到 `paper_output/data_cleaned/`。

-   `scripts/visualize_data.py`
    -   **何时用**：已有清洗好的数据，需要重新生成图表时。
    -   **做什么**：读取 `paper_output/data_cleaned/` 下的数据，生成基础 EDA 图表到 `paper_output/figures/`。

-   `scripts/paper_figure_templates.py`
    -   **何时用**：Agent 需要生成论文级图表代码时，优先读取本文件作为代码样板。
    -   **做什么**：提供预测对比、残差分布、模型/方案对比、敏感性分析、指标权重、综合得分排序、热力图、散点图等函数模板。

-   `scripts/generate_paper_figures_from_plan.py`
    -   **何时用**：已有 `visualization_plan.json` 和清洗后的 CSV，希望先生成一版论文级图表草稿时。
    -   **做什么**：按图表计划调用 `paper_figure_templates.py`，把计划图生成到 `paper_output/figures/fig_*.png`，并更新 `paper_output/figure_index.json`。

## 输出结构

运行后，将在 `paper_output` 目录下生成以下内容：

```
paper_output/
├── plan/
│   ├── data_plan.json       # 数据字段、清洗任务与子问题链接
│   └── visualization_plan.json # 建议图表、图题、用途与输出路径
├── figure_index.json        # 图表计划索引，供 QA 和正文生成核对
├── data_cleaned/       # 清洗后的数据文件
│   ├── dataset1_cleaned.csv
│   └── ...
├── figures/            # 生成的可视化图表
│   ├── fig_q1_1.png     # 按 visualization_plan 生成的论文级图表草稿
│   ├── fig_q1_2.png
│   ├── dataset1/
│   │   ├── dist_column_A.png
│   │   ├── heatmap.png
│   │   └── ...
│   └── ...
```

## 目录约定（与项目全局对齐）

- 输入数据优先放在 `problem_files/`（赛题附件）与 `crawled_data/`（补充/爬虫数据）。
- 本技能只写入 `paper_output/`，不会改动原始数据文件。
- `data_plan.json` 与 `visualization_plan.json` 是交接单，不是固定代码。Agent 应根据它们和当前附件结构二次生成或修改真实建模代码。
- `paper_figure_templates.py` 生成的是论文图表代码样板。若当前赛题已经有真实模型输出，应优先把真实结果表接入这些模板，而不是直接把模板图当最终结果。

## 前后衔接

- 后续通常接：`quality-assurance-auditor`（生成任务清单）→ `paper-micro-unit-generator`（生成与合并）。
- 若要继续到论文草稿：回到 `paper-workflow-orchestrator`。

## 约束（必须遵守）

- **Memory Interaction (必做)**:
  - **完成清洗后**，必须调用 `context-memory-keeper`，记录“数据质量概况（样本量/缺失情况）”与“关键图表路径”到 `Short-term Workbench`。
- 本技能只允许读取：`problem_files/` 与 `crawled_data/`；只允许写入：`paper_output/`。
- 任何需要在论文中出现的图表，必须从 `paper_output/figures/` 引用，避免散落在根目录或附件目录。
- 若用户目标是“产出完整论文草稿”，本技能结束后必须进入：`quality-assurance-auditor` 或直接回到 `paper-workflow-orchestrator`，否则会出现“有图但无正文/有正文但无任务清单”的断链。
