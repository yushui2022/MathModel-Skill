---
name: mathmodel-plugin-entry
description: Start or resume a mathematical-modeling contest in Codex using the Pro workflow. Recover a specific question's model decisions and current experiments, inspect changed evidence, or open the optional project companion. Use for modeling work, not for developing the plugin itself.
---

# MathModel 插件入口

对话负责审题、选模、论证和正式写作。插件绑定项目、恢复事实并运行可核验的计算。
正式工作流唯一入口是 `pro-workflow-orchestrator`，阶段 P0–P9，产物根为
`paper_output_pro/`。不要激活 Standard/Lite 入口或把旧版本 PASS 转成 Pro PASS。

## 每次开始或换会话

1. 从当前任务工作目录、用户指定目录和 `problem_files/` 确认实际比赛根。
   插件安装根与比赛根不同。根据本文件绝对位置向上两级定位插件根；通用脚本用
   插件绝对路径调用，赛题路径显式传入。不要向安装缓存写依赖或结果。
2. 使用 MCP `doctor` 核对活动插件、依赖和项目重复安装。MCP 不可用时运行：

   ```text
   python <插件根>/scripts/setup_runtime.py --project-root <比赛根>
   ```

   需要首次环境准备时，运行 `setup_runtime.py --runtime-root <可写运行目录>
   --install-deps`。Windows 优先 G 盘已有开发目录；其他环境使用用户可写的数据目录。
   该脚本生成已进行真实协议探测的绝对路径 MCP 配置，不依赖环境变量插值。
   宿主无法解析包内相对路径时按 [运行与安装](references/runtime.md) 注册本机配置。
3. 调用 `get_context_packet(project_root, question_id)`；“继续第二问”对应题意契约中
   实际存在的 question ID，不猜不存在的 ID。MCP 不可用时：

   ```text
   python <插件根>/scripts/build_context_packet.py --project-root <比赛根> --question q2 --format markdown
   ```

   全项目省略 `--question`。此命令默认只读，读取当前 Pro 验证器，不信任旧报告、
   聊天记忆或手工活动。若返回分页，读取当前任务所需的后续事实和来源文件。
4. 简短说明当前问题、已选模型及理由、有效结果、未决问题和下一步。摘要中每条事实
   都有来源。`current` 仅表示运行记录哈希有效；`recorded` 不是数学正确性的证明。
   `stale/unknown` 不可作为已确认结论。没有记录的淘汰理由保持未知。
5. 读取返回的 `handoff.skill_path` 并继续唯一 Pro 流程。用户指定的小问不能绕过
   前置问题依赖、失效证据或必要检查点。Pro P0 的全指令审计仍须执行；其后按阶段
   读取所需 references，不重复加载整个模型知识库。

模型和推理档位使用宿主实际可见设置或用户明确声明；不可见时说明缺少的信息，
不从产品名推断。工具是否支持独立上下文也按实际能力记录。

## 计算、检查与修改

- 使用 `run_job` 提交明确类型。Pro 预检传实际 `model/reasoning`；模型实验传
  `options.spec="code/<规格>.json"`。通过 `get_job` 分页读取日志，取消只用 `cancel_job`。
  页面和 MCP 连接同一项目服务，关闭页面不会终止计算。详见
  [运行与安装](references/runtime.md)。
- 本插件新建项目的预检启用 `optimization_check_profile=linear-v1`。P2 前读取
  QA Skill 的 `references/optimization-checks.md`，为全部获选/备用路线声明适用性。
  LP/MILP 提供独立数学规格、数据和预登记容差；其他题型记录具体不适用理由。
  不把复杂模型强行改写为线性规划。先检查规格，再向用户展示并正常批准检查点 2。
- 数学规格、容差和数据纳入批准哈希。实际实验要产出可检查的解，执行
  `pro_optimization.py`；启用该配置后正式 Pro gate 也会检查，不能只依赖提示词。
  旧项目缺此批准链返回 `MIGRATION_REQUIRED`，不能声称已经具备新增验证。
- 修改输入、共用代码或结论时读取 `get_change_impact`。沿返回的依赖路径安排必要
  重算；缺少数据处理依赖会保守扩大范围。影响分析不自动批准、不跳过最终全量审稿。
- 收到任务结果后重新读取恢复包，核对输入版本。过期结果保留为历史，不覆盖当前
  结论。需要持久摘要时显式执行 `build_context_packet.py --write`；它只写
  `.mathmodel/context/resume.json`，不改 Pro 批准和 QA。

## 独立角色与论文

多个 Skill 不等于多个独立 Agent。审题、独立复算和五角色审稿按 Pro 要求通过
宿主真实隔离上下文执行，保存宿主返回的任务 ID、输入版本、实际结果与执行记录。
评审 prepare 只生成待执行任务，不能用五个角色标签或模拟记录冒充真实评审。

正常流程保留三个 Pro 确认点：题意/范围、模型路线、结果/不确定性。展示具体结果
后记录用户实际决定；已经有效的批准不重复请求。变更了批准对象则按 Pro 规则重核。
其余已授权且可逆的工作继续推进，不把每个 Skill 交接变成额外确认。

正式写作只读取当前冻结证据并维护唯一 `final_paper_source.md`。数字有来源还不够，
逐问解释假设、推导、方法、结果、验证及局限；发现证据不足返回计算。
最终 Word、PDF、真实逐页视觉检查与五角色同版审稿仍全部保留。

## 右侧伴侣与交付

用户说“打开工作台”时调用 `open_workspace`，用实际返回的 `dashboard_url`
交给宿主 `open_in_codex` 的 browser target，placement=right。没有该能力时返回
本地 URL。MCP 不可用时 `workspace.py open --project-root <比赛根>` 提供同一入口。
只有健康检查成功的 URL 才能展示，不能编造端口；页面不创建第二个建模 Agent。

右侧按当前问题显示恢复事实、实际运行、产物及验证；模型讨论继续留在对话。
普通浏览器通过“复制恢复摘要”回到对话。不要宣称宿主保证 fullscreen 或 MCP Apps。

需要移交复算时调用 `export_replay`，只打包用户已授权分发的输入清单。使用
`replay_project.py run` 在新目录执行，结果是独立重放一致性报告，不是新项目 Pro PASS。
当前重放仅支持 Python、预登记 exact/numeric 比较；缺依赖、缺输入及未覆盖的统计
规则明确报出。不得把工程测试通过描述为优秀论文或获奖保证。
