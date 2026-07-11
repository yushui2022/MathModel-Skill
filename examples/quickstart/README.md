# MathModel Lite Quickstart

这是 Lite 分支的最小输入示例：

```text
examples/quickstart/problem_files/
├── sample_problem.txt
└── sample_data.csv
```

## 使用

1. 新建一个空项目并安装对应平台的 Lite ZIP。
2. 将本目录的 `problem_files/` 复制到项目根目录。
3. 运行 `pip install -r requirements.txt`。
4. 让 Agent 读取 `mathmodel-lite/SKILL.md` 并完成固定六步。

可使用以下提示词：

```text
请使用 MathModel Lite，只读取 mathmodel-lite。
根据 problem_files/ 完成 plan.json，创建并真实运行单个 model.py，生成 results.json 和 paper.md，最后运行 lite_finalize.py。
只有 lite_report.json 为 PASS 时才交付 paper.docx。
```

## 期望输出

```text
paper_output_lite/
├── input_manifest.json
├── plan.json
├── code/model.py
├── run_manifest.json
├── results.json
├── tables/
├── figures/
├── paper.md
├── paper.docx
└── lite_report.json
```

这个示例只验证 Lite 流程。真实赛题仍需根据题面和附件编写实际建模代码。
