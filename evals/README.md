# Skill 评估集

本目录存放两个层面的检查资产，两者目的不同，不能互相替代。

## 1. `trigger-cases.json` —— 发现层（选不选得对）

20 条真实口吻的用户提示词，每条标注应当被选中的 Skill（`null` 表示不该触发任何 MathModel Skill）。
由 `scripts/check_skill_triggers.py` 消费：

```bash
python scripts/check_skill_triggers.py            # 只打印结果
python scripts/check_skill_triggers.py --strict   # 任一未命中即退出码 1
```

**边界说明：** 该脚本用字符二元组 + ASCII 词的 TF-IDF 余弦相似度做**词面代理**，不是模型路由实测。
它擅长发现"两个 Skill 用同一套词描述自己"这类冲突，不能证明真实宿主下的发现准确率。
修改 `description` 后应先跑它，再用真实宿主验证。

## 2. `<skill-name>/evals.json` —— 产出层（做得对不对）

按 [agentskills.io 评估规范](https://agentskills.io/skill-creation/evaluating-skills) 的格式记录每条用例：

- `prompt`：用户会真的这么说的请求
- `expected_output`：人能读懂的合格标准
- `files`：可选，用例需要的输入文件

标准跑法是**同一条用例跑两遍**：带 Skill 与不带 Skill（或对上一版），比较差异；先看结果再补断言。

当前覆盖三个关键 Skill：`paper-workflow-orchestrator`（入口）、`quality-assurance-auditor`（放行判定）、
`problem-doc-model-selector`（题面解析）。

## 为什么评估集不在 `skills/` 里

官方惯例是把 `evals/evals.json` 放在 Skill 目录内。本项目把它放在仓库根，原因是
`skills/` 下的每个文件都会进入发布包（`dist/MathModel-Skill-Standard.zip`）并计入
`MATHMODEL_EDITION.json` 的 `required_files`；把测试语料打包给最终用户既增加体积，也让
"安装载荷"变成"仓库资产清单"。放在根目录既能纳入版本控制，也不污染安装包。

需要与 Skill 一起分发时，再单独评估是否迁入。
