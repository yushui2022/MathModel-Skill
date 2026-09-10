"""Plot recorded benchmark results; never invent paper measurements."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument("--out", required=True)
args = parser.parse_args()
base, baseline, stress = [json.loads(Path(f"experiments/{name}-milp/metrics.json").read_text())["metrics"]
                          for name in ("base", "baseline", "stress")]
fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), layout="constrained")
colors = ["#56616b", "#087e8b", "#a13d63"]
bars = axes[0].bar(["All open", "Optimized", "Demand +20%\n(reoptimized)"],
                   [baseline["cost"], base["cost"], stress["cost"]], color=colors, width=0.6)
axes[0].bar_label(bars, fmt="%.2f", padding=4)
axes[0].set(ylim=(0, 195), ylabel="Cost per period (constructed units)", title="A  Comparable objective values")
x = np.arange(2)
for offset, values, label, color in ((-.24, [base["loads"][1], base["loads"][3]], "Base assignment", colors[1]),
                                   (0, [base["loads"][1]*1.2, base["loads"][3]*1.2], "Fixed assignment +20%", colors[2]),
                                   (.24, [stress["loads"][1], stress["loads"][3]], "Reassigned +20%", colors[0])):
    bars = axes[1].bar(x+offset, values, width=.22, label=label, color=color)
    axes[1].bar_label(bars, fmt="%.1f", padding=2, fontsize=8)
for index, capacity in enumerate([15, 13]):
    axes[1].plot([index-.4, index+.4], [capacity, capacity], color="black", linestyle="--", linewidth=1.3)
axes[1].set(xticks=x, xticklabels=["Depot 2", "Depot 4"], ylim=(0, 23), ylabel="Demand units per period",
            title="B  Capacity versus assignment policy")
axes[1].legend(frameon=False, fontsize=8, loc="upper left")
for ax in axes:
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_axisbelow(True)
    ax.grid(axis="y", color="#e1e4e6", linewidth=.6)
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
fig.savefig(out / "cost-and-capacity.png", dpi=180)
plt.close(fig)
(out / "metrics.json").write_text(json.dumps({"metrics": {"base_cost": base["cost"],
    "baseline_cost": baseline["cost"], "stress_cost": stress["cost"]}}, indent=2)+"\n")
