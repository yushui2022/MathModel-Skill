# 可复用建模工具

只在需要数据选择、数值回归基线或线性解复核时读取本文件。
`build_result_contracts.py` 会把 `modeling_tools.py` 与共享的 `data_inputs.py`
复制到 `paper_output/code/modeling/`，不增加依赖；工具使用现有 NumPy/Pandas。
时间/分组验证和主动求解见 [实验验证工具](experiment-validation.md)；其中优化后端按需安装 SciPy。

## 1. 当前数据与显式绑定

数据必须来自本轮有效 `paper_output/data_cleaned/cleaning_report.json`。
缺报告、来源不再获准、来源或清洗文件被修改时停止，不回退扫描历史文件。
自定义预处理也应由真实代码产生兼容的清洗记录，不能手写 PASS 绕过验证。

`model_route.json` 每问可使用下面的配置。行号是 CSV 数据行的零基位置，不是索引标签；
这里只展示接口，不代表任意赛题都应使用这组字段或切分。

```json
{
  "question_id": "Q1",
  "task_type": "forecasting",
  "data_source": "problem_files/observations.xlsx",
  "sheet": "observations",
  "regression": {
    "target": "demand",
    "features": ["temperature"],
    "train_rows": [0, 1, 2, 3],
    "test_rows": [4, 5]
  }
}
```

多个文件/工作表须明确选择；仅有一个数据集时可省略 `data_source`/`sheet`。
加载时保留字符串编号、空单元格和字面量 `NA`，只对绑定的预测字段进行数值解析。
列名、单位、关联键和缺失标记的含义由赛题决定，工具不自动推断。

## 2. 留出集回归基线

在赛题 `q*_model.py` 中调用：

```python
from modeling_tools import load_current_dataset, regression_baseline
from result_contract_io import PROJECT_ROOT, RESULTS_DIR, write_json

frame, source = load_current_dataset(
    PROJECT_ROOT, source="problem_files/observations.xlsx", sheet="observations"
)
report = regression_baseline(
    frame, target="demand", features=["temperature"],
    train_rows=[0, 1, 2, 3], test_rows=[4, 5]
)
write_json(RESULTS_DIR / "q1_baseline.json", report)
```

- OLS 使用 `numpy.linalg.lstsq`；中位数填补、中心与尺度只在训练行拟合。
- 缺失目标不填补，训练集全空特征不借用测试集信息；无穷值、非数值字段、重复/重叠行号拒绝。
- 返回测试集 RMSE/MAE、训练均值基线 RMSE、系数、预处理参数、样本行号和逐行残差。
- 不自动挑目标、特征或最佳划分，不自动调参，也不把训练误差当测试误差。
- 时间序列应按时间先后划分并考虑预测窗口；重复主体应按组划分。不同数据行也可能泄漏。
- 不能用测试集选择模型再报告同一测试集表现。数据很少或秩不足时，基线不支持强泛化结论。

默认生成的预测脚手架会同时保存 `results/q1_baseline.json` 和留出集 CSV。
结果仍是 `scaffold_result_needs_review`，须完成题意复核和适当验证，再由实际运行代码产出正式契约。

## 3. 线性优化结果复核

把求解器返回的解与原始问题系数交给独立的数值检查函数。
约定 `A_ub @ x <= b_ub`、`A_eq @ x == b_eq`、目标值 `c @ x`；
变量边界必须逐一声明，`None` 表示该端无界，不隐含非负约束。

```python
from modeling_tools import verify_linear_solution

check = verify_linear_solution(
    c=[-3, -1], x=[2, 1],
    A_ub=[[1, 1]], b_ub=[3],
    bounds=[(0, 2), (0, 2)], integer_indices=[0, 1],
    reported_objective=-7
)
assert check["status"] == "PASS", check["checks"]
```

这是一个已知解的小例子，不是通用优化算法。真实任务须替换全部系数与解。
检查返回每项左/右值、违例量、容差、可行性和重算目标值。
整数性仅用绝对容差，避免巨大变量值被相对容差误放行。

**PASS 不证明最优性**：最优性仍需界、对偶证书、小规模穷举或适用求解器证据。
非线性、逻辑、业务约束必须另写验证；不能只检查线性子集就宣称方案整体可行。

## 4. 运行与证据

自定义报告须加入 `execution_provenance.output_artifacts`，通过 `run_modeling.py`
执行后才能进入证据链。工具不会自动盖章通过 S6。
新 runner 在执行前后比较来源、当前数据、清洗报告、模型路线和本目录 Python 文件；
它是可复现性检查，不是文件系统沙箱，也不能防范故意伪造的建模程序。

已有用户修改的代码不会被生成器覆盖。升级旧赛题时先保留代码，再迁移输入绑定和运行记录；
不能继续依赖旧 runner 对历史目录的递归扫描。
