<div align="center">
  <img src="./assets/mathe-skill-logo.svg" alt="MathModel Lite logo" width="132" height="132" />

# MathModel Skill Lite

### 面向普通模型、较旧模型和短上下文的单入口数学建模 Skill

#### 支持 Codex、Claude Code 和 Trae

[![Version](https://img.shields.io/badge/version-2.2.1--lite.2-111827)](#下载)

</div>

<p align="center">
  <a href="./assets/orlando-liu-social.jpg">
    <img src="./assets/orlando-liu-social.jpg" alt="Orlando Liu social media profile" width="480" />
  </a>
</p>

这是 MathModel Skill 的 **Lite 分支**，推荐普通模型、较旧模型、上下文较短或工具调用稳定性一般的模型使用。本分支只包含 Lite，不包含 Standard 的总控、正式论文、证据门禁或其他协作 Skills。用户下载本分支或 Lite 发布包后，只会发现一个入口：`mathmodel-lite`。

## 版本选择

| 模型与目标 | 建议版本 | 分支 |
|---|---|---|
| Claude Fable 5 / GPT-5.6 Sol Ultra，允许高计算成本，追求最高可验证质量 | Pro | [`pro`](https://github.com/yushui2022/MathModel-Skill/tree/pro) |
| 强模型、长上下文、复杂工具调用稳定，需要正式竞赛论文 | Standard | [`master`](https://github.com/yushui2022/MathModel-Skill/tree/master) |
| 普通模型、较旧模型、上下文较短，希望流程简单稳定 | **Lite（当前分支）** | [`lite`](https://github.com/yushui2022/MathModel-Skill/tree/lite) |

Pro 位于 `pro` 分支，面向 Claude Fable 5、GPT-5.6 Sol Ultra 和不计成本的高验证流程；Standard 位于默认分支 `master`，面向强模型和正式竞赛；Lite 用固定六步降低普通模型的上下文与决策负担。

**一个比赛项目只安装一个版本。** 不要把 Pro、Standard 和 Lite 的 ZIP 解压到同一目录。

## 为什么有 Lite

Standard 推荐强模型和正式比赛交付使用，但多 Skill 路由、长上下文和复杂契约可能让普通模型或较旧模型承担过高负担。Lite 将流程压缩为一个 Skill、三个确定性脚本和固定六步，同时保留最重要的真实性底线：

- 记录输入文件大小和 SHA-256。
- 必须真实运行一个 `model.py`。
- 记录代码、输入、结果和证据文件哈希。
- 拒绝输入或代码在运行后被修改。
- 拒绝空答案、非有限指标、缺失证据和占位正文。
- 只有 `lite_report.json.status=PASS` 才生成并交付 Word。

Lite 不提供原生 Word OMML 公式、严格正文引文审计、LibreOffice 渲染或 Standard 的完整 S0-S8 证据链。

## 固定流程

```text
problem_files/
-> lite_preflight.py
-> plan.json
-> 单个 code/model.py
-> lite_run.py
-> results.json
-> paper.md
-> lite_finalize.py
-> paper.docx + lite_report.json
```

全部运行产物写入 `paper_output_lite/`。

## 下载

只下载与你的平台对应的一个 ZIP：

| 平台 | 发布包 | 安装入口 |
|---|---|---|
| Codex | `dist/MathModel-Skill-Lite-Codex.zip` | `skills/mathmodel-lite/SKILL.md` |
| Claude Code | `dist/MathModel-Skill-Lite-Claude-Code.zip` | `.claude/skills/mathmodel-lite/SKILL.md` |
| Trae | `dist/MathModel-Skill-Lite-Trae.zip` | `.trae/skills/mathmodel-lite/SKILL.md` |

解压到一个未安装 Standard 的比赛项目根目录，然后安装依赖：

```bash
pip install -r requirements.txt
```

## 使用

在项目根目录创建：

```text
problem_files/
```

放入赛题和附件后，对 Agent 说：

```text
请使用 MathModel Lite，只读取 mathmodel-lite。
严格按固定六步执行，所有产物写入 paper_output_lite/。
必须真实运行 model.py，只有 lite_report.json 为 PASS 时才能交付 paper.docx。
```

完整提示词见 [Lite Starter Prompt](docs/lite-starter-prompt.md)，详细流程见 [Lite Workflow](docs/lite-workflow.md)。

## 三个脚本

以 Codex 为例：

```bash
python skills/mathmodel-lite/scripts/lite_preflight.py
python skills/mathmodel-lite/scripts/lite_run.py
python skills/mathmodel-lite/scripts/lite_finalize.py
```

Claude Code 将 `skills/` 替换为 `.claude/skills/`，Trae 替换为 `.trae/skills/`。

## 开发与发布

Claude Code 目录是 canonical payload，Codex 和 Trae 由同步脚本生成：

```bash
python scripts/sync_platform_packages.py
python scripts/sync_platform_packages.py --check
```

运行测试并生成三个确定性发布包：

```bash
python tests/run_lite_tests.py
python scripts/build_release_packages.py --clean
python scripts/build_release_packages.py --verify
```

每个 ZIP 都包含 `VERSION`、`LICENSE`、`MATHMODEL_EDITION.json` 和
`MATHMODEL_BUILD.json`，可校验逐文件 SHA-256 与聚合 payload SHA-256；
`dist/SHA256SUMS.txt` 记录三个安装包的发布哈希。

## 许可证

MIT License，Copyright (c) 2026 yushui2022。
