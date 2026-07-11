# MathModel Lite Starter Prompt

本提示词只随 Lite 发布包分发。不要在同一项目中同时安装 Standard 和 Lite。

```text
我已经把赛题和附件放进 problem_files/。
请使用 MathModel Lite，只读取 mathmodel-lite。
严格按固定六步执行：预检输入、写 plan.json、创建单个 model.py、通过 lite_run.py 真实运行、根据 results.json 写 paper.md、通过 lite_finalize.py 生成 Word。
所有产物写入 paper_output_lite/。输入或代码变化后必须重跑；results.json 不得使用占位结果；只有 lite_report.json 为 PASS 时才能交付 paper.docx。
如果检测到 Standard 的 paper-workflow-orchestrator，请停止并提示我清理混装，而不是尝试选择其中一个入口。
```

