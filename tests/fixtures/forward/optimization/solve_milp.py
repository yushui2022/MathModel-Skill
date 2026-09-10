"""Binary capacitated facility location with a HiGHS optimality certificate."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)
parser.add_argument("--out", required=True)
parser.add_argument("--scale", type=float, default=1)
parser.add_argument("--seed", type=int)
parser.add_argument("--all-open", action="store_true")
args = parser.parse_args()
data = json.loads(Path(args.input).read_text(encoding="utf-8"))
demand = np.asarray(data["demand"], dtype=float) * args.scale
if args.seed is not None:
    demand *= np.random.default_rng(args.seed).uniform(0.9, 1.1, len(demand))
cost = np.asarray(data["unit_cost"], dtype=float)
m, n = cost.shape
c = np.concatenate([data["fixed_cost"], (cost * demand).ravel()])
rows, lo, hi = [], [], []
for i in range(n):
    row = np.zeros(m + m * n)
    row[m + i::n] = 1
    rows.append(row)
    lo.append(1)
    hi.append(1)
for j in range(m):
    row = np.zeros(m + m * n)
    row[j] = -data["capacity"][j]
    row[m + j * n:m + (j + 1) * n] = demand
    rows.append(row)
    lo.append(-np.inf)
    hi.append(0)
lower = np.zeros(len(c))
if args.all_open:
    lower[:m] = 1
solution = milp(c, integrality=np.ones(len(c)), bounds=Bounds(lower, np.ones(len(c))),
                constraints=LinearConstraint(np.asarray(rows), lo, hi), options={"mip_rel_gap": 0})
if not solution.success:
    raise RuntimeError(solution.message)
assignment = np.rint(solution.x[m:]).reshape(m, n)
load = assignment @ demand
metrics = {
    "cost": float(solution.fun), "lower_bound": float(solution.mip_dual_bound),
    "gap": float(solution.mip_gap), "max_violation": float(max(0, np.max(load - np.asarray(data["capacity"]) * np.rint(solution.x[:m])))),
    "open_count": int(np.rint(solution.x[:m]).sum()),
    "assignment": [int(x) for x in assignment.argmax(axis=0)],
    "loads": load.tolist(), "demand": demand.tolist(),
}
Path(args.out).mkdir(parents=True, exist_ok=True)
(Path(args.out) / "metrics.json").write_text(json.dumps({"metrics": metrics}, indent=2) + "\n", encoding="utf-8")
print(json.dumps(metrics))
