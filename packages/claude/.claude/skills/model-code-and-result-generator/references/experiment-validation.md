# 实验验证工具

仅在预测验证或线性/整数优化时加载。其他题型继续使用现有工作流，不强制套用这些方法。
工具由生成器复制到赛题 `paper_output/code/modeling/`，编辑赛题脚本，不修改安装目录。

## 预测：先声明验证目标

`regression_baseline` 的显式行号接口继续保留，但不会检查时间/主体泄漏。
新增 `validation_tools.backtest_regression` 支持如下 `model_route.json` 每问配置：

```json
{
  "question_id": "Q1",
  "task_type": "forecasting",
  "data_source": "problem_files/data.csv",
  "regression": {
    "target": "demand",
    "features": ["scheduled_capacity"],
    "unit": "吨",
    "feature_availability": {"scheduled_capacity": "known_in_advance"},
    "validation": {
      "kind": "rolling_origin",
      "time_column": "date",
      "min_train_size": 12,
      "test_size": 3,
      "gap": 1,
      "step": 3
    }
  }
}
```

- `temporal_holdout`：只声明 `time_column/test_size/gap`，留出最后一段。
- `rolling_origin`：增加 `min_train_size`；可选 `step`、`window`。窗口尺寸均按不同时间点计数，非天数。`gap` 从训练尾部排除时间点；`step >= test_size`，测试窗口不重叠。
- `group_holdout`：改用 `group_column` 与显式 `test_groups` 列表，模拟新对象预测。组 ID 必须与读取后的类型一致，CSV 导入默认保留字符串。
- 时间列用明确的 ISO 日期/时间并预先升序排列；不自动排序，不猜数字时间戳单位。混合时区转换为 UTC。当前回测只支持单序列；面板数据需按主体分别建模与验证，不能把不同主体的末值混为一个基线。
- 每个特征明确声明 `known_in_advance` 或一个记录其可获得时间的列。后一种会检查训练/测试特征均不晚于预测起点。不要把未来实际天气、最终销量等标成预先已知。
- 标签默认在对应记录时间可用；有发布延迟时声明 `target_available_at` 时间列，检查训练标签在起点已可获取。
- 分组留出没有时间起点，要求显式声明特征可用性；需要同时隔离时间与主体时写专用划分，不假装工具已覆盖。

输出每折行号、系数、训练内预处理、逐样本预测、RMSE/MAE、训练均值基线，以及时间序列末值基线。
汇总 RMSE 按全部不重叠测试样本重算，不直接平均各折 RMSE。额外尾部不足一个窗口的数据不计入该回测；以输出行号为准。
指标自动带 `metric_id/unit/split/sample_scope/source_table` 并写入 CSV；报告和预测表一并登记为运行产物。
来源定位同时绑定指标名、单位、数据划分和样本范围列；S7 检查这些列与指标元数据一致。

这些 `test` 标签仅表示每折未用于拟合，**不是保证从未参与调参的最终测试集**。
若据此选择模型，另外保留未用于选择的最终测试集，或采用合适的嵌套验证。
不能根据表现反复选择划分，不能把不同划分上的指标直接用于模型胜负比较。

## 优化：可选求解器及证据

只有使用线性/整数规划适配器时安装：

```bash
python -m pip install -r requirements-modeling.txt
```

采用 SciPy `optimize.milp` / HiGHS；预测工具仍只依赖已有 NumPy/Pandas。
接口 `solver_evidence.solve_linear_problem(problem, metric_id=..., unit=...)`，支持显式最小化/最大化、线性等式/不等式、边界和整数索引。
非线性、二次、逻辑或机理约束不能静默丢弃；其他求解器需要另做适配和独立测试。

在模型路线中用 `optimization` 代替 `regression`：

```json
{
  "unit": "万元",
  "sample_scope": "本期资源分配方案",
  "time_limit": 60,
  "mip_rel_gap": 0,
  "problem": {
    "sense": "max",
    "c": [3, 1],
    "bounds": [[0, 2], [0, 2]],
    "A_ub": [[1, 1]],
    "b_ub": [3],
    "integer_indices": [0, 1]
  }
}
```

该小例子只说明格式。真实赛题必须从获准输入构造模型，说明系数来源；不能照搬矩阵。
`A_ub x <= b_ub`、`A_eq x = b_eq`；每个变量显式声明边界，`null` 为该端无界。
默认单次求解限时 60 秒，可按任务明确调整，不对 Standard 引入无上限流程。

报告 `solver-evidence/1` 保存原问题及哈希、UTC 时间、SciPy 版本、求解参数、原始状态/消息、解向量、界与差距，独立重算目标、约束、边界与整数性。

- `OPTIMAL`：原始状态成功且复核通过；整数模型还需有效界与足够小的差距。
- `FEASIBLE`：有经过复核的可行解，但最优性未确认，包括限时退出或带非零明显差距的成功退出。
- `INFEASIBLE/UNBOUNDED/UNKNOWN/ERROR`：保留失败记录，不输出伪造的目标值，不通过正式门禁。
- 数值最优性仅针对提交的模型及容差，不是形式化证明，也不证明约束忠实于题意。

S7 对 `optimal` 重新解析该报告、核对问题哈希、重新算约束与目标并推导允许的声明强度。
旧版只有 `optimality_verified: true` 的报告不能再通过；必须重新运行产生支持的报告。
此版本未适配任意数学证书/其他求解器，遇到该需求需扩展适配器，不能伪装成 HiGHS 输出。
有写权限的程序仍可能伪造整个报告；运行哈希用于复现与误改检测，不是防恶意程序的安全证明。

## 交接与验收

脚手架会真实计算，但仍保持 `scaffold_result_needs_review`；工具不能自动放行 S6。
Agent 完成题意、特征、约束和验证设计审查后，由赛题代码输出正式结论，再运行 runner、S6 和 S7。
S7 策略版本更新为 2；旧写作计划需重新运行 `prepare_authoring.py`。
保留旧数据源与手改脚本；生成器不会覆盖已去除 managed marker 的用户文件。

接口参考：[SciPy milp](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html)、
[时间序列划分原则](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html)。
