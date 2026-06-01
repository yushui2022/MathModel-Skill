---
name: "authoritative-data-harvester"
description: "自动定位并获取权威公开数据（优先API/官方批量下载），输出可复现抓取与清洗方案。Invoke when用户需要权威数据、官方统计、API下载或数据源爬取。"
---

# 权威数据自动获取（Authoritative Data Harvester）

## 全局流程协作约束（长对话防漂移）

- 本 skill 不得作为孤立入口。用户要求完整论文、生成 Word、继续流程或不确定阶段时，先回到 `paper-workflow-orchestrator` 判断当前 S0-S8 阶段。
- 启动或继续本 skill 的正式任务前，必须运行：
  ```bash
  python .claude/skills/paper-workflow-orchestrator/scripts/workflow_guard.py --skill authoritative-data-harvester
  ```
- 如果输出 `[WORKFLOW FAIL]` 或报告 `status != "PASS"`，停止本 skill，按 `paper_output/qa/workflow_guard_report.json` 的失败项回补前置阶段，不得凭记忆继续。
- 本 skill 只写入自己契约范围内的 `paper_output/` 产物；完成后必须回到 `paper-workflow-orchestrator` 判断下一步，并用 `context-memory-keeper` 记录已完成产物、阻塞项和下一步。
- 长对话中如果上下文变长、阶段不确定或用户分开调用 skill，先运行：
  ```bash
  python .claude/skills/paper-workflow-orchestrator/scripts/workflow_guard.py --status
  ```
  再读取 `paper_output/qa/workflow_guard_report.json`、`paper_output/preflight_report.json`、`paper_output/input_manifest.json`、`paper_output/results/run_manifest.json` 和本 skill 的上游 JSON 契约，按报告里的 `recommended_skill` 与 `next_action` 继续。

## 执行契约
- 上游输入：用户给出的变量需求，或 `paper_output/step1/problem_analysis.json`、`paper_output/plan/model_route.json` 中识别出的外部数据需求。
- 必须输出：可复现的数据源说明、抓取或下载方案，并将原始/处理后数据与来源信息保存到 `crawled_data/`，优先包含 `crawled_data/sources.json`。
- 下游交接：`data-cleaning-and-visualization` 读取 `crawled_data/` 做统一清洗、图表计划和论文级配图。
- 推荐下一步：数据落盘后进入 `data-cleaning-and-visualization`；完整论文目标应回到 `paper-workflow-orchestrator` 判断后续阶段。
- 失败回退：若无法自动获取，应给出同级权威替代源、口径差异和人工下载路径；不得使用无来源或不可引用的数据冒充权威数据。

## 目标
在数学建模任务中，快速找到“权威、可引用、可复现”的公开数据源，并以尽量不爬网页、优先 API/批量下载的方式获取数据，最终输出：
- 数据获取脚本/方案（含链接、参数、时间范围、字段解释）
- 原始数据与清洗后的数据（CSV/Parquet）
- 数据字典与引用信息（来源、更新时间、许可证/条款、访问日期）

## 何时调用
- 需要权威/官方数据源（统计局、国际组织、政府开放数据）
- 需要可复现的数据抓取流程（接口参数固定、可重复运行）
- 已有变量清单但缺数据，或需要补充替代指标

## 总原则（必须遵守）
1. 优先使用官方 API 或 Bulk Download，最后才做 HTML 解析。
2. 遵守 robots.txt 与服务条款，尊重速率限制；不得绕过登录/付费/验证码。
3. 全流程可复现：记录来源 URL、接口参数、访问日期、版本/更新时间、字段含义与单位。
4. 数据质量优先：对齐口径、单位、频率、地理范围；明确缺失与异常处理策略。

## 标准工作流（每次执行都按此输出）
### 1) 需求归一化
输出“数据需求表”，至少包含：
- 变量名（中英）、单位、期望频率（日/月/年）、时间范围
- 地区粒度（国家/省/市/网格）与口径说明
- 允许替代指标（主指标不可得时）

### 2) 选源策略（先权威后便利）
按任务类型优先匹配：
- 宏观/发展：World Bank、IMF、OECD、UNData
- 人口/社会：UN DESA、World Bank、各国统计局/人口普查
- 公共卫生：WHO（必要时补充二次聚合源并标注来源链）
- 气象/气候：NOAA、NASA（按开放政策选择）
- 欧盟统计：Eurostat
- 中国：国家统计局、部委开放数据、地方统计局（优先可下载/接口）

### 3) 访问方式决策树
- 有官方 API：直接 API
- 无 API 但有批量下载（CSV/Excel/ZIP）：直链下载
- 仅网页表格：优先找页面背后的 XHR/JSON；仍不行再做 HTML 解析

### 4) 抓取实现规范
交付脚本必须具备：
- 参数化：start/end、region、indicator、output_dir
- 稳健性：重试（指数退避）、超时、速率限制、缓存/断点
- 落盘：raw/ 与 processed/ 分目录；保留原始响应或原始文件
- 日志：只记录必要信息，不输出敏感信息

### 5) 清洗与校验（最低要求）
- 字段：统一命名（snake_case）、类型转换、单位换算、时间索引对齐
- 缺失：说明缺失原因（不可得/断档/口径变化），给出处理策略
- 异常：基本规则校验（范围、同比/环比跳变阈值）
- 抽检：与来源页面/元数据对照样本行

### 6) 交付物清单（必须输出）
- 数据文件：raw.*、processed.csv（或 parquet）
- 元数据：sources.json（name/url/access_method/params/license/updated_at/accessed_at）
- 数据字典：字段含义、单位、频率、地区粒度、缺失策略
- 引用格式：可直接用于论文/报告的参考条目

## 常用权威数据源（可扩展）
- World Bank Data API
- IMF Data
- UNData / UN agencies
- OECD Data
- Eurostat
- WHO
- NOAA / NASA
- 各国统计局与政府开放数据平台

## 用户输入模板（用于快速启动）
- “我要做【主题】建模，变量有【A,B,C】；时间【YYYY-YYYY】；地区【国家/省/市】；请给权威来源与可复现的数据获取脚本+清洗结果。”
- “我需要【某指标】的官方数据，优先 API，没有就批量下载；请输出 sources.json + processed.csv。”

## 失败回退策略
当某源不可用/受限：
1. 换同级权威源（例如 UN ↔ World Bank ↔ OECD）
2. 换替代指标并明确口径差异
3. 仅交付最权威的可下载版本，并说明无法自动化获取原因

## 目录约定（与项目全局对齐）
- 原始下载与接口响应建议保存到：`crawled_data/raw/`。
- 清洗后的结构化数据建议保存到：`crawled_data/processed/`。
- 来源与可复现信息建议保存为：`crawled_data/sources.json`（包含 url、参数、访问日期、许可证/条款）。

## 前后衔接
- 后续通常先做：`data-cleaning-and-visualization`（把 `crawled_data/` 里的数据统一清洗并出图）。
- 若要继续到论文草稿：回到 `paper-workflow-orchestrator`。

## 约束（必须遵守）

- **Memory Interaction (必做)**:
  - **获取数据后**：必须调用 `context-memory-keeper`，记录“新增数据源名称”与“存放路径”到 `Short-term Workbench`。
- 本技能只负责“把权威数据拿到手并保证可复现”，不负责直接写论文正文；产物必须落盘到 `crawled_data/`。
- 若数据要进入论文，必须同时满足两点：
  - `crawled_data/sources.json` 中记录可引用来源信息。
  - 后续调用 `data-cleaning-and-visualization`，把数据清洗并生成 `paper_output/figures/` 的证据图表。
