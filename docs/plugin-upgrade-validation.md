# MathModel Plugin 0.5.0-alpha.1：实施与验证记录

日期：2026-09-10。本记录区分已实现代码、已运行工程测试与尚未完成的产品/竞赛验收。对应设计为 [plugin-pro-upgrade-plan.md](./plugin-pro-upgrade-plan.md)；本文不是稳定版发布声明。

## 比较基线与源码边界

| 对象 | 固定版本或提交 | 本轮处理 |
|---|---|---|
| Pro 比较基线 | `3.3.0-pro.1` / `da520d49c62c8f5dc3755eb16bedefd78e77b466` | 受控引入核心、依赖、契约文档与原测试；新增优化验证和读取接口在此基础上实现 |
| Standard 历史基线 | `2.3.0` / `0cc261d90d21e4ed540b02b0c71018cdcd47af58` | 原测试断言、历史平台 ZIP 与独立分发入口保留 |
| 插件计划比较点 | 已提交 `0.3.0` / `cbd6c75b2c52b15841316bb091697980792c426d` | 另有原工作区 `0.3.1` 改动；它不是已发布的 Pro 插件基线 |
| 本轮候选版本 | `0.5.0-alpha.1` | Pro 集成及有限新增功能，尚无真实赛题对照质量结论 |

唯一核心源码链：Claude canonical → 生成 Codex → 生成插件 Skills。`mathmodel-plugin-entry` 是插件专属入口。同步检查还包含插件根的 `core-requirements.txt` 与 LICENSE；构建检查 Pro edition lock、入口、依赖文件和逐文件哈希，不接受源代码同名但字节已变的旧 ZIP。

Standard 和 Pro 原测试各自在固定提交的隔离布局中执行。Pro 测试树覆盖当前 canonical/Codex 核心；Standard 使用原源码与原断言。本分支不通过删除历史断言或重建 Standard ZIP 来迁就 Pro 目录。

## 继承与新增

Pro 原有三路独立审题、多路线锦标赛及淘汰理由、预登记比较规则、真实执行回执、独立复算、稳健性实验、三个用户确认点、冻结、双向结论映射、五角色审稿与 Word/PDF 检查。这些能力没有计作插件新增卖点。

本轮增加了：按小问与来源版本组织的恢复/交接包；由项目服务维护的实际计算作业；限定 LP/MILP 的独立规格检查；输入/代码/规格到实验、指标、结论和章节的修改影响说明；含独立 runner 的冻结重放包。任何进程成功、上下文事实状态或重放一致性结论，都不授予新的正式 Pro 批准。

## 里程碑实际状态

| 里程碑 | 已落地 | 验收边界或未完成部分 |
|---|---|---|
| M0 运行与安装可靠性 | 项目服务、作业持久化、进程归属、HTTP/路径边界、幂等键、包字节验证、绝对 MCP 配置及协议探针 | 本机安装与协议已验证；不宣称覆盖全部宿主 |
| M1 Pro 核心接入 | 固定 Pro 源码、P0–P9 只读状态、真实检查点与门禁、单向生成链、历史基线保留 | 旧项目的安装指令或批准对象变化时仍须按 Pro 重新审计/确认 |
| M2 恢复与交接 | 按问题恢复、来源哈希、版本化分页、具体 Skill/产物交接包、实际计算任务与日志 | 宿主角色执行记录自动收集/核验的新适配尚未完成；独立角色与五角色要求主要继承 Pro。没有证明任意新会话都能正确使用恢复包 |
| M3 数学规格 | LP/MILP 的变量域、目标、约束、可行性及适用界证书检查；绑定 P2/P3/冻结/最终门禁；显式迁移 | 不覆盖一般非线性问题；自然语言形式化仍需人/模型审查；预测题数据泄漏检查尚未实现，未完成真实优化赛题质量验收 |
| M4 影响与重放 | 声明依赖图、保守影响扩展、拓扑重算建议、只读 P0–P6 源准入、显式输入授权、独立 runner、新运行比较报告 | 无法证明任意动态文件/网络读取依赖完整；重放仅 exact/numeric，本轮拒绝统计等价和以其他实验输出为输入的运行链 |
| M5 页面与发布 | 同一服务、实际浏览器图表/表格/代码/PDF 预览、本机插件安装、README、基线 CI、发行包校验 | 新任务自然语言自动打开尚未单独验收；24 组真实赛题盲评尚未进行，不能标全部里程碑完成 |

## 已执行的工程验证

本机为 Windows、Python 3.11。科学计算依赖已有于本机环境；缺少的 PyMuPDF 安装在 G 盘临时依赖目录。隔离测试、venv、缓存和临时 ZIP 均在 G 盘。完整流水线使用真实 LibreOffice。以下数目按各自测试运行记录填写，不把测试夹具的批准、审稿记录或论文当成真实竞赛成果。

| 检查 | 已通过结果 | 证明范围 |
|---|---|---|
| 固定 Standard 原回归 | 42 项 | 在原布局执行，断言未删 |
| 固定 Standard 范围/渲染回归 | 14 项；历史 ZIP 验证通过 | 保留历史版本的交付和分发基线 |
| 原 Pro 回归覆盖当前核心 | 81 项，启用 `REQUIRE_LIBREOFFICE=1` | 包含实际实验、独立复算、真实 DOCX/PDF 流水线及错误注入；不是赛题盲评 |
| 纯 Pro 状态 | 8 项 | 文件字节和 mtime 不变；拒绝伪最终 PASS/过期批准；完整真实合成流水线可读为完成，论文修改后不能继续验收 |
| LP/MILP 独立检查 | 31 项 | 容量、目标、整数域、固定容差、证书、迁移和门禁绑定等回归 |
| 修改影响 | 11 项 | 小问专用输入、共享代码、跨运行次序、真实审稿哈希关联的措辞变化、缺依赖保守处理与路径拒绝 |
| 独立重放 | 16 项 | 真实插件 P0–P6 准入、原始输入修改后拒绝导出、干净无 pip venv 使用导出 runner、缺输入/依赖、篡改、数值差异和不支持的跨运行输入 |
| 插件打包 | 8 项 | 两次构建字节相同；源/ZIP 篡改、版本或核心漂移、重复/额外条目、依赖与许可证缺失均检出 |
| 历史发布入口保护 | 3 项 | 错误核心版本下，旧 Standard 构建/清理/验证命令在写入前阻断；历史 ZIP 字节与时间戳不变；两个隔离平台包检查仍通过 |
| 核心实验日志容量 | 8 项真实进程测试 | stdout/stderr 每流保留最多 2 MiB，继续排空避免死锁；回执记录实际读取/保留字节与截断状态，截断为 FAILED，保留实际退出码；覆盖双流、UTF-8、超量、watchdog 与后代持有管道 |
| 源码同步与清单 | 两级 `--check`、官方 plugin validator、最终 ZIP 字节/清单验证与两次构建哈希一致 | 验证最终插件有效载荷，不把版本号视为结果保证 |
| 上下文恢复 | 10 项通过 | 纯读取、伪回执、来源分页、活动不扰动分页、畸形结构/文件路径、跨项目记忆与失效诊断 |
| 持久任务运行 | 11 项通过 | 顺序队列、幂等与输入变化、独立重试、子进程树取消、日志容量及恢复 |
| Workbench 兼容 | 3 项通过 | 人工 PASS 不晋级、路径边界与原有恢复接口 |
| HTTP 边界 | 8 项通过；PDF 接入后再次通过 | 单服务、Host/Origin/令牌、跨客户端恢复、MIME、日志与路径边界 |
| PDF 页面预览 | 7 项通过 | 实际 PNG 渲染、密码/损坏/页码、输入/输出/像素上限、超时/并发与 Windows junction 拒绝 |
| 发行物安装与官方 MCP | 1 个完整集成场景通过 | ZIP 解压只读安装、独立中文空格目录、协议初始化、两客户端同服务、产物读取、真实检查与安装目录字节不变；Windows 使用只读文件标记，未使用拒绝写入目录 ACL |

核心日志修改已同步到 Codex 与插件；修改后的原 Pro 81 项全量回归于本轮再次通过（85.383 秒，包含实际 LibreOffice 渲染）。此表不宣称尚未执行的 CI 矩阵已经远程通过。

### 本机安装与桌面验收

已使用官方 Codex CLI `0.154.0` 从既有 `personal` marketplace 重装。发行 ZIP 为 `dist/MathModel-Codex-Plugin.zip`，版本 `0.5.0-alpha.1`；本机开发安装带官方 cachebuster 后缀 `+codex.20260910124703`。CLI 再读取确认 `mathmodel` 已启用，绝对命令指向安装缓存中的 MCP 脚本。最终发行 ZIP SHA-256：`bc9bd96efdd8ee20f1190a0cfacd15481f4641c745eb75fec54cfee42e0ec30c`。

运行环境位于 `G:\DevCache\MathModelRuntime\.venv`。完整依赖安装和 `pip check` 通过，doctor 为 READY；实际 MCP 连接发现 13 个工具。插件相对配置没有被当作已验证的宿主插值；本机使用安装脚本生成并通过 `codex mcp add` 注册的绝对配置。当前 SDK 与新版 pydantic-settings 有 lifespan 注解警告，实际协议与任务正常。

Codex 内置浏览器检查了 420、820、1360 CSS 像素及浅深色页面，未发现页面水平溢出。实际操作验证导航、文件选择/折叠、代码行号、CSV 表格与科学图、证据检查任务/日志以及 PDF 翻页。取消、重试与多客户端恢复的进程行为由 HTTP/runtime 集成测试验证，没有宣称所有桌面按钮都已逐个点击验收。

原生 PDF iframe 在本机显示空白，现改为隔离子进程解析实际 PDF 并返回 PNG。实际观察到 1190×1683 的论文页面，上一页/下一页边界有效，刷新后仍停留第 2 页；原文件可下载。接口最多两路并发、12 秒超时、500 页、250 万像素、25 MiB PDF 和 8 MiB 图片。

工程项目“工程合成场景_配送设施选址”使用 6 次 SciPy/HiGHS 与枚举计算产生真实指标、图表和两页 PDF。题目、模拟批准/评审及界面均标记 `ENGINEERING_SMOKE_ONLY`。实际修改已选代码后，页面自动显示新内容，验证阶段从 10/10 降为 3/10；恢复原字节后重新核验。服务升级重启后保留前一次检查任务与日志。

右侧 `open_in_codex` 请求已提交，内置浏览器真实页面已验证。新安装的 Skills/MCP 需要新任务加载；“在全新任务中只说开始建模即自动打开”的整条宿主流程仍待单独验收。没有宣称 MCP Apps、画中画或所有 Codex 版本支持完整工作台。

## 可复现检查命令

在本地先准备依赖和 G 盘测试缓存；Linux CI 则使用 runner 的临时目录。

```powershell
$env:MATHMODEL_TEST_TEMP = 'G:\DevCache\Temp\mathmodel-plugin'
$env:MATHMODEL_TEST_TMP = $env:MATHMODEL_TEST_TEMP
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:REQUIRE_LIBREOFFICE = '1'
python -B scripts/sync_platform_packages.py --check
python -B plugins/mathmodel/scripts/sync_plugin_skills.py --check
python -B scripts/run_baseline_tests.py --edition standard
python -B scripts/run_baseline_tests.py --edition pro
python -B -m unittest discover -s tests -p test_pro_status.py -v
python -B -m unittest discover -s tests -p test_optimization_spec.py -v
python -B -m unittest discover -s tests -p test_plugin_dependencies.py -v
python -B -m unittest discover -s tests -p test_plugin_replay.py -v
python -B -m unittest discover -s tests -p test_plugin_packaging.py -v
python -B scripts/build_plugin_package.py
python -B scripts/build_plugin_package.py --verify
```

CI 配置为 Windows/Ubuntu、Python 3.11/3.12；所有 checkout 使用 `fetch-depth: 0` 取得固定基线对象。插件测试文件在独立 Python 进程运行，避免测试夹具把不同安装位置的 Pro 模块混入同一模块缓存。单独的 LibreOffice 任务运行完整 Pro 与历史 Standard 流水线。构建比较写 runner 临时目录，不覆盖仓库历史 Standard ZIP。

测试缓存路径在步骤执行时从 `RUNNER_TEMP` 配置，不在 workflow/job 级 `env` 使用尚不可用的 `runner` context；使用范围依据 [GitHub Actions contexts reference](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#context-availability)。

## 真实限制与后续验收

- 新宿主角色执行来源适配尚未形成自动闭环；手工填写的 execution ID 不能变成宿主执行证明。
- M3 检查的是明确声明的数学规格，不能证明规格完整表达题意。范围外与未知必须保持可见，不能贴换标签掩盖失败。
- 影响图基于已声明文件关系。无法证明完整时扩大重算建议；保留历史运行仍须重新通过当前 Pro 规则。
- 重放不自动解决商业求解器、本机二进制依赖或数据分发权限；未包含的输入需要明确补齐。代码输出一致不等于模型正确。
- 当前 Alpha 没有完成 24 组真实赛题、相同模型和预算下的 Pro 对照盲评。不能把工程测试项数、页数或版本号作为论文质量提升证据。
- 稳定版前仍需完成新任务自然语言接入、支持宿主矩阵与真实赛题对照；本机浏览器和工程协议测试不替代这些验收。
