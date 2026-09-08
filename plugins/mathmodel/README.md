# MathModel Workbench for Codex

MathModel packages the existing S0–S8 mathematical-modeling Skills with a local, evidence-first workbench. The conversation remains the place for problem analysis, model choices and paper writing; the right-side dashboard is the operational view of real project state.

## 使用

在包含 `problem_files/` 的比赛目录中直接告诉 Codex：

> 开始建模，先做预检，并打开 MathModel 工作台。

Codex 会使用插件入口 Skill，启动本地服务并在支持的桌面宿主中打开右侧工作台。工作台服务只监听回环地址，产物只从 `paper_output/` 登记读取，不上传题面、代码或结果。关闭页面不会终止实验，重新打开会从 `.mathmodel/` 恢复状态。

用户也可以手动启动本地服务（适合调试或宿主尚未提供右栏能力）：

```bash
python <插件目录>/scripts/serve_dashboard.py --project-root . --port 8765
```

然后在 Codex 中打开打印出的本地地址。普通浏览器也可以访问，但它不是 Codex 右栏的保证替代品。

## MCP 工具

`.mcp.json` 注册可选的 Python MCP 服务。安装了官方 Python MCP SDK 后，服务提供 `open_workspace`、`get_status`、`list_artifacts`、`read_artifact`、`run_job`、`get_job`、`cancel_job` 和 `get_next_action`。没有安装 SDK 时，Skills 和本地看板仍可使用，启动错误会明确提示安装命令。

受控任务只有预检、模型运行、证据检查和格式检查四类，不接受任意 shell 字符串。Guard 的验证报告是完成依据，手工记录的 `passed` 事件只能显示为“待验证”，不能伪造阶段通过。

## 开发与发布

插件 Skills 是生成副本，规范来源仍是 `packages/claude/.claude/skills`。同步并检查：

```bash
python plugins/mathmodel/scripts/sync_plugin_skills.py
python plugins/mathmodel/scripts/sync_plugin_skills.py --check
```

插件缓存与比赛项目严格分离；结果、记忆和 SQLite 状态写入比赛目录的 `.mathmodel/` 与 `paper_output/`。发布前运行插件校验、Python 编译、MCP 协议 smoke test 和现有完整回归测试。
