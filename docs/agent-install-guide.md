# MathModel Skill Pro 通用安装

每版一份源码、一个 ZIP；版本内部原有协作 Skill 全部保留。安装位置不改变工作流。

### 1. 下载一个通用包

当前分支版本为 **3.3.0-pro.4**。下载 [MathModel-Skill-Pro.zip](https://github.com/yushui2022/MathModel-Skill/raw/refs/heads/pro/dist/MathModel-Skill-Pro.zip) 和 [SHA256SUMS.txt](dist/SHA256SUMS.txt)。这是分支构建，不是新建的正式 Release；历史 Release 平台包不作改动。

**同一份内容适用于不同宿主，不再分别下载 Claude、Codex、Trae 包。** ZIP 内有完整 `skills/`、安全安装器、依赖与启动说明。

### 2. 选择一个项目安装位置

先解压到独立下载目录，再执行（赛题目录必须已经存在）：

```bash
python "<解压目录>/install.py" --project-root "<赛题目录>" --platform codex --check
python "<解压目录>/install.py" --project-root "<赛题目录>" --platform codex
```

| 宿主 | 安装参数 | 项目内目标目录 |
|---|---|---|
| Codex | `--platform codex` | `.agents/skills/` |
| Claude Code | `--platform claude` | `.claude/skills/` |
| Trae | `--platform trae` | `.trae/skills/` |

一个项目只选一个位置。安装器仅使用 Python 3.11+ 标准库，不联网、不自动安装依赖，不覆盖 `AGENTS.md`、`CLAUDE.md`、其他 Skill、附件或已有论文。手动安装可完整复制 `skills/` 内全部目录到一个目标位置，不要只复制 `SKILL.md`。

无记录旧包、混装、用户修改和不完整安装会阻塞，不会自动清理。已托管且未改动的同主版本安装，先停止建模任务，再用 `--check --upgrade` 检查，确认后用 `--upgrade`；中断时用 `--recover` 回滚。安装器不重新批准任何旧证据。

### 3. 准备环境并启动

在选定的 Python 环境中手动安装依赖：

```bash
python -m pip install -r "<解压目录>/requirements.txt"
python -m pip check
```

把题面和原始附件放到赛题目录的 `problem_files/`，用宿主打开该赛题目录并刷新 Skill 列表。让 Agent 读取实际安装位置中的 **pro-workflow-orchestrator/SKILL.md**，按[启动提示词](pro-start-prompt.md)开始。

`<SKILL_ROOT>` 指实际加载的所有 Skill 的父目录，须替换为真实绝对路径；脚本从赛题根目录运行，不在安装目录生成结果。Pro 的平台参数仅记录宿主能力，不改变 payload。详细见[安装与恢复说明](agent-install-guide.md)。

Pro 的三次用户确认、独立复算和 Word/PDF 双门禁保持不变。安装到 Trae 或其他宿主不代表其多代理、联网或工具权限已验收；P0 必须记录实际能力，不具备隔离能力时不得伪造独立审稿。



## 校验与恢复

- `--check` 只读，列出拟执行操作；不会创建安装记录。
- 安装记录为项目内 `.mathmodel/install.json`，包含托管文件 SHA-256 和目标目录。它不是论文门禁。
- 内容完全相同的重复安装为无操作。版本不同必须显式 `--upgrade`，不支持降级、跨 edition 或跨主版本升级。
- 用户改动、未知同名文件、多位置安装、符号链接或目录联接会阻塞。可再生 Python 缓存不参与托管文件核验。
- `python "<解压目录>/install.py" --project-root "<赛题目录>" --recover` 只回滚经过日志与哈希验证的安装文件；日志中的文件若已被用户改动则停止，不删除修改。
- 无安装记录的手动安装可以运行，但不能自动纳入托管升级。旧包先备份并由用户处理，再重新安装。
- 不把下载包目录本身当作赛题项目；存放在项目下载子目录的包不会被递归误判为启用位置。
- 升级后重新预检，按该版本原有规则复核证据与交付门禁。不要在建模任务运行时升级。
- 安装测试证明文件与脚本行为，不等于真实宿主自动发现、多代理或模型成文质量已经实测。
