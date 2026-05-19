---
name: "data-cleaning-and-visualization"
description: "自动清洗赛题或爬取的数据（处理缺失/异常/格式），并生成可视化图表。Invoke when 用户需要处理原始数据、清洗数据或生成数据分析图表。"
---

# 数据清洗与可视化 (Data Cleaning and Visualization)

本技能用于自动处理数学建模中的原始数据，执行标准化的清洗流程，并生成基础的数据探索性分析（EDA）图表。旨在减少手动处理数据的繁琐步骤，快速获取数据的统计特征和分布情况。

## 重要定位：脚本是代码级提示词

数学建模赛题的数据表结构、字段名称、单位口径和图表需求通常都不同，因此本技能的 `scripts/` 不应被理解为所有赛题通用的固定程序。它们的核心价值是提供高质量的数据处理与图表生成样板：包括输入输出目录、清洗步骤、图表尺寸、配色、标注、保存路径和论文引用口径。

真实赛题中，应先分析当前附件的数据格式和建模需求，再引用 `scripts/` 中的写法二次修改，或让 Agent 读取这些脚本后重新生成适配当前赛题的新代码。

## 功能特性

1.  **自动发现数据源**：自动扫描 `problem_files/`（赛题附件）或 `crawled_data/`（爬虫数据）目录。
2.  **智能清洗**：
    -   自动识别并转换数值列。
    -   处理缺失值（数值型填补均值/中位数，分类型填补众数）。
    -   去除全空行/列。
    -   简单的异常值标记/处理。
3.  **自动可视化**：
    -   数值变量：直方图、箱线图。
    -   分类变量：柱状图。
    -   多变量关系：相关性热力图、散点矩阵。
4.  **规范化输出**：所有清洗后的数据和图表统一保存到 `paper_output/` 目录下，方便后续论文写作调用。

## 脚本清单

本技能包含以下核心脚本，位于 `skills/data-cleaning-and-visualization/scripts/` 目录下：

-   `scripts/run_pipeline.py`
    -   **何时用**：用户提供赛题数据或完成爬虫后，需要一键完成清洗和绘图时。这是最常用的入口脚本。
    -   **做什么**：依次调用清洗和绘图脚本，并在 `paper_output/` 下生成完整结果。

-   `scripts/clean_data.py`
    -   **何时用**：只需要清洗数据，不需要绘图，或者需要自定义清洗逻辑时。
    -   **做什么**：读取原始数据，输出清洗后的 CSV/Excel 文件到 `paper_output/data_cleaned/`。

-   `scripts/visualize_data.py`
    -   **何时用**：已有清洗好的数据，需要重新生成图表时。
    -   **做什么**：读取 `paper_output/data_cleaned/` 下的数据，生成图表到 `paper_output/figures/`。

## 输出结构

运行后，将在 `paper_output` 目录下生成以下内容：

```
paper_output/
├── data_cleaned/       # 清洗后的数据文件
│   ├── dataset1_cleaned.csv
│   └── ...
├── figures/            # 生成的可视化图表
│   ├── dataset1/
│   │   ├── dist_column_A.png
│   │   ├── heatmap.png
│   │   └── ...
│   └── ...
```

## 目录约定（与项目全局对齐）

- 输入数据优先放在 `problem_files/`（赛题附件）与 `crawled_data/`（补充/爬虫数据）。
- 本技能只写入 `paper_output/`，不会改动原始数据文件。

## 前后衔接

- 后续通常接：`quality-assurance-auditor`（生成任务清单）→ `paper-micro-unit-generator`（生成与合并）。
- 若要一键跑到论文草稿：直接调用 `paper-workflow-orchestrator`。

## 约束（必须遵守）

- **Memory Interaction (必做)**:
  - **完成清洗后**，必须调用 `context-memory-keeper`，记录“数据质量概况（样本量/缺失情况）”与“关键图表路径”到 `Short-term Workbench`。
- 本技能只允许读取：`problem_files/` 与 `crawled_data/`；只允许写入：`paper_output/`。
- 任何需要在论文中出现的图表，必须从 `paper_output/figures/` 引用，避免散落在根目录或附件目录。
- 若用户目标是“产出完整论文草稿”，本技能结束后必须进入：`quality-assurance-auditor` 或直接回到 `paper-workflow-orchestrator`，否则会出现“有图但无正文/有正文但无任务清单”的断链。
