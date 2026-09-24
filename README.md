<div align="center">
  <img src="./assets/mathmodel-banner.png" alt="MathModel Skill：豆包坐镇指挥，Fable 推导模型，Astra 编写代码" width="100%" />

# MathModel Skill Flash

### 用高吞吐模型快速生成带真实实验的基础长篇数学建模论文

[![Version](https://img.shields.io/badge/version-2.0.0--flash.1-D97706)](https://github.com/yushui2022/MathModel-Skill/tree/flash)
[![Platforms](https://img.shields.io/badge/platforms-Codex%20%7C%20Claude%20Code%20%7C%20Trae-111827)](#快速导入使用)
[![License](https://img.shields.io/badge/license-MIT-16a34a)](./LICENSE)

</div>

MathModel Skill 是面向数学建模竞赛的 Agent 工作流。它从赛题和附件出发，读取数据、运行建模代码、保存真实结果和图表，再生成可编辑的论文文档。**Flash 是独立的速度优先版本**：适合 DeepSeek、Gemini、GLM 等 Flash 类高吞吐模型，目标是在较短时间内完成一份有实验内容、结果数值和 Word 导出的基础长文草稿。

Flash 不承诺 Standard 的完整证据链、原生 Word 公式和 PDF 排版验收，也不承诺 Pro 的多路线竞赛、独立复算和五角色审稿。它适合作为快速起稿和方案探索版本；正式提交前应使用 Standard 或 Pro 复核。

## 版本选择

本项目每个版本在独立 Git 分支维护，**不是安装后的切换模式**。质量和速度不是单一的高低排序：Lite 优先降低模型负担，Flash 优先降低等待时间，Standard 优先正式交付，Pro 优先验证深度。

| 定位 | 版本与分支 | 适合谁 | 主要交付 |
|---|---|---|---|
| 速度优先 | [**Flash**](https://github.com/yushui2022/MathModel-Skill/tree/flash) | DeepSeek/Gemini/GLM 等 Flash 类高吞吐模型 | 真实实验、图表、结果和约 18–22 页目标的基础 Word 长文；不做严格终稿门禁 |
| 低负担 | [**Lite**](https://github.com/yushui2022/MathModel-Skill/tree/lite) | DeepSeek 等普通、较旧或短上下文模型 | 固定六步基础报告；篇幅和验证较轻 |
| 正式标准 | [**Standard**](https://github.com/yushui2022/MathModel-Skill/tree/standard) | GPT-5.5、GPT-5.6 Sol 等中高能力模型 | 完整章节写作、证据检查、原生 Word 公式和 PDF 渲染检查 |
| 高强度旗舰 | [**Pro**](https://github.com/yushui2022/MathModel-Skill/tree/pro) | GPT-6 Astra、Claude Fable 5.1 等前沿模型 | 多路线比较、独立复算、稳健性实验、五角色审稿和 Word/PDF 检查；预发布 |
| TeX 实验 | [**LaTeX**](https://github.com/yushui2022/MathModel-Skill/tree/Latex) | 需要旧版 TeX/PDF 流程的用户 | 独立实验性分支，不等同于 Standard 或 Pro 的当前能力 |

各版本 README 都保留这张版本表，便于从任意分支回到其他版本。**一个项目只安装一个版本、一个平台包，不要混装。**

## 小红书

作者：**Orlando Liu（奥兰多）**，小红书号：[`xiaoyushui2022`](https://www.xiaohongshu.com/user/profile/610d282b0000000001004ffb)。点击图片进入主页，也可以扫码找到我。

<p align="center">
  <a href="https://www.xiaohongshu.com/user/profile/610d282b0000000001004ffb">
    <img src="./assets/orlando-liu-social.jpg" alt="Orlando Liu 小红书主页与二维码" width="480" />
  </a>
</p>

## 快速导入使用

### 1. 下载 Flash 包

进入 [Flash 分支](https://github.com/yushui2022/MathModel-Skill/tree/flash) 的 `dist/` 下载对应平台包，或等待本版本 Release 发布。不要把仓库源码 ZIP 当作平台安装包。

| 平台 | 解压后的目录 |
|---|---|
| Codex | `.agents/skills/` |
| Claude Code | `.claude/skills/` |
| Trae | `.trae/skills/` |

保留用户已有的 `AGENTS.md` / `CLAUDE.md`，不要把不同版本的入口复制到同一项目。Python 建议使用 3.11 或 3.12，安装本包内 `requirements.txt` 后执行 `python -m pip check`。

### 2. 放入题目并启动

在项目根目录创建 `problem_files/`，放入赛题和附件，然后对 Agent 说：

```text
请使用 $mathmodel-flash 完成这道数学建模题，赛题和附件在 problem_files/。
按 Flash 六步流程完成：预检、计划、真实实验、运行记录、约 20 页目标的完整基础论文、Word 检查。
所有产物只写入 paper_output_flash/，不要读取其他版本的旧结果，不要用重复段落凑页数。
只有 flash_report.json 为 PASS 后，才交付 paper.docx，并明确说明这是一份需要进一步复核的快速基础稿。
```

也可以直接读取 [Flash 启动提示词](docs/flash-starter-prompt.md)。

## 原理介绍

```text
赛题与附件
→ 输入哈希预检
→ 单路线快速计划
→ 一个 model.py 真实运行
→ 保存 results / CSV / PNG
→ 生成有实验内容的长文
→ 基础一致性检查与 Word 导出
```

Flash 用少量固定脚本守住最低真实性底线：预检记录输入，运行器绑定计划、脚本和结果，终检检查每个问题、关键数值、图表和 DOCX 重开内容。它刻意不加入 Pro 的高成本研究闭环，以保持 Flash 模型的速度优势。

### 论文长度说明

默认目标是约 18–22 页，至少 9000 个有效字符，并按问题展开方法、算法、实验、结果、检验、敏感性和局限。脚本会给出粗略页数估计；不足目标只告警，不能靠复制正文通过。Word 页数会受到字体、页边距、表格和图片影响，因此 Flash 不把估算页数描述成排版保证。

### 明确限制

Flash PASS 不是数学正确性证明，也不是正式竞赛验收。没有严格引用审计、原生 OMML 公式、PDF 渲染门禁、独立双路径复算和多角色审稿时，应在提交前转入 [Standard](https://github.com/yushui2022/MathModel-Skill/tree/standard) 或 [Pro](https://github.com/yushui2022/MathModel-Skill/tree/pro)。

## 开发验证

```bash
python scripts/sync_platform_packages.py --check
python scripts/build_release_packages.py --verify
```

Flash 当前只维护 `mathmodel-flash` 一个入口，三端包都由 Claude canonical payload 同步生成；分支内不包含 Standard、Lite 或 Pro 的工作流。
