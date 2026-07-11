# Lite 安装指南

本分支只分发 MathModel Lite。Standard 位于默认分支 `master`。

| 平台 | 下载包 | 复制到项目 | Skill 入口 |
|---|---|---|---|
| Codex | `dist/MathModel-Skill-Lite-Codex.zip` | `skills/` + `AGENTS.md` | `skills/mathmodel-lite/SKILL.md` |
| Claude Code | `dist/MathModel-Skill-Lite-Claude-Code.zip` | `.claude/skills/` + `CLAUDE.md` | `.claude/skills/mathmodel-lite/SKILL.md` |
| Trae | `dist/MathModel-Skill-Lite-Trae.zip` | `.trae/skills/` | `.trae/skills/mathmodel-lite/SKILL.md` |

不要在已安装 Standard 的项目上覆盖安装。切换版本时，创建新项目最稳妥；否则先彻底删除旧版本的 skill 目录和入口文件。

安装后运行：

```bash
pip install -r requirements.txt
```

然后使用 [Lite Starter Prompt](lite-starter-prompt.md)。
