from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


PALETTE = {
    "blue": "#2563eb",
    "green": "#16a34a",
    "orange": "#f59e0b",
    "red": "#dc2626",
    "slate": "#334155",
    "gray": "#64748b",
    "cyan": "#0891b2",
    "purple": "#7c3aed",
}


def set_paper_style() -> None:
    """Use a restrained, publication-friendly Matplotlib style."""
    sns.set_theme(style="whitegrid", font_scale=1.0)
    plt.rcParams.update(
        {
            "figure.dpi": 120,
            "savefig.dpi": 300,
            "axes.edgecolor": "#cbd5e1",
            "axes.labelcolor": "#334155",
            "axes.titlecolor": "#111827",
            "xtick.color": "#475569",
            "ytick.color": "#475569",
            "grid.color": "#e5e7eb",
            "grid.linewidth": 0.8,
            "legend.frameon": False,
            "axes.unicode_minus": False,
        }
    )
    for font in [
        "SimHei",
        "Microsoft YaHei",
        "PingFang SC",
        "Arial Unicode MS",
        "WenQuanYi Micro Hei",
        "Noto Sans CJK SC",
    ]:
        try:
            plt.rcParams["font.sans-serif"] = [font]
            fig = plt.figure(figsize=(1, 1))
            plt.text(0.5, 0.5, "测试")
            plt.close(fig)
            return
        except Exception:
            continue


def sanitize_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def numeric_columns(df: pd.DataFrame, exclude: set[str] | None = None) -> list[str]:
    exclude = exclude or set()
    result = []
    for column in df.columns:
        name = str(column)
        if name in exclude:
            continue
        converted = safe_numeric(df[column])
        if converted.notna().sum() >= max(2, int(len(df) * 0.5)):
            result.append(name)
    return result


def categorical_columns(df: pd.DataFrame, exclude: set[str] | None = None) -> list[str]:
    exclude = exclude or set()
    result = []
    for column in df.columns:
        name = str(column)
        if name in exclude:
            continue
        if name not in numeric_columns(df, exclude):
            result.append(name)
    return result


def pick_x(df: pd.DataFrame, spec: dict[str, Any]) -> str:
    candidate = sanitize_text(spec.get("candidate_x"))
    if candidate in df.columns:
        return candidate
    patterns = ("year", "date", "time", "month", "day", "年份", "年度", "日期", "时间", "月份")
    for column in df.columns:
        name = str(column)
        lower = name.lower()
        if any(pattern in lower or pattern in name for pattern in patterns):
            return name
    cats = categorical_columns(df)
    if cats:
        return cats[0]
    return str(df.columns[0]) if len(df.columns) else ""


def pick_y(df: pd.DataFrame, spec: dict[str, Any], x_col: str, limit: int = 3) -> list[str]:
    raw = spec.get("candidate_y")
    result = []
    if isinstance(raw, list):
        for item in raw:
            name = sanitize_text(item)
            if name in df.columns and name != x_col:
                result.append(name)
    if result:
        return result[:limit]
    return numeric_columns(df, exclude={x_col})[:limit]


def sorted_for_x(df: pd.DataFrame, x_col: str) -> pd.DataFrame:
    if not x_col or x_col not in df.columns:
        return df.reset_index(drop=True)
    work = df.copy()
    numeric_x = safe_numeric(work[x_col])
    if numeric_x.notna().sum() >= max(2, int(len(work) * 0.5)):
        work["_sort_x"] = numeric_x
        return work.sort_values("_sort_x").drop(columns=["_sort_x"]).reset_index(drop=True)
    parsed = pd.to_datetime(work[x_col], errors="coerce")
    if parsed.notna().sum() >= max(2, int(len(work) * 0.5)):
        work["_sort_x"] = parsed
        return work.sort_values("_sort_x").drop(columns=["_sort_x"]).reset_index(drop=True)
    return work.reset_index(drop=True)


def apply_title(ax: plt.Axes, title: str, subtitle: str = "") -> None:
    ax.set_title(title, loc="left", fontsize=14, fontweight="bold", pad=12)
    if subtitle:
        ax.text(
            0,
            1.02,
            subtitle,
            transform=ax.transAxes,
            fontsize=9,
            color=PALETTE["gray"],
            va="bottom",
        )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def save_figure(fig: plt.Figure, output_path: Path) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return output_path.as_posix()


def label_endpoints(ax: plt.Axes, x_values: pd.Series, y_values: pd.Series, label: str, color: str) -> None:
    clean = pd.DataFrame({"x": x_values, "y": y_values}).dropna()
    if clean.empty:
        return
    row = clean.iloc[-1]
    ax.scatter([row["x"]], [row["y"]], s=34, color=color, zorder=5)
    ax.annotate(
        f"{label}: {row['y']:.3g}",
        xy=(row["x"], row["y"]),
        xytext=(8, 4),
        textcoords="offset points",
        fontsize=8,
        color=color,
    )


def plot_prediction_comparison(df: pd.DataFrame, spec: dict[str, Any], output_path: Path) -> str:
    title = sanitize_text(spec.get("title"), "真实值-预测值对比图")
    x_col = pick_x(df, spec)
    y_cols = pick_y(df, spec, x_col, limit=2)
    if not x_col or not y_cols:
        return plot_empty(title, "缺少可绘制的横轴或数值列", output_path)

    work = sorted_for_x(df[[x_col, *y_cols]].dropna(how="all"), x_col)
    x = work[x_col]
    y_actual = safe_numeric(work[y_cols[0]])
    fig, ax = plt.subplots(figsize=(8.8, 5.2))
    ax.plot(x, y_actual, color=PALETTE["blue"], linewidth=2.2, marker="o", markersize=4, label=y_cols[0])
    label_endpoints(ax, x, y_actual, y_cols[0], PALETTE["blue"])

    if len(y_cols) >= 2:
        y_pred = safe_numeric(work[y_cols[1]])
        ax.plot(
            x,
            y_pred,
            color=PALETTE["orange"],
            linewidth=2.0,
            marker="s",
            markersize=4,
            linestyle="--",
            label=y_cols[1],
        )
        label_endpoints(ax, x, y_pred, y_cols[1], PALETTE["orange"])
        subtitle = "用于论文结果展示：真实序列、预测序列与末端差异需要在正文中解释。"
    else:
        trend = y_actual.rolling(window=min(3, max(1, len(y_actual))), min_periods=1).mean()
        ax.plot(x, trend, color=PALETTE["orange"], linewidth=2.0, linestyle="--", label="趋势参考线")
        subtitle = "当前仅生成趋势参考线；正式预测线应由当前赛题模型结果替换。"

    apply_title(ax, title, subtitle)
    ax.set_xlabel(x_col)
    ax.set_ylabel("数值")
    ax.legend(loc="best")
    return save_figure(fig, output_path)


def plot_residual_distribution(df: pd.DataFrame, spec: dict[str, Any], output_path: Path) -> str:
    title = sanitize_text(spec.get("title"), "残差分布图")
    x_col = pick_x(df, spec)
    y_cols = pick_y(df, spec, x_col, limit=2)
    if not y_cols:
        return plot_empty(title, "缺少数值列，无法绘制残差分布", output_path)

    actual = safe_numeric(df[y_cols[0]])
    if len(y_cols) >= 2:
        residual = actual - safe_numeric(df[y_cols[1]])
        subtitle = f"残差 = {y_cols[0]} - {y_cols[1]}。正式论文需说明模型误差来源。"
    else:
        baseline = actual.rolling(window=min(3, max(1, len(actual))), min_periods=1).mean()
        residual = actual - baseline
        subtitle = "当前以局部趋势均值构造参考偏差；正式残差应由模型预测结果替换。"

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.8), gridspec_kw={"width_ratios": [1.2, 1]})
    sns.histplot(residual.dropna(), bins=18, kde=True, color=PALETTE["blue"], ax=axes[0])
    axes[0].axvline(0, color=PALETTE["red"], linewidth=1.2, linestyle="--")
    axes[0].set_xlabel("残差")
    axes[0].set_ylabel("频数")
    apply_title(axes[0], title, subtitle)

    ordered = residual.dropna().sort_values().reset_index(drop=True)
    if len(ordered) > 1:
        theoretical = np.linspace(-2, 2, len(ordered))
        axes[1].scatter(theoretical, ordered, color=PALETTE["green"], alpha=0.78, s=24)
        axes[1].axhline(0, color=PALETTE["red"], linewidth=1.0, linestyle="--")
    apply_title(axes[1], "残差分位参考", "用于检查偏差是否集中在零附近。")
    axes[1].set_xlabel("理论分位参考")
    axes[1].set_ylabel("残差")
    return save_figure(fig, output_path)


def plot_model_comparison(df: pd.DataFrame, spec: dict[str, Any], output_path: Path) -> str:
    title = sanitize_text(spec.get("title"), "模型或方案对比图")
    x_col = pick_x(df, spec)
    y_cols = pick_y(df, spec, x_col, limit=3)
    if not x_col or not y_cols:
        return plot_empty(title, "缺少分类列或指标列，无法绘制对比图", output_path)

    work = df[[x_col, *y_cols]].dropna(how="all").copy()
    if len(work) > 20:
        work = work.head(20)
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    x_positions = np.arange(len(work))
    width = min(0.75 / max(1, len(y_cols)), 0.32)
    for idx, column in enumerate(y_cols):
        offset = (idx - (len(y_cols) - 1) / 2) * width
        values = safe_numeric(work[column])
        ax.bar(
            x_positions + offset,
            values,
            width=width,
            label=column,
            color=list(PALETTE.values())[idx % len(PALETTE)],
            alpha=0.88,
        )
    ax.set_xticks(x_positions)
    ax.set_xticklabels(work[x_col].astype(str), rotation=30, ha="right")
    ax.set_ylabel("指标值")
    ax.legend(loc="best")
    apply_title(ax, title, "用于比较基线模型、主模型或不同方案；正式论文需说明指标方向。")
    return save_figure(fig, output_path)


def plot_sensitivity_curve(df: pd.DataFrame, spec: dict[str, Any], output_path: Path) -> str:
    title = sanitize_text(spec.get("title"), "敏感性分析图")
    x_col = pick_x(df, spec)
    y_cols = pick_y(df, spec, x_col, limit=3)
    if not y_cols:
        return plot_empty(title, "缺少敏感性指标列", output_path)

    work = sorted_for_x(df[[x_col, *y_cols]].dropna(how="all"), x_col) if x_col else df[y_cols].copy()
    fig, ax = plt.subplots(figsize=(8.8, 5.2))
    x = work[x_col] if x_col and x_col in work.columns else pd.Series(range(len(work)), name="扰动序号")
    for idx, column in enumerate(y_cols):
        y = safe_numeric(work[column])
        ax.plot(
            x,
            y,
            marker="o",
            linewidth=2.0,
            markersize=4,
            color=list(PALETTE.values())[idx % len(PALETTE)],
            label=column,
        )
    apply_title(ax, title, "用于展示参数、权重或阈值扰动下结论是否稳定。")
    ax.set_xlabel(x_col or "扰动序号")
    ax.set_ylabel("响应指标")
    ax.legend(loc="best")
    return save_figure(fig, output_path)


def plot_weight_bar(df: pd.DataFrame, spec: dict[str, Any], output_path: Path) -> str:
    title = sanitize_text(spec.get("title"), "指标权重图")
    x_col = pick_x(df, spec)
    y_cols = pick_y(df, spec, x_col, limit=1)
    if not y_cols:
        return plot_empty(title, "缺少权重或得分列", output_path)

    work = df[[x_col, y_cols[0]]].copy() if x_col else df[[y_cols[0]]].copy()
    if not x_col:
        work["指标"] = [f"指标{i + 1}" for i in range(len(work))]
        x_col = "指标"
    work[y_cols[0]] = safe_numeric(work[y_cols[0]])
    work = work.dropna().sort_values(y_cols[0], ascending=True).tail(20)
    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    colors = [PALETTE["blue"] if idx < len(work) - 1 else PALETTE["orange"] for idx in range(len(work))]
    ax.barh(work[x_col].astype(str), work[y_cols[0]], color=colors, alpha=0.9)
    ax.set_xlabel(y_cols[0])
    apply_title(ax, title, "用于评价/排序问题，正文需说明权重来源和标准化方法。")
    return save_figure(fig, output_path)


def plot_score_ranking(df: pd.DataFrame, spec: dict[str, Any], output_path: Path) -> str:
    title = sanitize_text(spec.get("title"), "综合得分排序图")
    x_col = pick_x(df, spec)
    y_cols = pick_y(df, spec, x_col, limit=1)
    if not x_col or not y_cols:
        return plot_empty(title, "缺少对象列或得分列", output_path)

    work = df[[x_col, y_cols[0]]].copy()
    work[y_cols[0]] = safe_numeric(work[y_cols[0]])
    work = work.dropna().sort_values(y_cols[0], ascending=True).tail(20)
    fig, ax = plt.subplots(figsize=(8.8, 5.4))
    ax.barh(work[x_col].astype(str), work[y_cols[0]], color=PALETTE["green"], alpha=0.88)
    ax.set_xlabel(y_cols[0])
    apply_title(ax, title, "用于展示方案、地区或样本的综合评价排序。")
    return save_figure(fig, output_path)


def plot_heatmap(df: pd.DataFrame, spec: dict[str, Any], output_path: Path) -> str:
    title = sanitize_text(spec.get("title"), "变量关系热力图")
    nums = numeric_columns(df)
    if len(nums) < 2:
        return plot_empty(title, "至少需要两个数值列才能绘制热力图", output_path)
    corr = df[nums[:10]].apply(pd.to_numeric, errors="coerce").corr()
    fig, ax = plt.subplots(figsize=(8.2, 6.4))
    mask = np.triu(np.ones_like(corr, dtype=bool))
    sns.heatmap(
        corr,
        mask=mask,
        cmap="RdBu_r",
        center=0,
        annot=True,
        fmt=".2f",
        linewidths=0.5,
        cbar_kws={"shrink": 0.78},
        ax=ax,
    )
    apply_title(ax, title, "用于说明变量相关结构；正式论文需解释高相关变量的含义。")
    return save_figure(fig, output_path)


def plot_scatter(df: pd.DataFrame, spec: dict[str, Any], output_path: Path) -> str:
    title = sanitize_text(spec.get("title"), "二维关系散点图")
    x_col = pick_x(df, spec)
    y_cols = pick_y(df, spec, x_col, limit=2)
    nums = numeric_columns(df)
    if (not x_col or x_col not in numeric_columns(df)) and nums:
        x_col = nums[0]
        y_cols = [col for col in nums if col != x_col][:2]
    if not x_col or not y_cols:
        return plot_empty(title, "缺少可绘制的二维数值列", output_path)

    fig, ax = plt.subplots(figsize=(8.4, 5.4))
    hue_candidates = categorical_columns(df, exclude={x_col, *y_cols})
    hue = hue_candidates[0] if hue_candidates and df[hue_candidates[0]].nunique() <= 12 else None
    sns.scatterplot(
        data=df,
        x=x_col,
        y=y_cols[0],
        hue=hue,
        size=y_cols[1] if len(y_cols) > 1 else None,
        sizes=(30, 140),
        alpha=0.78,
        color=PALETTE["blue"],
        ax=ax,
    )
    apply_title(ax, title, "用于展示样本分布、聚类结果或变量关系。")
    return save_figure(fig, output_path)


def plot_generic_line(df: pd.DataFrame, spec: dict[str, Any], output_path: Path) -> str:
    title = sanitize_text(spec.get("title"), "趋势变化图")
    x_col = pick_x(df, spec)
    y_cols = pick_y(df, spec, x_col, limit=3)
    if not x_col or not y_cols:
        return plot_empty(title, "缺少横轴或数值列", output_path)
    work = sorted_for_x(df[[x_col, *y_cols]].dropna(how="all"), x_col)
    fig, ax = plt.subplots(figsize=(8.8, 5.2))
    for idx, column in enumerate(y_cols):
        ax.plot(
            work[x_col],
            safe_numeric(work[column]),
            marker="o",
            linewidth=2.0,
            markersize=4,
            label=column,
            color=list(PALETTE.values())[idx % len(PALETTE)],
        )
    apply_title(ax, title, "用于论文结果展示；正式图题应包含变量、单位和样本范围。")
    ax.set_xlabel(x_col)
    ax.set_ylabel("数值")
    ax.legend(loc="best")
    return save_figure(fig, output_path)


def plot_empty(title: str, message: str, output_path: Path) -> dict[str, Any]:
    fig, ax = plt.subplots(figsize=(8.0, 4.5))
    ax.axis("off")
    ax.text(0.02, 0.72, title, fontsize=15, fontweight="bold", color="#111827", transform=ax.transAxes)
    wrapped = re.sub(r"(.{22})", r"\1\n", message)
    ax.text(0.02, 0.48, wrapped, fontsize=11, color=PALETTE["gray"], transform=ax.transAxes)
    ax.text(
        0.02,
        0.2,
        "该图是占位式图表模板。请结合当前赛题字段、模型输出和论文结论二次生成。",
        fontsize=9,
        color=PALETTE["orange"],
        transform=ax.transAxes,
    )
    return {
        "path": save_figure(fig, output_path),
        "placeholder": True,
        "message": message,
    }


def infer_template(spec: dict[str, Any]) -> str:
    hint = sanitize_text(spec.get("template_hint")).lower()
    if hint:
        return hint[5:] if hint.startswith("plot_") else hint
    text = f"{spec.get('chart_type', '')} {spec.get('title', '')} {spec.get('purpose', '')}".lower()
    rules = [
        ("prediction_comparison", ("预测", "预报", "真实值", "forecast", "prediction")),
        ("residual_distribution", ("残差", "误差分布", "residual")),
        ("sensitivity_curve", ("敏感性", "灵敏度", "扰动", "sensitivity")),
        ("model_comparison", ("模型对比", "方案对比", "基线", "对照", "comparison")),
        ("weight_bar", ("权重", "指标权重", "weight")),
        ("score_ranking", ("得分", "排序", "排名", "score", "ranking")),
        ("heatmap", ("热力", "相关", "矩阵", "heatmap", "correlation")),
        ("scatter", ("聚类", "分群", "散点", "cluster", "scatter")),
    ]
    for template, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return template
    chart_type = sanitize_text(spec.get("chart_type")).lower()
    if chart_type in {"line", "bar", "scatter", "heatmap"}:
        return chart_type
    return "line"


def plot_figure_spec(df: pd.DataFrame, spec: dict[str, Any], output_path: Path) -> dict[str, Any]:
    set_paper_style()
    template = infer_template(spec)
    try:
        if template == "prediction_comparison":
            plotted = plot_prediction_comparison(df, spec, output_path)
        elif template == "residual_distribution":
            plotted = plot_residual_distribution(df, spec, output_path)
        elif template == "sensitivity_curve":
            plotted = plot_sensitivity_curve(df, spec, output_path)
        elif template == "model_comparison":
            plotted = plot_model_comparison(df, spec, output_path)
        elif template == "weight_bar":
            plotted = plot_weight_bar(df, spec, output_path)
        elif template == "score_ranking":
            plotted = plot_score_ranking(df, spec, output_path)
        elif template == "heatmap":
            plotted = plot_heatmap(df, spec, output_path)
        elif template == "scatter":
            plotted = plot_scatter(df, spec, output_path)
        elif template == "bar":
            plotted = plot_model_comparison(df, spec, output_path)
        else:
            plotted = plot_generic_line(df, spec, output_path)
        if isinstance(plotted, dict) and plotted.get("placeholder"):
            return {
                "ok": False,
                "path": plotted.get("path", ""),
                "template": template,
                "placeholder": True,
                "message": str(plotted.get("message") or "placeholder figure"),
            }
        return {"ok": True, "path": plotted, "template": template, "placeholder": False, "message": ""}
    except Exception as exc:
        fallback = plot_empty(sanitize_text(spec.get("title"), "图表模板"), str(exc), output_path)
        return {
            "ok": False,
            "path": fallback.get("path", ""),
            "template": template,
            "placeholder": True,
            "message": str(exc),
        }
