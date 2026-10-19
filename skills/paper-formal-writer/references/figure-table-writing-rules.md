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

正式正文必须优先使用：

- `paper_output/results/model_results.json`
- `paper_output/results/metrics.json`
- `paper_output/results/conclusions.json`
- `paper_output/tables/table_index.json`
- `paper_output/figure_index.json`

若证据状态不是 `ready` 或 `generated`，不得写成最终结论。
