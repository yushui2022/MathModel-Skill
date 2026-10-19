# Standard Starter Prompts

先读取实际安装位置的入口 SKILL.md。脚本从已加载 Skill 的目录定位，运行工作目录保持为赛题根；不要依赖平台专属调用语法。

## Formal Project

```text
请使用 paper-workflow-orchestrator 完成这个数学建模项目。
赛题和官方附件已放在 problem_files/。
先运行 preflight_check.py 和 workflow_guard.py --status，再按 S0-S8 推进。
所有当前赛题代码写入 paper_output/code/，真实结果、图表、表格、证据和论文写入 paper_output/。
S6 evidence gate 必须使用 official 模式并保持输入哈希新鲜。
S7 使用 Standard 单一正式主线：写作计划、完整章节草稿、逐章审计、必要时排队局部修复、确定性合并、全文统一改写、最终 Markdown 审计。
默认完整竞赛稿，可分多轮完成章节。核对当年赛题的页数限制，每个子问题充分展开推导、计算结果和验证；不要把单次回复当完整论文，也不要凑字凑页。除非我明确要求短稿，否则不改 short-report / smoke-test 或降低验收范围。
不要把 quickstart、legacy 或机械微单元合并稿提升为正式稿。
只有 authoring PASS 后才生成 final_paper.docx，并用 LibreOffice 执行 --render required。
任一门禁失败时继续修复，不要声称已经完成。
```

## Resume An Interrupted Project

```text
请使用 paper-workflow-orchestrator 恢复这个项目。
先运行 workflow_guard.py --status，读取 workflow_guard_report.json、workflow_memory.json 和当前文件哈希。
从第一个失败阶段继续，不要凭对话记忆重跑已完成阶段，也不要跳过 S6-S8。
```

## Repair A Failing Section

```text
请先读取 writing_plan.json、authoring_state.json、draft_audit.json 和 repair_queue.json。
如果队列策略是 section-rewrite，使用 paper-formal-writer 重写完整章节。
只有策略明确为 micro-repair 时才使用 paper-micro-unit-generator，并且只修复队列指定的章节、证据或段落。
修复后重新运行 validate_authoring.py --section <section-id>。
```

## Installation Smoke Test

```text
请定位已安装的 paper-workflow-orchestrator/scripts/quickstart_run.py，传入 --project-root 指向赛题目录，只验证安装和基础契约。
确认所有草稿只出现在 paper_output/quickstart/，并确认没有生成 final_paper_source.md、final_paper.docx 或其他正式命名文件。
```

## Script Location

<SKILL_ROOT> 是已加载 Skill 文件夹的父目录，使用实际绝对路径替换并保留引号，不是环境变量。安装目录选择见安装包根目录的 README-MathModel-Skill.md 或仓库安装指南。
