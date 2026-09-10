# MathModel for Codex · 0.5.0-alpha.1

**在 Codex 对话里推进比赛，用项目文件保留判断、实验与论文的来龙去脉。**

MathModel Plugin 将数学建模专业 Skills、Pro 工作流、本地计算工具和可选证据工作台一起安装到 Codex。你负责提出问题、讨论路线和确认关键决定；Codex 按流程分析、编程、验证与写作，插件提供读取项目事实、管理实验和追踪结果的工具。

[项目首页](https://github.com/yushui2022/MathModel-Skill/tree/feat/codex-plugin) · [安装与环境](#安装与环境) · [开始与恢复](#开始与恢复) · [证据工作台](#实验与证据页面) · [实际实施记录](https://github.com/yushui2022/MathModel-Skill/blob/feat/codex-plugin/docs/plugin-upgrade-validation.md)

## 为什么使用插件

当一场比赛跨越多个会话、包含多问和多轮实验时，仅靠聊天记录很难持续回答“为什么选这个模型”“这个结果用的是哪版数据”“论文哪些地方需要跟着改”。插件从项目中已保存的题意、路线、运行回执和论文契约恢复这些信息，让 Codex 根据当前证据继续。

| 你需要的帮助 | 插件提供什么 |
|---|---|
| 新会话接着做第二问 | 按小问恢复假设、模型决策、实验、结论及写作位置，附来源与状态 |
| 计算过程可查、可停、可重试 | 持久任务队列、实际日志、进程归属、退出结果与独立重试记录 |
| 检查程序有没有解错数学规格 | 对声明的 LP/MILP 目标、约束、变量域及适用的界证书进行独立检查 |
| 数据变更后知道要改哪里 | 解释输入、代码、实验、结论和章节之间的已声明依赖与失效影响 |
| 将关键结果交给队友复算 | 导出冻结代码、允许分发的输入、依赖版本和独立重放入口 |
| 随时查看论文及计算证据 | 在可选工作台预览项目文件、图表、表格、代码和 PDF |

当前 Alpha 使用 **Pro 3.3.0-pro.1** 核心，唯一正式流程是 P0–P9。多个 Skill 的组合负责分工与按需读取，MCP 负责工具调用，本地服务负责实际任务和状态；它们不会扩大模型上下文或自动创造独立审稿 Agent。

Pro 原有的三路审题、多路线比较、独立复算、稳健性、三个确认点、证据冻结和五角色审稿继续生效。插件新增的工程功能与有限范围数学检查不构成真实竞赛质量提升的证明。

## 安装与环境

### 1. 获取完整插件

下载 [MathModel-Codex-Plugin.zip](https://github.com/yushui2022/MathModel-Skill/raw/refs/heads/feat/codex-plugin/dist/MathModel-Codex-Plugin.zip)，解压到名为 `mathmodel` 的目录；也可以使用本仓库的 `plugins/mathmodel/`。完整目录应包含：

```text
mathmodel/
├── .codex-plugin/plugin.json    插件身份与能力入口
├── .mcp.json                   MCP 启动描述
├── core.lock.json              固定的 Pro 核心信息
├── skills/                     Pro 专业 Skills 与插件入口
├── scripts/                    运行、恢复、检查及安装工具
├── dashboard/                  可直接使用的前端资源
├── requirements.txt
└── core-requirements.txt
```

使用完整目录，不单独复制入口 `SKILL.md`。普通使用不需要 Node.js 或前端构建环境。

### 2. 安装到 Codex

当前采用第三方本地插件分发。在支持个人插件的 Codex 版本中，可以把下载目录交给 Codex，明确要求安装，例如：

> 请把 `G:\Plugins\mathmodel` 安装为我的个人 Codex 插件。使用当前宿主支持的插件安装流程，确认 MathModel 已启用，并告诉我实际安装目录。之后为它准备独立的 Python 运行环境。

将上面的目录换成实际解压位置。该步骤需要完成个人 marketplace 登记和插件安装；**把 ZIP 下载到磁盘不等于已经启用插件**。若 `mathmodel` 已登记在本机 `personal` marketplace，可通过支持插件命令的 Codex CLI 安装或重装：

```text
codex plugin add mathmodel@personal
```

此命令要求对应本地条目已经存在。发布到 GitHub、提供自建 marketplace 都不会自动进入所有用户的官方插件列表。不同宿主的导入界面与 CLI 能力可能不同；本机验证过的安装方式见[实施记录](https://github.com/yushui2022/MathModel-Skill/blob/feat/codex-plugin/docs/plugin-upgrade-validation.md)。

### 3. 准备一次 Python 环境

建议 Python 3.11/3.12。`requirements.txt` 固定 MCP SDK 依赖，`core-requirements.txt` 提供 Pro 建模依赖；正式 Word/PDF 交付还需要 LibreOffice。比赛目录只放赛题与比赛产物，避免再装第二套 MathModel Skill。

下面是 Windows 示例。`$plugin` 必须替换为上一步返回的**实际安装根目录**，运行环境放在插件缓存外的可写位置：

```powershell
$plugin = '<Codex 返回的实际插件安装根目录>'
$runtime = 'G:\DevCache\MathModelRuntime'

python "$plugin\scripts\setup_runtime.py" --runtime-root $runtime --install-deps --register-codex
```

该命令在运行目录创建 venv、安装依赖、生成 `mcp.local.json`，进行真实 MCP 连接探测，并通过 `codex mcp add` 注册绝对启动命令。CLI 不在 PATH 时加 `--codex <codex 可执行文件完整路径>`；只想生成配置时省略 `--register-codex`。

已有环境可以省略 `--install-deps`；运行目录内已有 `.venv` 时默认复用，或用 `--python <解释器完整路径>` 指定。非 Windows 环境可使用相同 Python 脚本及参数，将运行目录换为本机可写路径，venv 的解释器通常位于 `.venv/bin/python`。

之后的手动命令使用这个已准备好依赖的解释器。Windows 示例：

```powershell
$runtimePython = Join-Path $runtime '.venv\Scripts\python.exe'
& $runtimePython "$plugin\scripts\setup_runtime.py" --project-root 'G:\Projects\my-contest'
```

环境诊断会报告实际版本、缺失依赖与项目重复入口。`PROTOCOL_VERIFIED` 表示生成的配置可启动并连接 MCP；`READY` 表示所检查的依赖和项目入口满足诊断要求。

插件自带相对路径的 `.mcp.json`。宿主解析有问题时，使用安装脚本生成的绝对配置；注册默认更新 `mathmodel`，也可用 `--server-name` 指定名称，确保活动配置明确。设置写入运行目录或所选 Codex 配置，比赛结果写入比赛目录。

### 4. 用新任务开始

安装或更新后，在 Codex 的比赛项目中新建一个任务，让宿主加载新版 Skills 与 MCP 工具。已有比赛先读取恢复状态。更新后若实际安装目录变化，应重新运行配置步骤，避免绝对 MCP 命令仍指向已清理的旧缓存。

## 开始与恢复

把题面和附件放入比赛项目的 `problem_files/`，对 Codex 说：

> 开始建模。先检查输入、实际模型和推理档位，再按 MathModel Pro 推进；涉及确认时给出当前题意、路线或结果的具体对象。

首次使用会先审计指令、解析问题并整理可讨论的题意。Pro 保留三个确认点：题意与范围、模型路线、结果与不确定性；每次展示具体对象后记录用户的真实决定。已有有效批准可以继续使用，批准对象变化时重新核对。

恢复时可以说：

| 你说 | Codex 应读取并说明 |
|---|---|
| “继续第二问” | 第二问的当前目标、依赖、选中路线、已有结果和下一步 |
| “为什么没用另一个模型？” | 项目中记录的比较与淘汰理由；缺失理由明确说明未知 |
| “查看尚未解决的审稿意见” | 与当前稿件版本对应的问题、证据和修订位置 |
| “准备交付” | 当前门禁、证据冻结、格式及渲染检查，以及仍需解决的问题 |

无需先打开看板。调试时可直接读取恢复包：

```powershell
& $runtimePython "$plugin\scripts\build_context_packet.py" --project-root 'G:\Projects\my-contest' --question q2 --format markdown
```

`q2` 必须是题意契约中实际存在的小问 ID；读取全项目时省略 `--question`。恢复包包含事实来源、哈希、当前状态、小问定位、验收范围和下一 Skill；分页依照返回的游标与版本继续读取。完成项目不再分派重复写作任务，输入或稿件变动后按当前验证结果重新决定下一步。

默认读取不写 QA 或 memory，显式 `--write` 才保存 `.mathmodel/context/resume.json`。`pro_status.py` 通过现有 Pro 校验器只读重建状态；旧 memory 与当前门禁冲突时，以当前文件和门禁为准。

普通状态查询的退出码 0 表示查询完成。需要检查成功的进程退出语义时，使用 `--fail-if-blocked`；`--require-through P5` 检查到证据确认，`P6` 检查到冻结，默认 `P9` 要求全程通过。`current` 事实也只表示相应记录可追溯，不是正式论文验收。

## 实验与证据页面

工作台为对话提供可查看的依据，模型讨论和正式写作仍留在 Codex。页面按当前项目展示五个视图：

| 视图 | 内容与操作 |
|---|---|
| **总览** | 当前问题、恢复摘要、下一步、有效阶段与最新产物，可复制摘要回到对话 |
| **流程** | P0–P9 当前检查结果、失败或失效原因；显示已验证阶段数，不猜测耗时百分比 |
| **实验** | 实际运行回执、结果、图表与指标；没有可比较数据时明确显示空状态 |
| **代码** | 带行号的只读代码、实际作业日志、退出状态与可用的取消/重试操作 |
| **交付** | Markdown 正文、Word 下载、PDF 页面预览及格式和评审文件 |

项目文件树包含题面、附件和登记产物，自动读取当前文件变化。页面支持浅深色和窄面板；它不提供完整 IDE 的编辑器、终端或调试器。缺少宿主消息桥时，通过“复制恢复摘要”继续对话。

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
& $runtimePython "$plugin\scripts\workspace.py" open --project-root 'G:\Projects\my-contest'
```

该入口启动或复用比赛项目服务，返回实际 `dashboard_url`。Codex 可通过宿主 `open_in_codex` 在右侧打开该地址。服务仅监听回环地址，页面需要当前服务令牌；是否自动打开由宿主能力决定。普通浏览器可使用同一页面，本版本不承诺 MCP Apps 或无条件自动打开面板。

## 有限范围的数学检查

插件预检启用 `optimization_check_profile=linear-v1`。获选与备用路线须声明 LP、MILP 或有实质理由的范围外情况。LP/MILP 规格在检查点 2 前绑定变量、目标、约束和数据；独立检查器计算残差与目标，定位违规约束，区分可行与有证书支持的最优界。

模型自己填写的 `feasible=true` 或求解器 `optimal` 文本不能代替核验。修改规格或适用性会使批准失效；旧 Pro 项目必须显式迁移和重新确认，不能给旧批准补上未批准的新含义。预测数据泄漏检查、一般非线性证明尚未实现；自然语言题意是否被正确形式化仍需审题和数学评审。

## 修改影响与独立重放

```powershell
& $runtimePython "$plugin\scripts\change_impact.py" --project-root 'G:\Projects\my-contest' --changed 'paper_output_pro/data_cleaned/q2.csv'
```

影响分析连接回执中的输入、代码、规格、输出、指标、结论与章节，返回重算队列和依赖路径。省略 `--changed` 时比较已记录哈希。可选 `data_cleaned/provenance.json` 声明原始数据到清洗数据的哈希依赖；缺声明、未知代码或新输入会扩大影响范围。它不自动执行、不修改批准，也不减少全量冻结与最终同版审稿要求。

导出与执行分开：

```powershell
& $runtimePython "$plugin\scripts\replay_project.py" export --project-root 'G:\Projects\my-contest' --destination 'G:\Archive\my-contest-replay' --allow-input 'data_cleaned/data.json'
& $runtimePython 'G:\Archive\my-contest-replay\runner\run_replay.py' --output-root 'G:\Projects\my-contest-replay-run'
```

每个允许分发的输入分别提供一次 `--allow-input`，路径相对于 `paper_output_pro/`。未允许打包的输入只登记位置与哈希，重放前需用户补齐。包内包含冻结 Python 代码、依赖版本、比较规则和独立 runner；源项目须通过当前 P0–P6 校验。运行会写新的回执和一致性报告，不复制原项目批准。

当前重放只支持本地声明的 Python 依赖以及 exact/numeric 比较。统计等价规则、作为输入的其他实验输出暂不支持，明确阻断。环境或商业求解器缺失不会自动安装或购买。重放一致性通过不代表模型数学正确，也不授予新项目任何 Pro 阶段通过。

## 常见问题

**我已经装了 Pro Skill，还需要插件吗？**

如果现有 Pro 流程已经满足需求，可以继续使用独立 Skill。需要在 Codex 中统一管理跨会话恢复、后台实验、修改影响和证据预览时，插件更合适。同一比赛项目只保留一个活动 MathModel 入口，避免重复安装造成指令与版本混用。

**插件会帮我自动写出高质量获奖论文吗？**

它提供可执行的流程、证据检查和恢复工具。论文质量仍取决于题意理解、模型合理性、有效数据、实验设计与论证。当前 Alpha 尚未完成真实赛题相对 Pro 的对照盲评；工程样例的 `ENGINEERING_SMOKE_ONLY` 也不代表比赛论文验收。

**MCP 是不是另一套 AI？**

MCP 是 Codex 调用本地工具的接口。建模判断仍在当前对话中进行；`get_next_action` 返回建议和对应 Skill，不在后台启动另一套模型或自动创建审稿者。

**工作台关掉，任务和记忆会丢吗？**

项目记录保存在磁盘，页面与实验独立。重新打开会读取当前状态；异常退出的实验保留日志并标记可判断的状态，是否能从求解器内部断点继续取决于实验代码。

**能直接打开以前的 Standard 项目吗？**

当前插件正式入口是 Pro，产物根为 `paper_output_pro/`。Standard 使用 S0–S8 和 `paper_output/`，旧批准不会自动转换。旧项目继续使用对应版本；不要将历史示例的 PASS 当作新插件的当前验收。

## 开发者：源码同步与发布

在仓库根目录执行：

```bash
python -B scripts/sync_platform_packages.py
python -B plugins/mathmodel/scripts/sync_plugin_skills.py
python -B plugins/mathmodel/scripts/sync_plugin_skills.py --check
python -B scripts/build_plugin_package.py
python -B scripts/build_plugin_package.py --verify
```

核心以 Claude canonical 为唯一源，先生成 Codex，再生成插件；插件入口单独保留。同步也维护插件根的核心依赖与 LICENSE。构建清单锁定 Pro 比较提交及所有有效载荷哈希，验证检查逐文件字节、版本和清单，不能仅凭同名文件判断 ZIP 新鲜。Standard 历史测试与 ZIP 通过隔离基线流程保留。
