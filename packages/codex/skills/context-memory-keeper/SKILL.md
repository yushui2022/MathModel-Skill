---
name: "context-memory-keeper"
description: "Manages persistent memory. Invoke to read active context or archive old tasks. Structure: Long-term Principles (Rules) + Short-term Workbench (Tasks)."
---

# Context Memory Keeper

## 全局流程协作约束（长对话防漂移）

- 本 skill 不得作为孤立入口。用户要求完整论文、生成 Word、继续流程或不确定阶段时，先回到 `paper-workflow-orchestrator` 判断当前 S0-S8 阶段。
- 启动或继续本 skill 的正式任务前，必须运行：
  ```bash
  python skills/paper-workflow-orchestrator/scripts/workflow_guard.py --skill context-memory-keeper
  ```
- 如果输出 `[WORKFLOW FAIL]` 或报告 `status != "PASS"`，停止本 skill，按 `paper_output/qa/workflow_guard_report.json` 的失败项回补前置阶段，不得凭记忆继续。
- 本 skill 只写入自己契约范围内的 `paper_output/` 产物；完成后必须回到 `paper-workflow-orchestrator` 判断下一步，并用 `context-memory-keeper` 记录已完成产物、阻塞项和下一步。
- 长对话中如果上下文变长、阶段不确定或用户分开调用 skill，先运行：
  ```bash
  python skills/paper-workflow-orchestrator/scripts/workflow_guard.py --status
  ```
  再读取 `paper_output/qa/workflow_guard_report.json`、`paper_output/preflight_report.json`、`paper_output/input_manifest.json`、`paper_output/results/run_manifest.json` 和本 skill 的上游 JSON 契约，按报告里的 `recommended_skill` 与 `next_action` 继续。
- ?? `paper_output/context/workflow_memory.json` ?????????????? `current_step`?`next_step`?`recommended_skill`????????????????????
- ? skill ???????????? `paper-workflow-orchestrator` ?? `workflow_guard.py --status`?????
  ```bash
  python skills/context-memory-keeper/scripts/update_workflow_memory.py
  ```
  ?? `paper_output/context/workflow_memory.json` / `.md`?????????????

## 执行契约
- 上游输入：当前赛题约束、模型路线、数据源、图表路径、QA 结论、用户新增偏好和流程断点。
- 必须输出：更新后的 `memoryskill.md`；当短期工作台过长时，将旧任务摘要归档到 `memory_archive.md`。
- 下游交接：其他 skill 在复杂任务开始前读取 `memoryskill.md`，避免遗忘当前模型路线、数据来源和用户要求。
- 推荐下一步：完成记忆更新后回到调用它的当前 skill；若目标是完整论文，回到 `paper-workflow-orchestrator` 判断后续阶段。
- 失败回退：若无法安全更新记忆文件，应在本轮回复中明确保留关键结论，并提示后续手动补写到记忆文件。

## Description
此 Skill 维护双层记忆结构，旨在解决模型上下文遗忘问题，同时保持上下文窗口的整洁。

## Files Structure
## Executable Workflow Memory
- After `workflow_guard.py --status` or after a skill handoff, run:
  ```bash
  python skills/context-memory-keeper/scripts/update_workflow_memory.py
  ```
- The script reads `paper_output/qa/workflow_guard_report.json` plus key workflow artifacts and writes:
  - `paper_output/context/workflow_memory.json`
  - `paper_output/context/workflow_memory.md`
- Long conversations and resumed sessions should read `workflow_memory.json` before relying on chat history.

1. **`memoryskill.md` (Active Memory)**:
   - **长期准则**: 用户偏好、角色设定、全局约束 (Read-Only mostly)。
   - **短期工作台**: 当前任务状态、变量、正在进行的步骤、**外部文献/数据索引** (Read-Write frequently)。
2. **`memory_archive.md` (Archive)**:
   - 历史记录、已完成的任务详情 (Write-Only mostly)。

## When to Invoke
- **Read**: 每次开始复杂任务前，或感到上下文模糊时，读取 `memoryskill.md`。
- **Update**: 
  - 获得新指令或完成小步骤 -> 更新 `memoryskill.md` 的“短期工作台”。
  - 用户修改全局规则 -> 更新 `memoryskill.md` 的“长期准则”。
- **Archive (Cleanup)**:
  - 当“短期工作台”内容过长或阶段性任务结束 -> 将旧内容剪切到 `memory_archive.md`，并在 `memoryskill.md` 中仅保留关键结论。

## Compression Policy (Auto-Cleanup)
- **触发条件**: 当 `memoryskill.md` 超过 **100 行** 时，**必须**执行压缩。
- **保留原则**:
  1. **User Imperatives**: 用户强烈要求的命令、偏好、红线（High Priority）。
  2. **Project Skeleton**: 项目核心框架、关键路径、当前阶段里程碑（Medium Priority）。
  3. **Active Blockers**: 正在阻碍当前任务的问题（High Priority）。
- **丢弃/归档原则**:
  1. **Details**: 已完成任务的执行细节 -> 移至 `memory_archive.md`。
  2. **Logs**: 过程性的成功/失败日志 -> 移至 `memory_archive.md` 或直接删除。
  3. **Expired Context**: 已失效的临时变量或不再相关的上下文 -> 直接删除。

## Usage Tips
- 保持 `memoryskill.md` 轻量（建议 < 100 行），以便随时快速读取。
- 归档是**手动触发**的动作（由模型决定何时剪切粘贴）。
