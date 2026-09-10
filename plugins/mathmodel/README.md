# MathModel for Codex · 0.5.0-alpha.1

这个 Alpha 插件使用 MathModel **Pro 3.3.0-pro.1** 的 P0–P9 核心。对话负责审题、建模判断和写作；插件帮助新会话恢复具体问题、管理实际计算、解释修改影响，并交付可独立复算的代码包。

Pro 原有的三路审题、多路线比较、独立复算、稳健性、三个确认点、证据冻结和五角色审稿继续生效。插件新增的工程功能与有限范围数学检查不构成真实竞赛质量提升的证明。

## 安装与环境

使用完整插件目录或发行 ZIP，不要单独复制 `SKILL.md`。由当前 Codex 宿主支持的插件安装入口启用 `.codex-plugin/plugin.json`；比赛目录只放赛题和比赛产物，不再额外安装第二套 MathModel Skill。

建议 Python 3.11/3.12。`requirements.txt` 固定 MCP SDK 依赖；`core-requirements.txt` 提供 Pro 建模依赖。Word/PDF 正式交付还需要 LibreOffice。检查实际解释器、依赖和项目重复入口：

```powershell
$plugin = 'G:\Projects\mathmodel-insert\plugins\mathmodel'
python "$plugin\scripts\setup_runtime.py" --project-root 'G:\Projects\my-contest'
```

需要安装依赖时，使用插件缓存外的可写运行目录。下面的命令创建该目录内的 venv、安装依赖、生成绝对路径的 `mcp.local.json`，并用官方 MCP SDK 实际连接检查：

```powershell
python "$plugin\scripts\setup_runtime.py" --runtime-root 'G:\DevCache\MathModelRuntime' --install-deps
```

已有环境可以省略 `--install-deps`；运行目录内已有 `.venv` 时默认复用，或用 `--python <解释器完整路径>` 指定。命令完成的 `PROTOCOL_VERIFIED` 仅表示本机配置能启动并连接服务。需要通过 Codex CLI 注册时可加 `--register-codex`，默认更新 `mathmodel`，可用 `--server-name` 明确指定名称；确保实际宿主只启用一个 MathModel MCP 配置。插件自带 `.mcp.json` 使用相对路径，宿主不能正确解析时使用生成的绝对配置。

上述设置会写运行目录或用户显式选择的 Codex 配置。比赛状态与结果不会写回插件缓存。当前桌面安装与视觉验收结果由主线程在仓库[验证记录](../../docs/plugin-upgrade-validation.md)中补充；不要把 CLI 协议连通推断为所有宿主均已自动安装或展示成功。

## 开始与恢复

把题面和附件放入比赛项目的 `problem_files/`，对 Codex 说：

> 开始建模。先检查输入、实际模型和推理档位，再按 MathModel Pro 推进；涉及确认时给出当前题意、路线或结果的具体对象。

恢复可以说“继续第二问”“查看尚未解决的审稿意见”。无需打开看板。调试时可直接读取恢复包：

```powershell
python "$plugin\scripts\build_context_packet.py" --project-root 'G:\Projects\my-contest' --question q2 --format markdown
```

恢复包包含事实来源、哈希、当前状态、小问定位和下一 Skill；分页依照返回的游标与版本继续读取。默认读取不写 QA 或 memory，显式 `--write` 才保存 `.mathmodel/context/resume.json`。`pro_status.py` 通过现有 Pro 校验器只读重建状态；旧 memory 与当前门禁冲突时，以当前文件和门禁为准。

普通状态查询的退出码 0 表示查询完成。需要检查成功的进程退出语义时，使用 `--fail-if-blocked`；`--require-through P5` 检查到证据确认，`P6` 检查到冻结，默认 `P9` 要求全程通过。`current` 事实也只表示相应记录可追溯，不是正式论文验收。

## 实验与证据页面

所有正式比赛产物在 `paper_output_pro/`：`code/` 保存脚本和 run-spec，`experiments/<run_id>/` 保存回执与结果，`final_paper_source.md`、`final_paper.docx`、`final_paper.pdf` 保存论文交付。项目 `.mathmodel/` 保存服务、作业数据库和运行状态。

页面和 MCP 连接同一项目运行服务。关闭页面不会主动取消计算；服务或计算进程异常后会依据真实执行所有者和回执恢复可判断的状态。无法恢复的运行标记中断并保留日志，不能保证任意求解器从内部断点继续。

可用 MCP 工具：

| 用途 | 工具 |
|---|---|
| 安装诊断与页面地址 | `doctor`、`open_workspace` |
| 恢复与阶段 | `get_context_packet`、`get_next_action`、`get_status` |
| 产物与日志 | `list_artifacts`、`read_artifact`、`get_job` |
| 计算管理 | `run_job`、`cancel_job`、`retry_job` |
| 修改与移交 | `get_change_impact`、`export_replay` |

受控作业是 `preflight`、`model_run`、`evidence_check`、`format_check`、`final_check`。`model_run` 使用 `paper_output_pro/code/` 中的 JSON run-spec，不接收任意 shell 字符串。它仍需当前项目的真实批准；重试不覆盖旧实验目录。`get_next_action` 只返回交接包，不会隐式创建审稿 Agent。

需要看证据时说“打开 MathModel 工作台”，或调试运行：

```powershell
python "$plugin\scripts\serve_dashboard.py" --project-root 'G:\Projects\my-contest' --port 0
```

本地服务监听回环地址，页面需要当前服务令牌。`open_workspace` 返回健康检查后的 URL；是否在 Codex 右侧打开由宿主能力决定。普通浏览器可使用本地页面，本版本不承诺 MCP Apps 或无条件自动打开面板。

## 有限范围的数学检查

插件预检启用 `optimization_check_profile=linear-v1`。每条候选路线须声明 LP、MILP 或有实质理由的范围外情况。LP/MILP 规格在检查点 2 前绑定变量、目标、约束和数据；独立检查器计算残差与目标，定位违规约束，区分可行与有证书支持的最优界。

模型自己填写的 `feasible=true` 或求解器 `optimal` 文本不能代替核验。修改规格或适用性会使批准失效；旧 Pro 项目必须显式迁移和重新确认，不能给旧批准补上未批准的新含义。预测数据泄漏检查、一般非线性证明尚未实现；自然语言题意是否被正确形式化仍需审题和数学评审。

## 修改影响与独立重放

```powershell
python "$plugin\scripts\change_impact.py" --project-root 'G:\Projects\my-contest' --changed 'paper_output_pro/data_cleaned/q2.csv'
```

影响分析连接回执中的输入、代码、规格、输出、指标、结论与章节，返回重算队列和依赖路径。省略 `--changed` 时比较已记录哈希。可选 `data_cleaned/provenance.json` 声明原始数据到清洗数据的哈希依赖；缺声明、未知代码或新输入会扩大影响范围。它不自动执行、不修改批准，也不减少全量冻结与最终同版审稿要求。

导出与执行分开：

```powershell
python "$plugin\scripts\replay_project.py" export --project-root 'G:\Projects\my-contest' --destination 'G:\Archive\my-contest-replay' --allow-input 'data_cleaned/data.json'
python 'G:\Archive\my-contest-replay\runner\run_replay.py' --output-root 'G:\Projects\my-contest-replay-run'
```

每个允许分发的输入分别提供一次 `--allow-input`，路径相对于 `paper_output_pro/`。未允许打包的输入只登记位置与哈希，重放前需用户补齐。包内包含冻结 Python 代码、依赖版本、比较规则和独立 runner；源项目须通过当前 P0–P6 校验。运行会写新的回执和一致性报告，不复制原项目批准。

当前重放只支持本地声明的 Python 依赖以及 exact/numeric 比较。统计等价规则、作为输入的其他实验输出暂不支持，明确阻断。环境或商业求解器缺失不会自动安装或购买。重放一致性通过不代表模型数学正确，也不授予新项目任何 Pro 阶段通过。

## 源码同步与发布

在仓库根目录执行：

```bash
python -B scripts/sync_platform_packages.py
python -B plugins/mathmodel/scripts/sync_plugin_skills.py
python -B plugins/mathmodel/scripts/sync_plugin_skills.py --check
python -B scripts/build_plugin_package.py
python -B scripts/build_plugin_package.py --verify
```

核心以 Claude canonical 为唯一源，先生成 Codex，再生成插件；插件入口单独保留。同步也维护插件根的核心依赖与 LICENSE。构建清单锁定 Pro 比较提交及所有有效载荷哈希，验证检查逐文件字节、版本和清单，不能仅凭同名文件判断 ZIP 新鲜。Standard 历史测试与 ZIP 通过隔离基线流程保留。
