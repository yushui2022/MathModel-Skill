"""Build a disclosed constructed benchmark; never simulate final model reviews."""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tests"))
from pro_fixture import prepare_evidence, approve, run, envelope, SCRIPTS
from pro_contracts import read_json, write_json, sha256_file
from pro_run_experiment import execute, refresh_manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--simulate-checkpoints", action="store_true",
                        help="Required explicit opt-in: approvals/readers are test fixtures, not user decisions")
    args = parser.parse_args()
    if not args.simulate_checkpoints:
        parser.error("this engineering benchmark requires --simulate-checkpoints; not a competition workflow")
    project = args.output.resolve()
    if project.exists() and any(project.iterdir()):
        parser.error("benchmark output must be new or empty; existing evidence is never overwritten")
    project.mkdir(parents=True, exist_ok=True)
    root = prepare_evidence(project)
    fixture = REPO / "tests/fixtures/forward/optimization"
    shutil.copyfile(fixture / "plot_results.py", root / "code/plot_results.py")
    spec = root / "code/spec-chart.json"
    write_json(spec, {"run_id": "chart", "route_id": "r2", "implementation_id": "matplotlib-from-recorded-metrics",
        "script": "code/plot_results.py", "inputs": [f"experiments/{n}-milp/metrics.json" for n in ("base", "baseline", "stress")],
        "args": ["--out", "{run_dir}"]})
    _, passed = execute(project, spec)
    if not passed:
        raise RuntimeError("benchmark figure generation failed")
    refresh_manifest(root)
    approve(project, 3)
    run(SCRIPTS / "pro_freeze_evidence.py", "--project-root", project)
    values = [read_json(root / f"experiments/{n}-milp/metrics.json")["metrics"]["cost"] for n in ("base", "baseline", "stress")]
    text = (fixture / "paper.md").read_text(encoding="utf-8")
    for name, value in zip(("BASE", "BASELINE", "STRESS"), values):
        text = text.replace("{{"+name+"}}", f"{value:.2f}")
    (root / "final_paper_source.md").write_text(text, encoding="utf-8")
    sections = [("abstract", "摘要", 180), ("problem", "1 问题与数据", 280),
                ("assumptions", "2 假设与符号", 180), ("model", "3 模型构建", 240),
                ("methods", "4 求解与独立验证", 240), ("results", "5 结果与敏感性分析", 600),
                ("discussion", "6 讨论与结论", 400)]
    figure = "experiments/chart/cost-and-capacity.png"
    write_json(root / "paper_plan.json", envelope("benchmark-authoring-plan",
        title="容量约束下配送站点的选择与需求扰动分析", language="zh-CN", target_characters=3500,
        sections=[{"section_id": i, "title": t, "minimum_characters": n} for i, t, n in sections],
        figures=[{"path": figure, "sha256": sha256_file(root / figure)}]))
    write_json(project / "BENCHMARK_SCOPE.json", {
        "dataset": "constructed four-depot, five-customer instance; not a real contest",
        "simulated": ["P1 independent readers", "user checkpoint decisions"],
        "executed": ["six real independent solver runs", "chart from recorded outputs"],
        "not_yet_completed": ["five real isolated manuscript reviews", "DOCX/PDF rendering and actual page inspection"],
        "model_qualification": "No cross-model or real-contest qualification is implied",
    })
    run(SCRIPTS / "pro_paper_audit.py", "--project-root", project)
    print(f"Benchmark ready for REAL independent review: {root}")


if __name__ == "__main__":
    main()
