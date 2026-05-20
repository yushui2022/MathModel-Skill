from __future__ import annotations

from typing import Any


def normalize_task_type(task_type: str) -> str:
    text = str(task_type or "").lower()
    if any(key in text for key in ("预测", "回归", "forecast", "regression")):
        return "forecasting"
    if any(key in text for key in ("优化", "规划", "调度", "选址", "路径")):
        return "optimization"
    if any(key in text for key in ("评价", "排序", "权重", "综合", "topsis", "ahp")):
        return "evaluation"
    if any(key in text for key in ("分类", "识别", "判别")):
        return "classification"
    if any(key in text for key in ("聚类", "分群")):
        return "clustering"
    if any(key in text for key in ("仿真", "机理", "动力学", "微分")):
        return "simulation"
    return "general"


def metric_templates(task_type: str) -> list[dict[str, Any]]:
    kind = normalize_task_type(task_type)
    templates = {
        "forecasting": [
            {"metric_name": "RMSE", "metric_role": "预测误差", "value": None, "unit": ""},
            {"metric_name": "MAE", "metric_role": "平均绝对误差", "value": None, "unit": ""},
            {"metric_name": "MAPE", "metric_role": "相对误差", "value": None, "unit": "%"},
        ],
        "optimization": [
            {"metric_name": "objective_value", "metric_role": "目标函数值", "value": None, "unit": ""},
            {"metric_name": "constraint_satisfaction_rate", "metric_role": "约束满足率", "value": None, "unit": "%"},
            {"metric_name": "baseline_improvement", "metric_role": "相对基线改进幅度", "value": None, "unit": "%"},
        ],
        "evaluation": [
            {"metric_name": "top_score", "metric_role": "最高综合得分", "value": None, "unit": ""},
            {"metric_name": "rank_stability", "metric_role": "排序稳定性", "value": None, "unit": ""},
            {"metric_name": "weight_sensitivity", "metric_role": "权重敏感性", "value": None, "unit": ""},
        ],
        "classification": [
            {"metric_name": "accuracy", "metric_role": "分类准确率", "value": None, "unit": "%"},
            {"metric_name": "f1_score", "metric_role": "F1 值", "value": None, "unit": ""},
            {"metric_name": "auc", "metric_role": "AUC", "value": None, "unit": ""},
        ],
        "clustering": [
            {"metric_name": "silhouette_score", "metric_role": "轮廓系数", "value": None, "unit": ""},
            {"metric_name": "cluster_count", "metric_role": "聚类数量", "value": None, "unit": ""},
            {"metric_name": "cluster_stability", "metric_role": "聚类稳定性", "value": None, "unit": ""},
        ],
        "simulation": [
            {"metric_name": "fit_error", "metric_role": "历史拟合误差", "value": None, "unit": ""},
            {"metric_name": "parameter_sensitivity", "metric_role": "参数敏感性", "value": None, "unit": ""},
            {"metric_name": "scenario_change", "metric_role": "情景变化幅度", "value": None, "unit": ""},
        ],
        "general": [
            {"metric_name": "core_score", "metric_role": "核心评价指标", "value": None, "unit": ""},
            {"metric_name": "baseline_comparison", "metric_role": "基线对比结果", "value": None, "unit": ""},
            {"metric_name": "robustness_check", "metric_role": "稳健性检查", "value": None, "unit": ""},
        ],
    }
    return [dict(item) for item in templates[kind]]


def result_type(task_type: str) -> str:
    kind = normalize_task_type(task_type)
    return {
        "forecasting": "prediction_result",
        "optimization": "optimization_solution",
        "evaluation": "ranking_or_score",
        "classification": "classification_result",
        "clustering": "cluster_result",
        "simulation": "simulation_result",
        "general": "model_result",
    }[kind]


def suggested_table_titles(task_type: str) -> list[str]:
    kind = normalize_task_type(task_type)
    return {
        "forecasting": ["预测结果表", "误差指标表", "残差摘要表"],
        "optimization": ["最优方案表", "约束满足情况表", "方案对比表"],
        "evaluation": ["指标权重表", "综合得分排序表", "敏感性分析表"],
        "classification": ["分类结果表", "混淆矩阵表", "特征重要性表"],
        "clustering": ["聚类标签表", "群体特征表", "聚类稳定性表"],
        "simulation": ["参数估计表", "情景仿真结果表", "敏感性分析表"],
        "general": ["核心结果表", "模型对比表", "稳健性检查表"],
    }[kind]

