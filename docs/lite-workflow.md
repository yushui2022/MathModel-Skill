# MathModel Lite Workflow

Lite 面向上下文较短、推理能力较弱或工具调用不稳定的模型。它不是 Standard 的降质副本，而是减少路由和中间契约后的独立线性工作流。

## 与 Standard 的区别

| 能力 | Lite | Standard |
|---|---|---|
| Skill 数量 | 1 个单入口 | 10 个协作 Skill |
| 流程 | 固定 6 步 | S0-S8 动态路由 |
| 核心结构化文件 | manifest、plan、run、results、report | 完整模型路线、数据、图表、证据与格式契约 |
| 建模代码 | 单个 `model.py` | 按问题拆分并支持复杂流水线 |
| 输入和运行哈希 | 支持 | 支持，检查更完整 |
| Word | 基础 DOCX | 原生 OMML、引文和渲染 QA |
| 适合场景 | 快速基础稿、旧模型、低上下文 | 正式竞赛稿和高质量交付 |

Lite 仍然要求真实运行建模代码，不允许占位结果冒充最终稿。

## 安装隔离

- Standard 位于默认分支 `master`，Lite 位于独立分支 `lite`；每个分支只分发自己的版本。
- 一个比赛项目只能安装 Standard 或 Lite 其中之一，不要把两个分支的 ZIP 解压到同一个项目。
- Lite preflight 会检测 `paper-workflow-orchestrator`；发现 Standard 残留时直接失败。
- 从 Standard 切换到 Lite 时，先在项目中删除 Standard 的 skill 目录及 `CLAUDE.md` / `AGENTS.md` 入口，再安装 Lite。

## 使用方式

把赛题和附件放入：

```text
problem_files/
```

然后对 Agent 说：

```text
请使用 MathModel Lite。严格按 mathmodel-lite 的固定六步执行。所有产物写入 paper_output_lite/。必须真实运行 model.py，并在 lite_report.json 为 PASS 后才交付 paper.docx。如果检测到 Standard 入口，停止并提示清理混装。
```

安装 Lite 包内的精简依赖：

```bash
pip install -r requirements.txt
```

Lite 的依赖文件不包含 Standard 使用的 PDF、LaTeX 公式和严格格式检查组件。

三个脚本按顺序运行：

```bash
python skills/mathmodel-lite/scripts/lite_preflight.py
python skills/mathmodel-lite/scripts/lite_run.py
python skills/mathmodel-lite/scripts/lite_finalize.py
```

Claude Code 将 `skills/` 替换为 `.claude/skills/`，Trae 替换为 `.trae/skills/`。

## 最终产物

```text
paper_output_lite/plan.json
paper_output_lite/code/model.py
paper_output_lite/run_manifest.json
paper_output_lite/results.json
paper_output_lite/paper.md
paper_output_lite/paper.docx
paper_output_lite/lite_report.json
```

需要原生 Word 公式、严格参考文献审计、PDF 渲染或完整评分闭环时，改用默认分支 `master` 的 Standard。
