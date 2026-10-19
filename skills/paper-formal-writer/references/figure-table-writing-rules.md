# 图表、公式和结果证据写作规则

## 图表引用

每张图表遵守：

```text
正文引导句
图/表
图表解释段
结论回扣句
```

示例：

```text
为比较不同策略的收益差异，图5.2.1给出了基准策略与最优策略的单位期望利润。

![图5.2.1 问题二最优策略收益对比](figures/fig_q2_profit_comparison.png)

由图5.2.1可以看出，情况4的收益提升最明显。这说明当调换损失较高且检测成本下降时，对关键零配件进行检测能够显著降低后续缺陷风险。
```

## 表格写法

表格前说明表格用途，表格后解释规律。不要只贴 CSV。

```text
表5.2.1列出了六种情形下的最优检测与拆解决策。
```

表格列名应短而明确，数值保留合理位数。

## 公式写法

公式三段式：

```text
设变量 ...

公式

其中 ...。该式用于 ...
```

## 结果证据

正式正文只能使用当前冻结清单内的证据，通过 claim ID 追踪到：

- `paper_output_pro/experiments/<run-id>/metrics.json` 及真实运行回执
- `paper_output_pro/replication_report.json` 的独立复算
- `paper_output_pro/claim_evidence_map.json` 的声明与数值映射
- `paper_output_pro/source_ledger.json` 的外部来源快照
- `paper_output_pro/evidence_freeze.json` 中记录的图表文件

`ready`、`generated` 或手填 `PASS` 都不能代替新鲜检查点3和实际复算。
正式图表使用明确的 Markdown 图像路径和表格，不使用旧版索引占位标记。
每张图需列入写作计划并绑定冻结哈希；按实际论文语言设置标题、单位与图例。
