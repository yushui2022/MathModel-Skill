---
name: "paper-formal-writer"
description: "国赛数学建模正式论文范式、outline、Word 排版和格式门禁 skill。Invoke when 证据门禁通过后需要生成 CUMCM 风格正式论文、规范标题编号、扩写正文、插入图表表格、导出 Word 或检查论文格式。"
---

# 正式论文范式写作器

## 全局流程协作约束（长对话防漂移）

- 本 skill 不得作为孤立入口。用户要求完整论文、生成 Word、继续流程或不确定阶段时，先回到 `paper-workflow-orchestrator` 判断当前 S0-S8 阶段。
- 启动或继续本 skill 的正式任务前，必须运行：
  ```bash
  python .claude/skills/paper-workflow-orchestrator/scripts/workflow_guard.py --skill paper-formal-writer
  ```
- 如果输出 `[WORKFLOW FAIL]` 或报告 `status != "PASS"`，停止本 skill，按 `paper_output/qa/workflow_guard_report.json` 的失败项回补前置阶段，不得凭记忆继续。
- 本 skill 只写入自己契约范围内的 `paper_output/` 产物；完成后必须回到 `paper-workflow-orchestrator` 判断下一步，并用 `context-memory-keeper` 记录已完成产物、阻塞项和下一步。
- 长对话中如果上下文变长、阶段不确定或用户分开调用 skill，先运行：
  ```bash
  python .claude/skills/paper-workflow-orchestrator/scripts/workflow_guard.py --status
  ```
  再读取 `paper_output/qa/workflow_guard_report.json`、`paper_output/preflight_report.json`、`paper_output/input_manifest.json`、`paper_output/results/run_manifest.json` 和本 skill 的上游 JSON 契约，按报告里的 `recommended_skill` 与 `next_action` 继续。
- 继续流程前，必须把 `paper_output/context/workflow_memory.json` 视为长期断点记录；若其中的 `current_step`、`next_step`、`recommended_skill` 与 `workflow_guard.py --status` 不一致，以 guard 报告为准。
- 每次完成本 skill 的产物后，先回到 `paper-workflow-orchestrator` 或运行 `workflow_guard.py --status`，再更新 workflow memory：
  ```bash
  python .claude/skills/context-memory-keeper/scripts/update_workflow_memory.py
  ```
  更新后读取 `paper_output/context/workflow_memory.json` / `.md`，确认下一步和推荐 skill 已记录。

## 执行契约
- 上游输入：必须优先读取 `paper_output/plan/model_route.json`、`paper_output/results/`、`paper_output/tables/table_index.json`、`paper_output/figure_index.json` 和证据门禁报告。
- 核心输出：`paper_output/plan/paper_outline.json`、`paper_output/final_paper_source.md`、`paper_output/final_paper.docx`、`paper_output/format_check_report.md`。
- 下游交接：格式检查通过后，回到 `quality-assurance-auditor` 做最终一致性检查；未通过时继续补正文、图表解释或证据引用。
- 失败回退：证据门禁未通过时，不得把 Word 称为最终稿；可以只生成 outline 和待写作清单。

## 目标
- 本技能负责正式论文范式、章节编号、写作约束、Word 排版和格式检查。
- 正式论文必须由 Agent 基于完整证据链全局写作，不得机械拼接 quickstart 草稿或微单元草稿。
- 标题编号固定采用 `1 / 1.1 / 1.1.1`。
- 篇幅目标由 `build_paper_outline.py` 按子问题数量 `Q` 动态生成：最低 `6500 + 1200Q`、理想 `7500 + 1500Q`、建议上限 `10000 + 2200Q` 个有效字符。以证据密度和完整推导为准，不得为了固定字数复制、近义改写或仅替换数字扩写。

## 何时使用
- `quality-assurance-auditor/scripts/evidence_gate.py` official 模式已经通过，需要进入正式成稿。
- 用户要求“按国赛论文格式”“正式 Word”“扩写到比赛论文工作量”“图表插入并解释”“检查论文格式”。
- 已有 `final_paper_source.md` 或 `final_paper.md`，需要统一 Word 样式、图题表题和标题层级。

## References
- 正式格式总规范：`references/cumcm-paper-standard.md`
- 可直接交给 Agent 的全文模板：`references/formal-paper-template.md`
- 各章节扩写规则：`references/section-expansion-rules.md`
- 图表、公式、算法和结果解释规则：`references/figure-table-writing-rules.md`

## 脚本清单
- `scripts/build_paper_outline.py`
  - 读取题意、模型路线、结果、指标、结论、图表和表格索引。
  - 输出 `paper_output/plan/paper_outline.json`。
- `scripts/format_formal_docx.py`
  - 输入 `paper_output/final_paper_source.md`。
  - 输出 `paper_output/final_paper.docx` 和 `paper_output/format_check_report.md`。
  - 在正式模式下先验证 evidence gate 的输入哈希仍然新鲜；过期报告不得继续生成正式 Word。
  - 调用 `formula_omml.py` 把行内和独立 LaTeX 公式转换为 Word 原生 OMML。存在源公式但转换失败时，正式模式必须终止；`--allow-draft` 才可用纯文本回退并写入 `final_paper_draft.docx`。
- `scripts/formula_omml.py`
  - 使用 `latex2mathml` 解析 LaTeX，并将常用分式、上下标、根式、重音、极限和矩阵结构转换为可编辑 OMML。
- `scripts/check_paper_format.py`
  - 检查动态篇幅、章节、三级标题、图表引用、附录、占位符、证据覆盖和 Word 视觉结构。
  - 拒绝控制字符、数字归一化后的重复/近重复段落，以及附录前的内部工程话术。
  - 单独统计正文引文与文末条目；参考文献必须在正文实际引用，不得只列清单。
  - 对比 Markdown 源公式数量和 DOCX 原生 OMML 数量；原生公式不足即失败。
  - 将源稿、DOCX、outline、图表索引和证据报告哈希写入格式报告，供 S8 检测报告过期。
  - 支持 `--render auto|required|skip`。最终交付使用 `--render required`，通过 LibreOffice 转 PDF 并检查页数和可提取文本。
  - 输出 `paper_output/format_check_report.md` 与 `paper_output/format_check_report.json`。

## 正式工作流
1. 确认证据门禁已通过；若未通过，先补齐 `paper_output/code/`、`results/`、`tables/` 和 `figures/`。
2. 运行：
   ```bash
   python .claude/skills/paper-formal-writer/scripts/build_paper_outline.py
   ```
3. Agent 读取 `paper_outline.json` 和 references，基于完整证据链全局撰写：
   ```text
   paper_output/final_paper_source.md
   ```
4. 运行：
   ```bash
   python .claude/skills/paper-formal-writer/scripts/format_formal_docx.py
   python .claude/skills/paper-formal-writer/scripts/check_paper_format.py --render required
   ```
5. 若格式检查失败，按报告修复证据引用、公式、重复段落、正文引文、图表解释、附录或渲染问题；不得用扩写填充掩盖失败项。

## 正式论文必须满足
- 摘要按子问题展开，包含方法、模型、算法和关键结果。
- `1 问题重述`、`2 问题分析`、`3 模型假设`、`4 符号说明`、`5 模型的建立与求解`、`6 模型检验与灵敏度分析`、`7 模型评价与推广`、`8 参考文献`、`附录` 结构完整。
- 每问在第 5 章中至少包含 `5.x.1 建模思路`、`5.x.2 变量定义与公式推导`、`5.x.3 求解算法`、`5.x.4 结果分析`、`5.x.5 模型检验或灵敏度分析`。
- 每张图表必须在正文中引用并解释；图表不能只插入不分析。
- 每个公式必须先定义变量、再给公式、再解释公式含义和用途。
- 正式 DOCX 中的数学公式必须是可编辑的 Word 原生公式，不得用截图或普通文本冒充。
- 文末每条参考文献都必须在正文引用，正文引用编号必须能在参考文献表中找到。
- 禁止复制段落后只改数字、序号或少量同义词来满足篇幅目标。
- `paper_output`、内部脚本名、Skill/Agent 调用说明等实现话术只能放在附录，不得进入正式正文。
- 算法必须用 `Step 1`、`Step 2` 等形式说明。

## 与其他 skill 的关系
- `paper-workflow-orchestrator`：总入口，证据门禁通过后路由到本技能。
- `paper-micro-unit-generator`：提示词资产库和兜底草稿工具，不再作为正式论文主笔。
- `quality-assurance-auditor`：负责证据门禁；本技能负责格式门禁，两者都通过后才可称为正式稿。
