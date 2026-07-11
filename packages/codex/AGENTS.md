# MathModel Lite for Codex

当用户明确要求 MathModel Lite、简易版，或说明当前模型能力较弱时，只读取：

```text
skills/mathmodel-lite/SKILL.md
```

严格执行该 Skill 的固定六步，不路由到 Standard 的其他数学建模 skills。输入只读取 `problem_files/`，输出只写入 `paper_output_lite/`。必须通过 `lite_run.py` 真实运行建模代码，并在 `lite_finalize.py` 返回成功后才交付 `paper.docx`。

如果项目中仍存在 `paper-workflow-orchestrator`，立即停止并提示用户清理 Standard 残留；不要尝试在两个入口之间自行选择。

用户要求正式竞赛稿、完整证据链、原生 Word 公式、严格引文或渲染检查时，不使用 Lite，改用 Standard。
