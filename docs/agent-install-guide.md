# Lite 安装指南

本分支只分发 MathModel Lite。Standard 位于默认分支 `standard`。

| 平台 | 下载包 | 复制到项目 | Skill 入口 |
|---|---|---|---|
| Codex | `dist/MathModel-Skill-Lite-Codex.zip` | `.agents/skills/` | `.agents/skills/mathmodel-lite/SKILL.md` |
| Claude Code | `dist/MathModel-Skill-Lite-Claude-Code.zip` | `.claude/skills/` | `.claude/skills/mathmodel-lite/SKILL.md` |
| Trae | `dist/MathModel-Skill-Lite-Trae.zip` | `.trae/skills/` | `.trae/skills/mathmodel-lite/SKILL.md` |

不要在已安装 Standard 或 Pro 的项目上覆盖安装。切换版本时优先使用新项目；需要原地切换时，只清理旧 MathModel Skill 目录，保留其他 Skills 和用户根目录配置。历史 `AGENTS.md` / `CLAUDE.md` 中的 MathModel 专属指令须单独确认后调整，不要删除整个文件。

安装后运行：

```bash
pip install -r requirements.txt
```

然后使用 [Lite Starter Prompt](lite-starter-prompt.md)。
