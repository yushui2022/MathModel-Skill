# Flash 安装指南

本分支只分发 MathModel Flash 2.0.0-flash.1。Standard、Lite、Pro 和 LaTeX 位于独立分支，不能与 Flash 混装。

| 平台 | 安装包 | 解压到项目 | Skill 入口 |
|---|---|---|---|
| Codex | `MathModel-Skill-Flash-Codex.zip` | `.agents/skills/` | `.agents/skills/mathmodel-flash/SKILL.md` |
| Claude Code | `MathModel-Skill-Flash-Claude-Code.zip` | `.claude/skills/` | `.claude/skills/mathmodel-flash/SKILL.md` |
| Trae | `MathModel-Skill-Flash-Trae.zip` | `.trae/skills/` | `.trae/skills/mathmodel-flash/SKILL.md` |

不要在已安装其他 MathModel 版本的项目上覆盖安装。切换版本时优先使用新项目；需要原地切换时，只清理确认的旧 MathModel Skill 目录，保留其他 Skills 和用户根目录配置。

安装后运行：

```bash
python -m pip install -r requirements.txt
python -m pip check
```

然后使用 [Flash Starter Prompt](flash-starter-prompt.md)。
