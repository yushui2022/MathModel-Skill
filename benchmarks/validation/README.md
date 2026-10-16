# 离线实验验证案例

这两个原创合成案例用于程序验收，不是历史赛题，也不代表论文获奖或 20 页成文能力。

- 预测：`y = 2x + 3`，按时间滚动训练与测试。核对斜率、截距、逐样本预测、训练均值和末值基线。
- 优化：最大化 `3x + y`，`0 <= x,y <= 2`、`x+y <= 3` 且变量为整数。测试独立穷举全部候选核对最优值 7。

运行：

```bash
python -m pip install -r requirements.txt -r requirements-modeling.txt
python tests/test_validation_tools.py
python tests/test_validation_integration.py
```

集成测试在临时项目中执行数据导入、脚手架生成、真实 runner、S6 门禁和 S7 数值声明审计，
并验证错误样本口径、报告篡改、假最优性和求解失败会被拒绝。不是 DOCX/PDF 全流程验收。
`benchmark_question.py` 仅用于已经定义好的合成题，不能用作真实赛题的自动审核或放行脚本。

Windows 本地维护时把 `TEMP`/`TMP` 指向 G 盘已有临时目录。测试结束后自动清理临时项目。
