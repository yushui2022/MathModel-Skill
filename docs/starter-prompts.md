# Starter Prompts

本页给用户复制即可用的启动提示词。普通使用时，不需要手动选择多个 skill；让 Agent 先进入总控 skill，再由总控路由到后续阶段。

## 正式论文流程（推荐）

```text
我已经把赛题 PDF/Word 和附件数据放进 problem_files/。
请使用 MathModel Skill，从 paper-workflow-orchestrator 开始。
不要先跑 quickstart 脚本。请读取赛题和附件，生成模型路线，判断附件是原始数据还是结果模板，在 paper_output/code/ 中生成并运行当前赛题专用代码，产出真实图表、表格、指标和结论。
证据门禁通过后，请调用 paper-formal-writer 生成 paper_output/plan/paper_outline.json，再基于完整证据链全局撰写 paper_output/final_paper_source.md。篇幅使用 outline 按子问题数量生成的动态目标，标题采用 1 / 1.1 / 1.1.1，禁止复制或近义改写凑字数。
写完后运行 format_formal_docx.py 生成含可编辑 Word 原生公式的 paper_output/final_paper.docx，再运行 check_paper_format.py --render required。证据门禁和格式门禁未同时通过时，不要把当前 Word 称为最终稿。
写作时可以引用 paper-micro-unit-generator 中保留的微单元提示词资产，但不要机械拼接，要按当前题目的模型、结果和评分点整体成文。
注意：skills 里的 scripts 是样板和代码级提示词，遇到真实赛题数据时，请先读取这些脚本，再根据当前字段、单位、指标和图表需求二次生成或修改专用代码。
当前赛题专用代码统一写入 paper_output/code/，不要写回 .trae/skills/、.claude/skills/ 或 skills/。
JSON 文件是 skill 之间的结构化交接单，不是平台内置标准；请把关键结论沉淀到 paper_output/ 中再进入下一阶段。
```

## 安装验证

```text
我想验证 MathModel Skill 是否安装成功。请先读取 paper-workflow-orchestrator，然后使用 examples/quickstart/problem_files/ 或当前 problem_files/ 跑通 quickstart。
请运行对应平台的 quickstart_run.py。验证目标是生成 problem_analysis.json、model_route.json、data_plan.json、model_results.json、tasks.json、final_paper.md 和 final_paper.docx。
注意：quickstart 输出只是验证草稿，不代表正式比赛论文质量。
```

## 只做赛题解析

```text
请使用 MathModel Skill 只完成赛题结构化分析。
从 paper-workflow-orchestrator 开始，路由到 problem-doc-model-selector，读取 problem_files/ 中的赛题和附件，输出 paper_output/step1/problem_analysis.json。
不要直接进入正文生成。
```

## 只做模型路线

```text
请基于已有的 paper_output/step1/problem_analysis.json 生成模型路线与评分闭环。
调用 modeling-paper-rubric-and-model-selector，输出 model_route.json、rubric_alignment.json 和 scoring_strategy.md。
重点说明每一问为什么选这个模型、需要哪些公式、指标、图表和评分证据。
```

## 只做数据与图表

```text
请基于 problem_files/、crawled_data/ 和已有模型路线，完成数据清洗与图表计划。
调用 data-cleaning-and-visualization，输出 data_plan.json、visualization_plan.json、figure_index.json、data_cleaned/ 和 figures/。
请把 scripts 中的绘图代码当作高质量格式样板，根据当前赛题字段二次修改，不要机械套用固定列名。
数据处理代码写入 paper_output/code/data_processing/；绘图代码写入 paper_output/code/visualization/；格式化图表图片写入 paper_output/figures/。
```

## 只补结果证据

```text
请补齐结果证据层。
读取 model_route.json、data_plan.json、visualization_plan.json 和 paper_output/data_cleaned/，调用 model-code-and-result-generator，生成或更新 model_results.json、metrics.json、conclusions.json 和 table_index.json。
如果当前还没有真实建模代码，请在 paper_output/code/modeling/ 生成 q1/q2/q3 建模代码脚手架，并明确标记真实数值需要结合当前赛题专用代码补齐。
后续请先复核或修改 q*_model.py，再运行 python paper_output/code/modeling/run_modeling.py，把结果写回 results/ 与 tables/。
```

## 只做 QA 任务清单

```text
请进入质量审计阶段。
调用 quality-assurance-auditor，优先读取模型路线、评分点、数据图表计划、结果证据和表格索引，生成 paper_output/tasks.json。
请检查每个子问题是否有模型、验证计划、图表/表格/指标证据和结论回扣；缺失的地方请给 warning。
```

## 只重新生成正文

```text
请基于现有 paper_output/tasks.json 重新生成论文正文。
调用 paper-micro-unit-generator，生成 paper_output/micro_units/，合并 paper_output/final_paper.md 和 paper_output/final_paper.docx。
正文必须遵守 tasks.json 中的 main_model、model_reason、validation_plan、figure_suggestions、result_summary、key_metrics、tables 和 conclusions。
注意：这是微单元验证草稿或局部写作素材。正式论文仍应在证据门禁通过后，由 Agent 基于完整证据链整体改写或重写。
```

## 正式论文范式成稿

```text
请进入正式论文范式成稿阶段。
先运行 quality-assurance-auditor/scripts/evidence_gate.py，只有 official 模式通过后才继续。
然后调用 paper-formal-writer/scripts/build_paper_outline.py 生成 paper_output/plan/paper_outline.json。
请读取 paper_outline.json、model_route.json、model_results.json、metrics.json、conclusions.json、figure_index.json 和 table_index.json，按 CUMCM 正式论文范式整体撰写 paper_output/final_paper_source.md。
要求：标题编号使用 1 / 1.1 / 1.1.1；正文采用 paper_outline.json 中按子问题数量生成的动态篇幅目标；摘要 800-1200 字并按问题展开；每个 5.x 至少包含建模思路、变量定义与公式推导、求解算法、结果分析、模型检验或灵敏度分析；每张图表必须先引用、插入后解释；公式必须生成可编辑 Word OMML；正文引文与参考文献必须闭环；禁止复制、替换数字或少量同义词凑篇幅。
写完后运行 paper-formal-writer/scripts/format_formal_docx.py 和 paper-formal-writer/scripts/check_paper_format.py --render required。若格式门禁失败，请继续修订 final_paper_source.md 或修复渲染环境，而不是交付当前 Word。
```

## 最终审稿

```text
请对已经生成的 final_paper.md / final_paper.docx 做最终 QA。
检查每一问是否回答原题，模型路线是否前后一致，正文是否引用了 figure_index.json 和 table_index.json 中的证据，是否仍存在“真实建模结果待补”或其他占位文字。
请运行 quality-assurance-auditor/scripts/evidence_gate.py。若证据门禁未通过，不要把当前 Word 称为最终稿。
如果已经进入正式成稿，还必须运行 paper-formal-writer/scripts/check_paper_format.py --render required。若格式门禁未通过，也不要把当前 Word 称为最终稿。
如果不能作为最终比赛稿提交，请列出必须修改项。
```

## 平台入口路径

```text
Trae        -> .trae/skills/paper-workflow-orchestrator/SKILL.md
Claude Code -> .claude/skills/paper-workflow-orchestrator/SKILL.md
Codex       -> skills/paper-workflow-orchestrator/SKILL.md
```
