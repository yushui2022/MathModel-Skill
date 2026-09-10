"""Derive change impact from Pro execution records without changing approvals.

This is a dependency explanation, not a mathematical acceptance decision. Missing
raw-to-cleaned provenance widens impact conservatively. Optional provenance lives
under data_cleaned/provenance.json so Pro's existing freeze includes it.
"""
from __future__ import annotations

import argparse
from collections import defaultdict, deque
import json
from pathlib import Path
import sys

from .context import digest_file, read_contract, safe_file

OUTPUT = "paper_output_pro"
MAX_FILES = 10000
GLOBAL_INPUTS = {f"{OUTPUT}/{name}" for name in ("pro_config.json", "input_manifest.json", "problem_consensus.json", "candidate_routes.json", "tournament_report.json", "optimization_applicability.json")}


def _project_path(value: str, *, already_project: bool = False) -> str:
    raw = str(value).replace("\\", "/")
    if not raw or raw.startswith("/") or ":" in raw or ".." in Path(raw).parts:
        raise ValueError(f"Expected a safe project-relative path: {value}")
    if already_project or raw.startswith(("problem_files/", OUTPUT + "/")):
        return raw
    return f"{OUTPUT}/{raw}"


def build_dependency_graph(project_root: str | Path) -> dict:
    project = Path(project_root).expanduser().resolve()
    base = safe_file(project, OUTPUT)
    nodes: dict[str, dict] = {}
    edges: set[tuple[str, str, str]] = set()
    diagnostics: list[str] = []
    run_inputs, run_outputs = {}, {}

    def node(identifier, kind, **data):
        if identifier not in nodes:
            nodes[identifier] = {"id": identifier, "kind": kind, **data}
        return identifier

    def edge(left, right, relation):
        edges.add((left, right, relation))

    def file(value, expected=None, *, already_project=False):
        name = _project_path(value, already_project=already_project)
        safe_file(project, name)
        identifier = node("file:" + name, "file", path=name, expected_hashes=[])
        if expected and expected not in nodes[identifier]["expected_hashes"]:
            nodes[identifier]["expected_hashes"].append(expected)
        return identifier

    def read(value):
        path = _project_path(value)
        data, source = read_contract(project, path)
        if source.get("error"):
            diagnostics.append(f"{path}: {source['error']}")
        return data or {}

    freeze = read("evidence_freeze.json")
    for name, digest in freeze.get("file_hashes", {}).items():
        file(name, digest)
    original = read("input_manifest.json")
    for item in original.get("files", []):
        if isinstance(item, dict) and item.get("path"):
            file(item["path"], item.get("sha256"), already_project=True)
    routes = read("candidate_routes.json")
    route_questions = {str(r.get("route_id")): str(q.get("subproblem_id", "")) for q in routes.get("subproblems", []) if isinstance(q, dict) for r in q.get("routes", []) if isinstance(r, dict)}
    manifest = read("experiment_manifest.json")
    recorded = {r.get("receipt_path"): r.get("receipt_sha256") for r in manifest.get("runs", []) if isinstance(r, dict)}
    receipts_dir = safe_file(project, f"{OUTPUT}/experiments")
    receipts = sorted(receipts_dir.glob("*/receipt.json"))
    if len(receipts) > MAX_FILES:
        raise ValueError("Too many experiment receipts; partition the project before impact analysis")
    for path in receipts:
        name = path.relative_to(base).as_posix()
        receipt = read(name)
        run_id = str(receipt.get("run_id", ""))
        if not run_id:
            diagnostics.append(f"{name}: missing run identity")
            continue
        rid = "run:" + run_id
        if rid in nodes:
            diagnostics.append(f"duplicate run ID: {run_id}")
            continue
        qid = route_questions.get(str(receipt.get("route_id")), "")
        node(rid, "run", run_id=run_id, route_id=receipt.get("route_id"), question_ids=[qid] if qid else [], recorded_status=receipt.get("status", "UNKNOWN"))
        edge(file(name, recorded.get(name)), rid, "execution_receipt")
        if name not in recorded:
            diagnostics.append(f"{name}: receipt not indexed by experiment_manifest")
        run_inputs[run_id], run_outputs[run_id] = set(), set()
        for field in ("input_hashes", "script_hashes"):
            hashes = receipt.get(field)
            if not isinstance(hashes, dict) or not hashes:
                diagnostics.append(f"{run_id}: missing {field}; dependency coverage incomplete")
                continue
            for path_name, digest in hashes.items():
                fid = file(path_name, digest)
                edge(fid, rid, field)
                run_inputs[run_id].add(nodes[fid]["path"])
        if receipt.get("spec_path"):
            edge(file(receipt["spec_path"], receipt.get("spec_sha256")), rid, "run_specification")
        else:
            diagnostics.append(f"{run_id}: no run specification")
        for path_name, digest in receipt.get("output_hashes", {}).items():
            fid = file(path_name, digest)
            edge(rid, fid, "produces")
            run_outputs[run_id].add(nodes[fid]["path"])
        metrics_name = receipt.get("metrics_file")
        if metrics_name:
            for key in read(metrics_name).get("metrics", {}):
                mid = node(f"metric:{run_id}:{key}", "metric", run_id=run_id, metric=key)
                edge(file(metrics_name), mid, "metric_value")
                edge(rid, mid, "measured_by")
        for global_path in GLOBAL_INPUTS:
            edge(file(global_path), rid, "approved_problem_and_route")

    for binding in read("optimization_applicability.json").get("routes", []):
        if not isinstance(binding, dict) or not binding.get("spec_path"):
            continue
        spec_file = file(binding["spec_path"])
        spec = read(binding["spec_path"])
        for name, expected in spec.get("input_hashes", {}).items():
            edge(file(name, expected), spec_file, "mathematical_specification_input")
        for rid, item in list(nodes.items()):
            if item["kind"] == "run" and item.get("route_id") == binding.get("route_id"):
                edge(spec_file, rid, "mathematical_specification")

    provenance = read("data_cleaned/provenance.json")
    provenance_paths = set()
    for transform in provenance.get("transforms", []):
        if not isinstance(transform, dict):
            diagnostics.append("invalid data transform declaration")
            continue
        inputs, outputs = transform.get("input_hashes"), transform.get("output_hashes")
        if not isinstance(inputs, dict) or not inputs or not isinstance(outputs, dict) or not outputs:
            diagnostics.append("data transform needs nonempty input/output hash maps")
            continue
        for out, out_hash in outputs.items():
            output_file = file(out, out_hash, already_project=True)
            scripts = transform.get("script_hashes", {})
            if not isinstance(scripts, dict):
                diagnostics.append("data transform script_hashes must be a hash map")
                scripts = {}
            for inp, inp_hash in {**inputs, **scripts}.items():
                input_file = file(inp, inp_hash, already_project=True)
                edge(input_file, output_file, "declared_data_transform")
                provenance_paths.add(nodes[input_file]["path"])
            edge(file("data_cleaned/provenance.json"), output_file, "provenance_declaration")

    replication = read("replication_report.json")
    for evidence in replication.get("critical_results", []):
        if not isinstance(evidence, dict) or not evidence.get("result_id"):
            continue
        eid = node("evidence:" + evidence["result_id"], "evidence", evidence_id=evidence["result_id"])
        for ref in evidence.get("replication_paths", []):
            mid = f"metric:{ref.get('run_id')}:{ref.get('metric')}"
            if mid not in nodes:
                diagnostics.append(f"{evidence['result_id']}: missing metric dependency {mid}")
                mid = node(mid, "metric", run_id=ref.get("run_id"), metric=ref.get("metric"), missing=True)
                rid = "run:" + str(ref.get("run_id"))
                if rid in nodes:
                    edge(rid, mid, "unresolved_metric")
            edge(mid, eid, "independent_replication")
        edge(file("replication_report.json"), eid, "replication_contract")

    source_map = {s.get("source_id"): s for s in read("source_ledger.json").get("sources", []) if isinstance(s, dict)}
    for claim in read("claim_evidence_map.json").get("claims", []):
        if not isinstance(claim, dict) or not claim.get("claim_id"):
            continue
        cid = node("claim:" + claim["claim_id"], "claim", claim_id=claim["claim_id"], section_id=claim.get("section_id"))
        for value in claim.get("evidence_ids", []):
            eid = "evidence:" + str(value)
            if eid not in nodes:
                diagnostics.append(f"{claim['claim_id']}: missing evidence {value}")
                node(eid, "evidence", evidence_id=value, missing=True)
            edge(eid, cid, "supports_claim")
        for source_id in claim.get("source_ids", []):
            source = source_map.get(source_id, {})
            for key in ("snapshot_path", "retrieval_receipt"):
                if source.get(key):
                    edge(file(source[key]), cid, "external_evidence")
        for numeric in claim.get("numeric_evidence", []):
            if not isinstance(numeric, dict):
                continue
            mid = f"metric:{numeric.get('run_id')}:{numeric.get('metric')}"
            if mid in nodes:
                edge(mid, cid, "numeric_claim_value")
            else:
                diagnostics.append(f"{claim['claim_id']}: missing numeric dependency {mid}")
        edge(file("claim_evidence_map.json"), cid, "claim_contract")
        if claim.get("section_id"):
            sid = node("section:" + str(claim["section_id"]), "section", section_id=claim["section_id"])
            edge(cid, sid, "used_in_section")
    freeze_node = node("gate:freeze", "gate", name="new evidence freeze requires current approval")
    review_node = node("gate:review", "gate", name="five-role review of latest paper")
    delivery_node = node("gate:delivery", "gate", name="Pro final gate")
    for name in freeze.get("file_hashes", {}):
        edge(file(name), freeze_node, "frozen_inventory")
    for nid, item in list(nodes.items()):
        if item["kind"] == "section":
            edge(nid, review_node, "review_affected_section")
    edge(file("final_paper_source.md"), review_node, "manuscript_changed")
    edge(file("paper_plan.json"), review_node, "authoring_plan_changed")
    # Manuscripts are intentionally outside Pro's evidence freeze; their
    # current baseline comes from the real paper/review/format input hashes.
    for report_name in ("paper_audit.json", "review_board_report.json", "final_format_report.json", "pro_gate_report.json"):
        report = read(report_name)
        for name, expected in report.get("input_hashes", {}).items():
            file(name, expected)
        if report:
            edge(file(report_name), delivery_node, "recorded_delivery_check")
    edge(freeze_node, review_node, "review_frozen_evidence")
    edge(review_node, delivery_node, "latest_review_required")
    return {"schema_version": "1.0", "project_root": str(project), "output_root": str(base),
            "nodes": nodes, "edges": [{"from": a, "to": b, "relation": c} for a, b, c in sorted(edges)],
            "diagnostics": diagnostics, "run_inputs": {k: sorted(v) for k, v in run_inputs.items()},
            "run_outputs": {k: sorted(v) for k, v in run_outputs.items()}, "provenance_paths": sorted(provenance_paths),
            "has_freeze": bool(freeze.get("file_hashes"))}


def get_change_impact(project_root: str | Path, changed_paths: list[str] | None = None) -> dict:
    graph = build_dependency_graph(project_root)
    project = Path(graph["project_root"])
    nodes = graph["nodes"]
    if changed_paths is not None and (not isinstance(changed_paths, list) or len(changed_paths) > 256):
        raise ValueError("changed_paths must be an array with at most 256 project-relative paths")
    changed, diagnostics = set(), list(graph["diagnostics"])
    for nid, item in nodes.items():
        if item["kind"] != "file":
            continue
        if not item["expected_hashes"]:
            if graph["has_freeze"] and item["path"] in GLOBAL_INPUTS and safe_file(project, item["path"]).is_file():
                changed.add(item["path"])
            continue
        try:
            actual = digest_file(safe_file(project, item["path"]))
            if any(value != actual for value in item["expected_hashes"]):
                changed.add(item["path"])
        except (OSError, ValueError):
            changed.add(item["path"])
    if changed_paths is not None:
        for name in changed_paths:
            normalized = _project_path(name, already_project=True)
            safe_file(project, normalized)
            changed.add(normalized)
    # New raw files were not in the original manifest and cannot silently be
    # excluded. New run receipts or scripts likewise require evidence review.
    inventory_roots = ("problem_files", *[f"{OUTPUT}/{name}" for name in ("code", "experiments", "optimization_specs", "data_cleaned", "research", "figures", "tables", "analysis/independent")])
    for relative in inventory_roots:
        count = 0
        for path in safe_file(project, relative).rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            count += 1
            if count > MAX_FILES:
                diagnostics.append(f"{relative}: file inventory limit reached")
                break
            name = path.relative_to(project).as_posix()
            safe_file(project, name)
            if "file:" + name not in nodes:
                changed.add(name)
    adjacent = defaultdict(list)
    for edge in graph["edges"]:
        adjacent[edge["from"]].append(edge["to"])
    queue = deque("file:" + name for name in sorted(changed))
    affected, parents = set(queue), {}
    while queue:
        current = queue.popleft()
        for target in adjacent[current]:
            if target not in affected:
                affected.add(target)
                parents[target] = current
                queue.append(target)
    all_runs = {n[4:] for n, v in nodes.items() if v["kind"] == "run"}
    affected_runs = {n[4:] for n in affected if n.startswith("run:")}
    unknown_paths = [p for p in changed if "file:" + p not in nodes]
    unmapped_raw = [p for p in changed if p.startswith("problem_files/") and p not in graph["provenance_paths"] and not any(p in v for v in graph["run_inputs"].values())]
    unmapped_code = [p for p in changed if p.startswith(f"{OUTPUT}/code/") and not any(nodes.get(target, {}).get("kind") == "run" for target in adjacent["file:" + p]) and p not in graph["provenance_paths"]]
    conservative = bool(unknown_paths or unmapped_raw or unmapped_code or diagnostics)
    if conservative and changed:
        diagnostics += [f"No complete dependency path for {p}; all recorded runs require revalidation" for p in sorted(set(unknown_paths + unmapped_raw + unmapped_code))]
        affected_runs.update(all_runs)
        queue = deque("run:" + r for r in sorted(all_runs))
        affected.update(queue)
        while queue:
            for target in adjacent[queue.popleft()]:
                if target not in affected:
                    affected.add(target)
                    queue.append(target)
    # Stable topological run order based on actual declared intermediate files.
    dependencies = {r: set() for r in affected_runs}
    for later in affected_runs:
        for earlier in affected_runs - {later}:
            if set(graph["run_outputs"].get(earlier, [])) & set(graph["run_inputs"].get(later, [])):
                dependencies[later].add(earlier)
    ordered = []
    pending = dict(dependencies)
    while pending:
        ready = sorted(r for r, deps in pending.items() if not deps)
        if not ready:
            diagnostics.append("Cycle in run dependencies; inspect before executing any suggested queue")
            ordered += sorted(pending)
            conservative = True
            break
        ordered += ready
        for r in ready:
            pending.pop(r)
        for deps in pending.values():
            deps.difference_update(ready)
    def reason(rid):
        chain, current = ["run:" + rid], "run:" + rid
        while current in parents and len(chain) < 30:
            current = parents[current]
            chain.append(current)
        return list(reversed(chain)) if len(chain) > 1 else ["conservative dependency revalidation"]
    return {"schema_version": "1.0", "project_root": str(project), "changed": sorted(changed),
            "affected_nodes": [nodes[n] for n in sorted(affected) if n in nodes],
            "affected_runs": sorted(affected_runs),
            "affected_claims": sorted(n[6:] for n in affected if n.startswith("claim:")),
            "affected_sections": sorted(n[8:] for n in affected if n.startswith("section:")),
            "recompute_queue": [{"run_id": r, "question_ids": nodes["run:" + r]["question_ids"], "dependency_path": reason(r), "requires_fresh_approval": True} for r in ordered],
            "preserved_runs": sorted(all_runs - affected_runs), "conservative": conservative,
            "diagnostics": sorted(set(diagnostics)), "has_frozen_baseline": graph["has_freeze"],
            "coverage": "Declared receipt/spec/provenance dependencies only; arbitrary undeclared file or network reads cannot be proven absent. Preserved runs still require current Pro validation.",
            "approval_policy": "Advisory only. Preserve history; reuse only after current Pro validation. Changed approvals, complete evidence freeze and all five final reviews remain required."}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--changed", action="append", dest="changed_paths")
    args = parser.parse_args()
    print(json.dumps(get_change_impact(args.project_root, args.changed_paths), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
