# 插件运行与安装

仅在环境准备、工具不可用、任务运行或复算交付时读取。

插件根由当前 Skill 文件实际路径定位。所有通用代码来自活动插件；项目中不需要
`.agents/skills`。重复的 Standard/Lite/Pro 项目安装先诊断，不能悄悄挑一个版本运行。

## 首次准备与路径兼容

普通用户只需 Python；看板已包含静态前端，无 Node 构建要求。MCP 使用官方 Python SDK。

```text
python <插件根>/scripts/setup_runtime.py --runtime-root <可写运行目录> --install-deps
```

该命令在指定目录建 venv、缓存与临时目录，安装包内依赖，并用真实 MCP client
完成 initialize/tools/list。生成 `mcp.local.json`，其中解释器、脚本与 cwd 均为本机
绝对路径。安装失败会返回错误，不写入只读插件缓存。

若 Codex 不能解析包内 `.mcp.json` 的相对 cwd/脚本路径，使用已验证解释器注册：

```text
python <插件根>/scripts/setup_runtime.py --runtime-root <同一运行目录> --python <venv的Python> --register-codex --codex <实际Codex CLI路径>
```

通过 `codex mcp add` 注册 `mathmodel-local`，不手改 marketplace。完成后新任务加载
新工具；当前任务仍可使用 CLI。包内 MCP 可在宿主设置里停用，避免重复工具名称。

## 受控任务

MCP `run_job` 参数：`project_root, job_type, options`。CLI 使用相同服务：

```text
python <插件根>/scripts/workspace.py run --project-root <比赛根> --type preflight --model <实际模型> --reasoning <实际档位>
python <插件根>/scripts/workspace.py run --project-root <比赛根> --type model_run --spec code/q2-base.json
python <插件根>/scripts/workspace.py job --project-root <比赛根> --job-id <返回ID> --cursor 0
python <插件根>/scripts/workspace.py cancel --project-root <比赛根> --job-id <返回ID>
```

进程 `succeeded` 表示退出码为 0，阶段验证由当前 Pro gate 决定。实际用户批准依旧
通过 Pro checkpoint 工具记录；不能由运行事件授权。

代码/输入变化后重新提交会检查新版本。失败尝试和取消日志必须保留。重新运行 Pro
实验需独立 run ID，不覆盖已有 `experiments/<run_id>/`。从不可恢复的求解器中断
重试不表示能从任意求解器内部断点接续。

`.mathmodel/` 保存服务身份、队列、日志和派生状态；`paper_output_pro/` 保存正式
契约与成果。不要手改数据库、状态快照、ledger 来修复门禁。

## 影响与重放

```text
python <插件根>/scripts/change_impact.py --project-root <比赛根> --changed paper_output_pro/code/common.py
python <插件根>/scripts/replay_project.py export --project-root <比赛根> --destination <新目录> --allow-input data_cleaned/input.csv
python <插件根>/scripts/replay_project.py run --bundle-root <导出目录> --output-root <另一个新目录> --python-executable <复算环境Python>
```

导出不自动下载、不安装商业求解器、不复制批准、不运行计算。未授权打包的数据只
记录哈希，使用者需自行补齐匹配原件。重放报告明确说明支持的比较范围与失败原因。
