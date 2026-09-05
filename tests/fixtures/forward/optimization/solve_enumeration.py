"""Independent exhaustive assignment search; no SciPy or shared solver code."""
import argparse
import itertools
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)
parser.add_argument("--out", required=True)
parser.add_argument("--scale", type=float, default=1)
parser.add_argument("--all-open", action="store_true")
args = parser.parse_args()
data = json.loads(Path(args.input).read_text(encoding="utf-8"))
demand = [v * args.scale for v in data["demand"]]
m, n = len(data["capacity"]), len(demand)
best, best_assignment, feasible = float("inf"), None, 0
for assignment in itertools.product(range(m), repeat=n):
    loads = [sum(demand[i] for i in range(n) if assignment[i] == j) for j in range(m)]
    if any(loads[j] > data["capacity"][j] + 1e-9 for j in range(m)):
        continue
    feasible += 1
    opened = set(range(m)) if args.all_open else set(assignment)
    cost = sum(data["fixed_cost"][j] for j in opened) + sum(demand[i] * data["unit_cost"][assignment[i]][i] for i in range(n))
    if cost < best:
        best, best_assignment = cost, assignment
if best_assignment is None:
    raise RuntimeError("No feasible assignment")
metrics = {"cost": best, "enumerated": m ** n, "feasible_count": feasible,
           "assignment": list(best_assignment), "open_count": len(set(best_assignment)),
           "max_violation": 0}
Path(args.out).mkdir(parents=True, exist_ok=True)
(Path(args.out) / "metrics.json").write_text(json.dumps({"metrics": metrics}, indent=2) + "\n", encoding="utf-8")
print(json.dumps(metrics))
