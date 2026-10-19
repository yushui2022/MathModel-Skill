# Standard 宿主发现验收

验收日期：2026-10-19。范围仅为 Standard 通用包的安装与宿主发现，不增加建模功能，不测试付费模型，不自动升级用户的工具。

最终复测的 `MathModel-Skill-Standard.zip` SHA-256：`fbf7df39c7a665e64374eead036d4e013d6b9603b274c4251af839230e7e75cc`。该包已包含本次兼容性说明；Codex 与 Claude Code 均从该 ZIP 重新安装后复测，不只复用旧项目结果。

## 结果

| 宿主 | 验证方式 | 结果 |
|---|---|---|
| Codex 桌面内置引擎 `0.163.0-alpha.10.2` | 真实 app-server 进程，`initialize` 后请求 `skills/list`，强制刷新项目目录 | 十个 Skill 全部发现，`scope=repo`、`enabled=true`，无发现错误 |
| 本机 PATH 中的 Codex CLI `0.88.0` | 对同一 `.agents/skills/` 项目执行相同发现请求 | 十个项目 Skill 全部缺失；返回的只有宿主自身系统 Skill |
| Claude Code `2.1.150` | 标准启动模式，流式控制协议仅发送 `initialize` | 十个项目 Skill 全部出现在命令列表，描述标记为 `(project)` |
| Claude Code `2.1.150 --bare` | 对同一项目执行初始化 | 初始化列表没有项目 Skill；不将最小模式结果误判为标准模式失败 |
| Trae `3.5.71` | 已验证安装到 `.trae/skills/`；GUI 验收按用户要求暂缓 | **未完成宿主发现验收** |

发现验收检查的十个名称与安装包清单一致：

```text
authoritative-data-harvester
context-memory-keeper
data-cleaning-and-visualization
model-code-and-result-generator
modeling-paper-rubric-and-model-selector
paper-formal-writer
paper-micro-unit-generator
paper-workflow-orchestrator
problem-doc-model-selector
quality-assurance-auditor
```

## 方法与边界

1. 从真实通用 ZIP 解压，以 Python 3.11 和 `install.py` 安装到三个独立的中文、空格路径项目，没有手工补文件或制作旧目录副本。
2. 为每个探针设置独立 HOME、USERPROFILE、CODEX_HOME、CLAUDE_CONFIG_DIR 和临时目录，全部位于 G 盘；不使用已有项目、插件目录或用户全局配置作为安装目标。
3. 移除继承的模型凭据，将测试进程的模型基础地址和代理指向本机不可用端口。Claude 关闭 hooks、用户设置、会话保存和外部 MCP；不发送用户消息。Codex 不调用 thread/turn 启动接口。
4. 以宿主返回的项目 Skill 名称、描述、实际路径与错误列表为证据，不以文件存在、测试中的模拟列表或模型口头声称作为发现成功。
5. 测试进程结束后关闭，不更新全局 CLI，不把安装成功标为论文门禁 PASS。

Codex 协议以本机二进制生成的 JSON schema 为准；Claude 的初始化封装参照 [Anthropic Agent SDK 控制协议](https://github.com/anthropics/claude-agent-sdk-python/blob/main/src/claude_agent_sdk/_internal/query.py)。本次调用只用于读取命令元数据。

成功发现意味着宿主已经解析项目 Skill 元数据，不代表模型已经读完正文、能正确选择 Skill、执行 S0-S8 或产出约 20 页的合格论文。那些需要另行授权的前向任务验收。

## 使用建议

- Codex 桌面应用和终端的 CLI 可能是不同版本，分别核对；本次未推断支持 `.agents/skills/` 的最低版本。
- 旧 CLI 看不到 Skill 时，应更新或更换为已支持目录的宿主，不在同一项目再安装 `.codex/skills/` 副本。
- Claude Code 的标准启动结果与 `--bare` 结果分开记录，不能将未测试模式一概标为支持。
- Trae 的安装和离线脚本测试仍有效，但不宣称其 GUI 自动发现已通过。
- 未因本次验收合并分支、创建 Tag/Release 或修改其他 edition。
