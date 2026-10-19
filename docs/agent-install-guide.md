# Standard 通用包安装指南

Standard 2.4 开发版只提供一个 MathModel-Skill-Standard.zip。Skill 内容不区分平台，只有安装位置不同。其他 edition 仍使用各自分支的安装说明。本开发版尚无正式 Release。

## 首次安装

需要 Python 3.11 或 3.12。安装器只使用标准库，不联网、不自动安装依赖、不写用户全局目录。

1. 下载通用 ZIP 和 SHA256SUMS.txt，核对下载完整性。哈希不是发布者身份签名，应从可信仓库获取安装器。
2. 解压到独立目录，创建另一个空的赛题项目目录，不把解压根当作赛题根。
3. 选择一个平台，先检查再安装：

```text
python "<解压目录>/install.py" --project-root "<赛题目录>" --platform codex --check
python "<解压目录>/install.py" --project-root "<赛题目录>" --platform codex
```

| 平台 | 参数 | 目标目录 |
|---|---|---|
| Codex | codex | .agents/skills/ |
| Claude Code | claude | .claude/skills/ |
| Trae | trae | .trae/skills/ |

必须明确选择平台，不自动猜测，也不会同时安装三份。路径含中文、空格时保留引号。
安装器只安装十个完整 Skill 目录，并写 .mathmodel/install.json 与安装锁；不会覆盖 AGENTS.md、CLAUDE.md、requirements.txt、其他 Skills、problem_files/ 或 paper_output/。

安装后刷新宿主的 Skill 发现或重新打开项目。让 Agent 读取实际安装目录中的 paper-workflow-orchestrator/SKILL.md。平台目录测试不等同于宿主自动发现功能已实测。

## 依赖与启动

在赛题使用的 Python 环境中运行，不必将依赖清单复制到项目根：

```text
python -m pip install -r "<解压目录>/requirements.txt"
python -m pip check
```

仅需要优化求解时安装 requirements-modeling.txt。LibreOffice 是正式 Word/PDF 渲染的必要依赖，不由安装器下载。
将题面、官方附件放在赛题目录的 problem_files/，向 Agent 发送：

```text
请读取已安装的 paper-workflow-orchestrator Skill，按 S0-S8 完成这个赛题。
从赛题根运行预检，真实执行计算，保留证据，完整章节写作，检查最终 Word/PDF。
不得把安装成功或 quickstart 草稿称为正式论文通过。
```

Skill 文档中的 <SKILL_ROOT> 指已加载 Skill 文件夹的父目录，替换成实际绝对路径；它不是环境变量。
脚本与资源相对安装位置定位，输入输出相对赛题根定位。不要切入 Skill 目录运行赛题。

## 手动安装

将通用包内 skills/ 下的十个完整目录复制到一个目标目录，不只复制 SKILL.md，也不要将外层 skills/ 再嵌套一层。
保留 scripts/、references/、agents/ 和 Edition marker。agents/openai.yaml 是可选宿主元数据，不影响通用正文。
合法手动安装可以运行，无需伪造安装记录；安装器不会自动接管它。

## 冲突与升级

一个项目只启用一个 edition、一个安装位置。预检扫描 skills/、.agents/skills/、.codex/skills/、.claude/skills/、.trae/skills/，识别旧入口及 Standard/Lite/Flash/Pro。
无记录旧包、缺文件、用户修改、额外自建文件、混装或另一安装位置均阻塞并列出冲突。先自行备份、整理冲突，再重新安装；没有 --force。
源码仓库和下载包是安装源，不是已启用安装；不要将其根目录作为赛题目录，项目子目录中的下载包不会被递归误判为安装。

有安装记录且内容未被修改时，可以显式升级到同一主版本内的新版本。先停止正在运行的建模任务：

```text
python "<新版解压目录>/install.py" --project-root "<赛题目录>" --platform codex --upgrade --check
python "<新版解压目录>/install.py" --project-root "<赛题目录>" --platform codex --upgrade
```

相同包重复安装不写文件。不支持降级、同版本不同内容替换、跨主版本或跨 edition 升级。
升级不会修改、重新签署或批准旧论文证据；之后重新运行预检，并按原有证据新鲜性规则复核后续门禁。

## 中断恢复

正常异常自动回滚；断电或进程被强制结束后，事务日志会使预检阻塞。用完整通用包中的安装器执行：

```text
python "<解压目录>/install.py" --project-root "<赛题目录>" --recover
```

恢复只回滚已记录且未被修改的安装文件。若暂存备份或目标被用户改动，恢复会停止，不覆盖这些改动。
不要手动编辑 install.json 或 transaction.json 来绕过冲突；安装记录不是论文门禁。
