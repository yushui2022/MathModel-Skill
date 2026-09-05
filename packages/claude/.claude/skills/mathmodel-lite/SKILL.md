---
name: "mathmodel-lite"
description: "低上下文、单入口数学建模工作流。Use when 用户明确要求 Lite/简易版，使用较弱或较旧模型，或需要用固定线性步骤完成赛题分析、真实代码运行、结果整理和基础 Word 论文。不要在用户要求 Standard、完整证据链、原生 Word 公式或严格渲染 QA 时使用。"
---

# MathModel Lite

使用单个 skill 和三个确定性脚本完成数学建模基础流程。减少路由、长文档和中间契约，但不允许伪造运行结果或把占位内容称为最终稿。

## 适用边界

- 用户明确选择 Lite，或模型上下文、推理能力和工具使用能力有限时使用。
- 目标是得到可复核的基础建模方案、真实运行结果、结构完整的 Markdown 和 Word。
- 需要完整评分闭环、多模型比较、原生 Word OMML 公式、正文引文审计、LibreOffice 渲染或严格比赛终稿时，改用 Standard。
- Lite 与 Standard、Pro 不得混装；预检发现其他版本时停止，只清理确认的 MathModel Skill，保留用户根目录配置。

## 固定目录

输入只读取：

```text
problem_files/
```

输出只写入：

```text
paper_output_lite/
├── input_manifest.json
├── plan.json
├── code/model.py
├── run_manifest.json
├── results.json
├── figures/
├── tables/
├── paper.md
├── paper.docx
└── lite_report.json
```

不要修改 `problem_files/`。不要把当前赛题代码写回 skill 目录。

## 固定流程

严格按以下顺序执行，不路由到其他 MathModel skills。

### 1. 预检输入

在项目根目录运行：

```bash
python .claude/skills/mathmodel-lite/scripts/lite_preflight.py
```

退出码非 0 时停止。读取 `paper_output_lite/input_manifest.json`，只使用其中列出的当前附件。

### 2. 写最小计划

读取题面和附件，写入 `paper_output_lite/plan.json`：

```json
{
  "questions": [
    {
      "id": "Q1",
      "task": "这一问要解决什么",
      "model": "采用的模型或算法",
      "output": "需要给出的结果"
    }
  ]
}
```

要求：

- 每个显式子问题必须恰好对应一个 `Q*`。
- 优先选择稳健、常见、可解释的方法；不要为了显得高级堆叠模型。
- 数据不足时明确假设，不虚构观测值或外部来源。

### 3. 写一个建模脚本

只创建 `paper_output_lite/code/model.py`，在一个脚本中处理全部子问题。脚本必须实际读取附件、执行计算，并写入：

```json
{
  "status": "computed",
  "questions": [
    {
      "id": "Q1",
      "answer": "带关键数值的直接答案",
      "method": "实际执行的方法",
      "metrics": {"指标名": 0.0},
      "evidence": ["paper_output_lite/tables/q1.csv"]
    }
  ]
}
```

`metrics` 可以为空，但写入的数值必须有限。`evidence` 可以引用非空的 CSV、图片或文本结果。禁止手写 `run_manifest.json`。

### 4. 通过统一入口运行

```bash
python .claude/skills/mathmodel-lite/scripts/lite_run.py
```

该脚本运行 `model.py`，记录计划、脚本、输入和输出的 SHA-256，清除旧 `results.json` 防止空操作复用。默认超时 300 秒，较长计算可显式使用 `--timeout 900`；这不是代码安全沙箱。运行失败时修复后重跑，不要手改状态。

### 5. 写基础论文

根据 `plan.json` 和 `results.json` 写 `paper_output_lite/paper.md`。至少包含：

```text
# 题目
# 摘要
# 1 问题重述
# 2 模型假设
# 3 模型建立与求解
# 4 结果与检验
# 5 模型评价
# 6 结论
```

每问使用独立的 `## Q1 ...` 标题，展开方法、关键计算、数值结果、检验和局限，指标必须出现在该问正文。默认全文至少 1500 有效字符，每问至少 150 字符；可分多轮写作，不要凑字。公式可保留可读 LaTeX；Lite 不承诺原生公式，不得用占位表述。

默认 `plan.json.delivery.mode` 为 `basic-report`。用户要求短报告才设置 `{"mode":"short-report","reason":"用户要求的范围"}`（全文 300 / 每问 80 字符）；安装测试可用带理由的 `smoke-test`（50 / 30），不得冒充竞赛验收。不要为通过检查自行降低范围。

图片独占一行：`![图说明](paper_output_lite/figures/q1.png)`，必须已被运行清单记录；最终脚本嵌入图片并重新打开 DOCX 核对内容。

### 6. 最终检查与 Word

```bash
python .claude/skills/mathmodel-lite/scripts/lite_finalize.py
```

只有退出码为 0 且 `lite_report.json.status` 为 `PASS`，`paper.docx` 才能称为对应范围的 Lite 最终稿；不是 20 页正式竞赛论文验收。失败时按 `failures` 修复，不要绕过门禁。

## Lite 底线

- 必须真实运行 `model.py`。
- 输入或代码在运行后变化时，必须重新预检或重跑。
- `plan.json` 中每问都必须在结果和正文中出现。
- `results.json` 必须为 `computed`，答案不能为空，指标不得为 `NaN` 或 `Inf`。
- 被引用的图表和表格必须存在且非空。
- Lite 是低负担版本，不得宣称具备 Standard 的完整证据链、原生公式和渲染 QA。
