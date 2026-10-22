# 技能市场上架说明（Standard）

本文只讲**把 Standard 2.4 开发版上架到技能市场需要提交什么、填什么、怎么验**。技术细节见 [安装指南](agent-install-guide.md) 与 [通用包迁移验收](universal-package-validation.md)。

## 1. 上传物

| 项 | 文件 | 说明 |
|---|---|---|
| 技能 ZIP | [`dist/MathModel-Skill-Standard-store.zip`](../dist/MathModel-Skill-Standard-store.zip) | 根目录含 `SKILL.md`，市场从它的 YAML 前页自动填名称与摘要 |
| 技能标志 | [`assets/mathmodel-icon-512.png`](../assets/mathmodel-icon-512.png) | 512×512 正方形 PNG，约 41 KB，远低于 5 MB 上限 |
| 完整性 | [`dist/SHA256SUMS.txt`](../dist/SHA256SUMS.txt) | 同时覆盖通用包与商店包 |

商店包与 [`dist/MathModel-Skill-Standard.zip`](../dist/MathModel-Skill-Standard.zip) **内容一致**，只是多一份根目录 `SKILL.md`。多出来的这一份会被写进构建清单 `MATHMODEL_BUILD.json`，所以两个包都能用同一个 `install.py` 安装，`validate_source()` 的文件清单校验不会被这个额外文件打破。

## 2. 可直接粘贴的字段

**技能名称**（限 60 字符）：`MathModel Skill Standard`

**摘要**（一行）：`数学建模竞赛全流程技能包：输入预检、模型路线、真实运行、证据门禁、正式写作、Word/PDF 检查。`

**关于这项技能**：

> MathModel Skill 是一套供编程 Agent 使用的数学建模技能包，包含十个互相协作的技能和一个入口路由技能。把赛题与附件放进项目后，Agent 按 S0-S8 依次完成：输入预检与哈希登记、题意分析、模型路线与评分对齐、数据清洗与图表计划、编写建模代码、真实运行并保存结果证据、证据门禁、分章节正式写作、Word/PDF 渲染检查。
>
> 它和"让模型直接写一篇论文"的提示词不同：每个阶段用文件和 SHA-256 交接，图表必须可读取并绑定真实运行，数值结论要能追溯到本次计算的机器可读结果；手工修改指标或结论会让证据门禁失败。最终产物包括 `final_paper.docx`、Markdown 源稿、渲染 PDF、赛题代码、计算结果、图表和检查报告。
>
> 安装器只复制技能目录并记录哈希，不联网、不覆盖项目根配置、依赖文件或旧结果。支持 Codex、Claude Code、Trae 三种安装位置；其他能加载 Agent Skills 目录的宿主可以手动复制 `skills/` 下的十个目录。
>
> 需要 Python 3.11 或 3.12；最终 PDF 渲染检查需要 LibreOffice。检查通过代表证据、写作与格式门禁通过，不代表论文优秀或竞赛获奖。

## 3. 常见问题解答

**Q：需要什么运行环境？**
Python 3.11 或 3.12；`requirements.txt` 里的基础依赖；最终 PDF 渲染检查需要 LibreOffice。优化求解可选安装 `requirements-modeling.txt`。

**Q：支持哪些 Agent？**
安装器的 `--platform` 支持 `codex`（`.agents/skills/`）、`claude`（`.claude/skills/`）、`trae`（`.trae/skills/`）。三个宿主的技能内容完全相同，只是安装位置不同。

**Q：装完就能得到一篇优秀论文吗？**
不能。这套技能保证的是流程、证据链和格式检查，不保证数学正确性或获奖。它明确不允许编造数据、结果、引用和验证。

**Q：能不能只装其中一个技能？**
不建议。十个技能通过入口 `paper-workflow-orchestrator` 串联，缺一个会让对应阶段的检查失败。一个项目只安装一个版本、一个安装位置。

**Q：安装时目录已有旧内容怎么办？**
安装器不覆盖：会把冲突列出来，要求先自行备份整理，没有强制覆盖开关。中断的安装可以用 `--recover` 回滚。

**Q：做到一半中断了怎么继续？**
从赛题项目根目录运行 `workflow_guard.py --status`，读 `paper_output/qa/workflow_guard_report.json` 的 `recommended_skill` 与 `next_action` 从第一个失败阶段继续，不要重放已完成的工作。

**Q：会上传我的赛题数据吗？**
不会。安装器不联网；技能默认只读取 `problem_files/` 与 `paper_output/`，所有产物留在本地。只有需要公开外部数据时才会用到检索技能。

**Q：会覆盖我自己改过的代码吗？**
不会。安装器只写技能目录，赛题代码始终写在 `paper_output/code/`。升级时也只替换未被修改的受管文件。

**Q：能导出 LaTeX 吗？**
当前 Standard 只出可编辑的 Word OMML 公式与渲染 PDF。LaTeX 是独立的实验性分支，不是 Standard 的导出选项。

## 4. 上架前自检

在仓库根目录执行（本机与 CI 使用同一组命令）：

```bash
python scripts/check_skills.py
python scripts/check_skill_triggers.py --strict
python -S tests/test_installation.py
python scripts/build_release_packages.py --verify
```

最近一次本机结果（2.4.0-dev.4）：

| 检查 | 结果 |
|---|---|
| `check_skills.py` | PASS：十技能清单、版本、本地引用一致 |
| `check_skill_triggers.py --strict` | 20/20 触发用例命中，最高描述相似度 0.149（低于冲突阈值） |
| `tests/test_installation.py` | 24 项通过，2 项按平台跳过 |
| `build_release_packages.py --verify` | 两个归档与源码树、校验和一致 |
| 商店包端到端安装 | 解压后 `install.py --platform codex` 安装成功，十个技能落位，`preflight_check.py` 与 `workflow_guard.py` 可运行 |

## 5. 变更商店包时

只要 `skills/`、`store/SKILL.md` 或包内 `docs/` 改了，就必须重新生成归档再提交，否则 CI 的 `build_release_packages.py --verify` 会失败：

```bash
python scripts/build_release_packages.py --clean
python scripts/build_release_packages.py --verify
```

`VERSION` 与 `skills/paper-workflow-orchestrator/MATHMODEL_EDITION.json` 必须同步，否则安装器会拒绝这个包。
