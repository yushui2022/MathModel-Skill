"""Shared validators for checkpoints, evidence freezing and final delivery."""
from __future__ import annotations

import math
from pathlib import Path
from urllib.parse import urlparse

from pro_contracts import (
    canonical_json_hash, check_hashes, read_json, safe_path, sha256_file,
    valid_sha256, valid_utc, validate_envelope,
)

REVIEW_ROLES = {
    "mathematical_correctness", "code_reproducibility", "source_provenance",
    "paper_expression", "adversarial_challenge",
}
DIMENSIONS = {
    "task_fit", "data_feasibility", "validation_strength", "robustness",
    "interpretability", "innovation_value", "implementation_risk",
}


def finite(value) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def objects(value, name: str, *, empty: bool = False) -> list[dict]:
    if not isinstance(value, list) or (not empty and not value) or any(not isinstance(x, dict) for x in value):
        raise ValueError(f"{name} must be an array of objects")
    return value


def unique(items: list[dict], key: str) -> dict:
    result = {}
    for item in items:
        identifier = item.get(key)
        if not isinstance(identifier, str) or not identifier.strip() or identifier in result:
            raise ValueError(f"missing or duplicate {key}")
        result[identifier] = item
    return result


def check_sources(root: Path, data: dict) -> list[str]:
    errors = []
    sources = unique(objects(data.get("sources"), "sources", empty=True), "source_id")
    for source_id, source in sources.items():
        url = urlparse(str(source.get("url", "")))
        if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password:
            errors.append(f"{source_id}: invalid source URL")
        if not all(source.get(k) for k in ("title", "publisher", "purpose", "claim_ids")):
            errors.append(f"{source_id}: incomplete source metadata")
        if not valid_utc(source.get("accessed_at_utc")):
            errors.append(f"{source_id}: invalid access time")
        if source.get("authorization_required") is not False or source.get("access_status") != "PUBLIC_OK":
            errors.append(f"{source_id}: public access not established; private sources require a separate approved adapter")
        snapshot = safe_path(root, source.get("snapshot_path", ""))
        receipt_path = safe_path(root, source.get("retrieval_receipt", ""))
        errors.extend(check_hashes(root, {
            source["snapshot_path"]: source.get("content_sha256"),
            source["retrieval_receipt"]: source.get("retrieval_receipt_sha256"),
        }))
        if not snapshot.is_file() or snapshot.stat().st_size == 0 or not receipt_path.is_file():
            errors.append(f"{source_id}: missing retrieved content")
            continue
        errors.extend(validate_envelope(receipt_path, {"PASS"}))
        receipt = read_json(receipt_path)
        if (receipt.get("url") != source.get("url") or receipt.get("content_sha256") != source.get("content_sha256")
                or receipt.get("snapshot_path") != source.get("snapshot_path")
                or receipt.get("accessed_at_utc") != source.get("accessed_at_utc")
                or receipt.get("http_status") != 200):
            errors.append(f"{source_id}: retrieval receipt does not match source")
    for claim in unique(objects(data.get("critical_claims", []), "critical_claims", empty=True), "claim_id").values():
        ids = claim.get("source_ids", [])
        if not ids or len(set(ids)) != len(ids) or any(i not in sources for i in ids):
            errors.append(f"critical claim {claim.get('claim_id')}: unknown or missing sources")
            continue
        if any(claim.get("claim_id") not in sources[i].get("claim_ids", []) for i in ids):
            errors.append(f"critical claim {claim.get('claim_id')}: broken reverse source link")
        if claim.get("cross_validation_required", True):
            publishers = {str(sources[i]["publisher"]).strip().casefold() for i in ids}
            if len(publishers) < 2:
                errors.append(f"critical claim {claim.get('claim_id')}: needs two independent publishers")
        elif not claim.get("single_source_reason"):
            errors.append(f"critical claim {claim.get('claim_id')}: single-source exception needs a reason")
    return errors


def check_tournament(candidates: dict, report: dict, consensus: dict | None = None) -> list[str]:
    errors = []
    problems = unique(objects(candidates.get("subproblems"), "subproblems"), "subproblem_id")
    decisions = unique(objects(report.get("decisions"), "decisions"), "subproblem_id")
    if set(problems) != set(decisions):
        errors.append("tournament decisions do not cover exactly the candidate subproblems")
    if consensus and set(problems) != set(unique(objects(consensus.get("subproblems"), "consensus subproblems"), "subproblem_id")):
        errors.append("tournament omits or invents a confirmed subproblem")
    weights = candidates.get("weights", {})
    if set(weights) != DIMENSIONS or any(not finite(v) or v < 0 for v in weights.values()) or not math.isclose(sum(weights.values()), 1, abs_tol=1e-9):
        errors.append("tournament requires preregistered seven-dimension weights summing to one")
    for problem_id, problem in problems.items():
        routes = unique(objects(problem.get("routes"), "routes"), "route_id")
        if not 3 <= len(routes) <= 5:
            errors.append(f"{problem_id}: requires 3-5 routes")
        if not any(r.get("is_interpretable_baseline") is True for r in routes.values()):
            errors.append(f"{problem_id}: missing interpretable baseline")
        families = {str(r.get("model_family", "")).strip().casefold() for r in routes.values()}
        if "" in families or len(families) != len(routes):
            errors.append(f"{problem_id}: route families must be substantively distinct")
        for route_id, route in routes.items():
            scores = route.get("scores", {})
            if set(scores) != DIMENSIONS or any(not finite(v) or not 0 <= v <= 10 for v in scores.values()):
                errors.append(f"{problem_id}/{route_id}: invalid scores")
            if not route.get("experiment_plan") or not route.get("expected_evidence"):
                errors.append(f"{problem_id}/{route_id}: incomplete experiment plan")
        decision = decisions.get(problem_id, {})
        selected, backup = decision.get("selected_route_id"), decision.get("backup_route_id")
        if selected not in routes or backup not in routes or selected == backup:
            errors.append(f"{problem_id}: invalid selected/backup route")
        rejected = unique(objects(decision.get("rejected_routes", []), "rejected routes", empty=True), "route_id")
        if set(rejected) != set(routes) - {selected, backup} or any(not x.get("reason") for x in rejected.values()):
            errors.append(f"{problem_id}: missing route rejection reasons")
        if not decision.get("recommended_experiment_plan") or not decision.get("implementation_risks"):
            errors.append(f"{problem_id}: missing experiment plan or risks")
    if not isinstance(report.get("comparison_rules"), dict) or not report["comparison_rules"]:
        errors.append("tournament must preregister comparison_rules by result_id")
    return errors


def receipts(root: Path, manifest: dict) -> tuple[dict, list[str]]:
    errors = []
    runs = unique(objects(manifest.get("runs"), "runs"), "run_id")
    result = {}
    recorded_paths = set()
    for run_id, entry in runs.items():
        path = safe_path(root, entry.get("receipt_path", ""))
        recorded_paths.add(path)
        if not path.is_relative_to((root / "experiments").resolve()):
            errors.append(f"{run_id}: receipt outside experiments")
        errors.extend(check_hashes(root, {entry["receipt_path"]: entry.get("receipt_sha256")}))
        if not path.is_file():
            continue
        errors.extend(validate_envelope(path, {"PASS", "FAILED"}))
        run = read_json(path)
        result[run_id] = run
        errors.extend(check_hashes(root, {run.get("spec_path", ""): run.get("spec_sha256")}))
        if run.get("run_id") != run_id or run.get("producer_role") != "pro-experiment-runner":
            errors.append(f"{run_id}: mismatched execution receipt")
        for key in ("script_hashes", "input_hashes", "output_hashes"):
            errors.extend(f"{run_id}/{key}: {e}" for e in check_hashes(root, run.get(key)))
        if not run.get("argv") or not run.get("environment") or not run.get("implementation_id") or not run.get("route_id"):
            errors.append(f"{run_id}: missing execution identity or environment")
        if not valid_utc(run.get("started_at_utc")) or not valid_utc(run.get("finished_at_utc")):
            errors.append(f"{run_id}: missing execution times")
        if type(run.get("exit_code")) is not int:
            errors.append(f"{run_id}: invalid exit code")
        elif run.get("status") == "PASS" and run["exit_code"] != 0:
            errors.append(f"{run_id}: successful receipt has nonzero exit code")
        if run.get("status") == "FAILED" and not run.get("failure_reason"):
            errors.append(f"{run_id}: failure record missing reason")
        if run.get("status") == "PASS":
            metric_file = run.get("metrics_file", "")
            if metric_file not in run.get("output_hashes", {}):
                errors.append(f"{run_id}: metrics are not a recorded output")
            else:
                metrics = read_json(safe_path(root, metric_file)).get("metrics")
                if not isinstance(metrics, dict) or not metrics:
                    errors.append(f"{run_id}: empty metrics")
                elif any(not (finite(v) or (isinstance(v, list) and v and all(finite(x) for x in v))) for v in metrics.values()):
                    errors.append(f"{run_id}: nonnumeric or nonfinite metrics")
    actual = {p.resolve() for p in (root / "experiments").glob("*/receipt.json")}
    if actual != recorded_paths:
        errors.append("experiment manifest omits execution receipts, including failed runs")
    return result, errors


def metric(root: Path, runs: dict, reference: dict):
    run = runs.get(reference.get("run_id"), {})
    if run.get("status") != "PASS" or run.get("exit_code") != 0:
        raise ValueError(f"metric refers to an unsuccessful or unknown run: {reference}")
    values = read_json(safe_path(root, run.get("metrics_file", ""))).get("metrics", {})
    name = reference.get("metric")
    if name not in values:
        raise ValueError(f"missing metric {name}")
    value = values[name]
    if not (finite(value) or (isinstance(value, list) and value and all(finite(x) for x in value))):
        raise ValueError(f"invalid numeric metric {name}")
    return value


def compare(left, right, rule: dict) -> bool:
    kind = rule.get("kind")
    if kind == "exact":
        return left == right
    if kind == "numeric":
        atol, rtol = rule.get("atol"), rule.get("rtol")
        if not finite(atol) or not finite(rtol) or atol < 0 or not 0 <= rtol < 1:
            raise ValueError("numeric comparison requires nonnegative atol and rtol < 1")
        a = left if isinstance(left, list) else [left]
        b = right if isinstance(right, list) else [right]
        return len(a) == len(b) and all(math.isclose(x, y, abs_tol=atol, rel_tol=rtol) for x, y in zip(a, b))
    if kind == "statistical":
        from scipy import stats
        import numpy as np

        margin, alpha = rule.get("equivalence_margin"), rule.get("alpha")
        if not finite(margin) or margin <= 0 or not finite(alpha) or not 0 < alpha < 0.5:
            raise ValueError("statistical comparison needs preregistered equivalence_margin and alpha")
        if not isinstance(left, list) or not isinstance(right, list) or min(len(left), len(right)) < 10:
            return False
        a, b = np.asarray(left), np.asarray(right)
        variance = a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b)
        width = stats.t.ppf(1 - alpha / 2, min(len(a), len(b)) - 1) * math.sqrt(variance)
        difference = float(a.mean() - b.mean())
        return abs(difference) + width <= margin and stats.ks_2samp(a, b).pvalue >= alpha
    raise ValueError(f"unknown comparison kind: {kind}")


def check_replication(root: Path, data: dict, runs: dict, tournament: dict) -> list[str]:
    errors = []
    results = unique(objects(data.get("critical_results"), "critical results"), "result_id")
    rules = tournament.get("comparison_rules", {})
    if set(results) != set(rules):
        errors.append("replication results do not cover exactly the preregistered results")
    for result_id, result in results.items():
        paths = objects(result.get("replication_paths"), "replication paths")
        ids = [p.get("run_id") for p in paths]
        implementations = {runs.get(i, {}).get("implementation_id") for i in ids}
        script_sets = {canonical_json_hash(runs.get(i, {}).get("script_hashes", {})) for i in ids}
        script_contents = {tuple(sorted(runs.get(i, {}).get("script_hashes", {}).values())) for i in ids}
        if len(paths) < 2 or len(set(ids)) != len(ids) or len(implementations) < 2 or None in implementations or len(script_sets) < 2 or len(script_contents) < 2:
            errors.append(f"{result_id}: fewer than two distinct recorded implementations")
        if not result.get("independence_rationale"):
            errors.append(f"{result_id}: missing independence rationale")
        rule = result.get("comparison_rule")
        if rule != rules.get(result_id) or not isinstance(rule, dict):
            errors.append(f"{result_id}: comparison differs from approved rule")
            continue
        values = [metric(root, runs, p) for p in paths]
        if any(not compare(values[0], v, rule) for v in values[1:]) or result.get("agreement_status") != "PASS":
            errors.append(f"{result_id}: independent numeric comparison failed")
    return errors


def check_robustness(root: Path, data: dict, runs: dict) -> list[str]:
    errors = []
    for field in ("baseline_comparisons", "sensitivity_tests", "constraint_stress_tests"):
        for item in objects(data.get(field), field):
            refs = objects(item.get("measurements"), f"{field} measurements")
            if not item.get("interpretation") or not item.get("test_id"):
                errors.append(f"{field}: missing test identity or interpretation")
            for ref in refs:
                value = metric(root, runs, ref)
                if not finite(value) or not finite(ref.get("value")) or not math.isclose(value, ref["value"], rel_tol=1e-9, abs_tol=1e-12):
                    errors.append(f"{field}: measurement disagrees with recorded output")
            if field == "constraint_stress_tests" and not item.get("feasibility_assessment"):
                errors.append("stress test needs feasibility assessment, including failures")
    covered = set()
    for item in objects(data.get("stochastic_methods", []), "stochastic methods", empty=True):
        from scipy import stats
        import numpy as np

        ids = item.get("run_ids", [])
        covered.update(ids)
        seeds = [runs.get(i, {}).get("seed") for i in ids]
        if len(set(ids)) != len(ids) or len(set(seeds)) < 10 or any(type(s) is not int for s in seeds):
            errors.append("randomized method requires at least 10 unique recorded seeds")
            continue
        values = [metric(root, runs, {"run_id": i, "metric": item.get("metric")}) for i in ids]
        if not all(finite(v) for v in values):
            errors.append("stochastic summary needs scalar observations")
            continue
        level = item.get("confidence_level")
        if not finite(level) or not 0.5 < level < 1:
            errors.append("invalid confidence level")
            continue
        mean, variance = float(np.mean(values)), float(np.var(values, ddof=1))
        half = float(stats.t.ppf((1 + level) / 2, len(values) - 1) * math.sqrt(variance / len(values)))
        expected = [mean - half, mean + half]
        ci = item.get("confidence_interval")
        if (not finite(item.get("mean")) or not finite(item.get("variance"))
                or not isinstance(ci, list) or len(ci) != 2 or not all(finite(v) for v in ci)
                or not math.isclose(item["mean"], mean, rel_tol=1e-8, abs_tol=1e-10)
                or not math.isclose(item["variance"], variance, rel_tol=1e-8, abs_tol=1e-10)
                or any(not math.isclose(a, b, rel_tol=1e-8, abs_tol=1e-10) for a, b in zip(ci, expected))):
            errors.append("stochastic statistics disagree with recorded observations")
        target = item.get("target_half_width")
        if not finite(target) or target <= 0 or half > target or item.get("interval_stable") is not True:
            errors.append("stochastic interval has not met its declared precision target")
    randomized = {i for i, r in runs.items() if r.get("stochastic") is True and r.get("status") == "PASS"}
    if randomized - covered:
        errors.append("successful randomized runs omitted from stochastic summaries")
    return errors


def check_ablation(root: Path, data: dict, runs: dict) -> list[str]:
    tests = objects(data.get("ablations", []), "ablations", empty=True)
    if not tests:
        return [] if data.get("not_applicable_reason") else ["ablation report needs experiments or a reason"]
    errors = []
    for item in tests:
        left, right = metric(root, runs, item.get("with_component", {})), metric(root, runs, item.get("without_component", {}))
        if not item.get("component") or not item.get("interpretation") or not finite(left) or not finite(right) or not finite(item.get("effect")) or not math.isclose(right - left, item["effect"], rel_tol=1e-9, abs_tol=1e-12):
            errors.append("ablation effect disagrees with measured outputs")
    return errors


def check_claims(root: Path, data: dict, runs: dict, replication: dict, sources: dict) -> list[str]:
    errors = []
    claims = unique(objects(data.get("claims"), "claims"), "claim_id")
    results = unique(objects(replication.get("critical_results"), "replication results"), "result_id")
    source_ids = unique(objects(sources.get("sources"), "sources", empty=True), "source_id")
    external_critical = unique(objects(sources.get("critical_claims", []), "critical source claims", empty=True), "claim_id")
    used_results = set()
    for claim_id, claim in claims.items():
        ids = claim.get("evidence_ids", [])
        if not isinstance(ids, list) or any(i not in results for i in ids):
            errors.append(f"{claim_id}: dangling evidence IDs")
        if not ids and not claim.get("source_ids"):
            errors.append(f"{claim_id}: no computation evidence or external source")
        used_results.update(ids)
        if not claim.get("statement") or not claim.get("section_id"):
            errors.append(f"{claim_id}: statement and section_id required")
        if claim.get("external") is True and not claim.get("source_ids"):
            errors.append(f"{claim_id}: external claim has no source")
        if claim.get("external") is True and claim.get("critical", True):
            registered = external_critical.get(claim_id, {})
            if not registered or set(registered.get("source_ids", [])) != set(claim.get("source_ids", [])):
                errors.append(f"{claim_id}: critical external claim bypasses source cross-validation")
        for source_id in claim.get("source_ids", []):
            if source_id not in source_ids or claim_id not in source_ids[source_id].get("claim_ids", []):
                errors.append(f"{claim_id}: dangling source or reverse link")
        kind = claim.get("claim_type", "numeric")
        if kind not in {"numeric", "qualitative"}:
            errors.append(f"{claim_id}: unknown claim type")
        if kind == "qualitative" and not claim.get("qualitative_rationale"):
            errors.append(f"{claim_id}: qualitative claim needs a rationale, not invented numeric evidence")
        for ref in objects(claim.get("numeric_evidence", []), "numeric evidence", empty=kind == "qualitative"):
            verified_refs = {(p.get("run_id"), p.get("metric")) for i in ids for p in results.get(i, {}).get("replication_paths", [])}
            if (ref.get("run_id"), ref.get("metric")) not in verified_refs:
                errors.append(f"{claim_id}: numeric evidence is not part of its linked independent replication")
            value = metric(root, runs, ref)
            decimals = ref.get("decimals")
            if not finite(value) or type(decimals) is not int or not 0 <= decimals <= 12:
                errors.append(f"{claim_id}: scalar numeric evidence with declared precision required")
            elif ref.get("display") != f"{value:.{decimals}f}":
                errors.append(f"{claim_id}: displayed number differs from computed evidence")
    if used_results != set(results):
        errors.append("critical results and paper claims lack bidirectional coverage")
    return errors


def evidence_files(root: Path) -> dict[str, str]:
    names = [
        "pro_config.json", "input_manifest.json", "instruction_manifest.json", "instruction_audit.json",
        "problem_consensus.json", "source_ledger.json", "candidate_routes.json", "tournament_report.json",
        "experiment_manifest.json", "replication_report.json", "robustness_report.json", "ablation_report.json",
        "claim_evidence_map.json", "figure_index.json", "table_index.json",
    ]
    paths = [root / n for n in names if (root / n).is_file()]
    for directory in ("code", "experiments", "figures", "tables", "research", "data_cleaned", "analysis/independent"):
        paths += [p for p in (root / directory).rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    return {p.relative_to(root).as_posix(): sha256_file(safe_path(root, p.relative_to(root).as_posix())) for p in sorted(paths)}


def check_freeze(root: Path, data: dict) -> list[str]:
    errors = check_hashes(root, data.get("file_hashes"))
    if data.get("file_hashes") != evidence_files(root):
        errors.append("frozen inventory changed: an evidence file was added, removed or modified")
    claims = read_json(root / "claim_evidence_map.json").get("claims")
    reverse = {}
    for claim in claims:
        for key in [*claim.get("evidence_ids", []), *claim.get("source_ids", [])]:
            reverse.setdefault(key, []).append(claim["claim_id"])
    reverse = {k: sorted(set(v)) for k, v in reverse.items()}
    if data.get("claims") != claims or data.get("reverse_index") != reverse:
        errors.append("frozen claim trace differs from evidence map")
    ledger = read_json(root / "checkpoint_ledger.json")
    if data.get("checkpoint_3_approval_hash") != ledger.get("checkpoints", {}).get("3", {}).get("approval_hash"):
        errors.append("freeze does not match checkpoint 3")
    content = {key: data.get(key) for key in ("checkpoint_3_approval_hash", "file_hashes", "claims", "reverse_index")}
    if data.get("snapshot_sha256") != canonical_json_hash(content):
        errors.append("freeze snapshot digest is invalid")
    return errors


def review_inputs(root: Path) -> dict[str, str]:
    return {name: sha256_file(root / name) for name in ("final_paper_source.md", "evidence_freeze.json", "paper_plan.json")}


def check_review(root: Path, data: dict) -> list[str]:
    errors = []
    rounds = objects(data.get("rounds"), "review rounds")
    expected = review_inputs(root)
    current = rounds[-1]
    if data.get("input_hashes") != expected or current.get("input_hashes") != expected:
        errors.append("review board is stale for the current manuscript, plan or evidence")
    reviews = objects(current.get("reviews"), "reviews")
    by_role = unique(reviews, "role")
    if set(by_role) != REVIEW_ROLES:
        errors.append("review board requires exactly five roles")
    session_ids = set()
    for role, review in by_role.items():
        path = safe_path(root, review.get("report_path", ""))
        errors.extend(check_hashes(root, {review["report_path"]: review.get("report_sha256")}))
        if not path.is_file():
            continue
        errors.extend(validate_envelope(path, {"PASS"}))
        detail = read_json(path)
        if detail.get("role") != role or detail.get("input_hashes") != expected:
            errors.append(f"{role}: reviewer did not inspect the current artifacts")
        execution = detail.get("execution", {})
        session_id = execution.get("context_id")
        if (detail.get("isolated_context") is not True or not session_id or session_id in session_ids
                or execution.get("mode") not in {"subagent", "fresh-session"}
                or not execution.get("model") or not execution.get("record_path")):
            errors.append(f"{role}: missing distinct isolated execution record")
        session_ids.add(session_id)
        if execution.get("record_path"):
            errors.extend(check_hashes(root, {execution["record_path"]: execution.get("record_sha256")}))
        if not detail.get("checks_performed") or not detail.get("assessment"):
            errors.append(f"{role}: empty review assessment")
        for finding in objects(detail.get("findings", []), "findings", empty=True):
            if finding.get("severity") not in {"CRITICAL", "MAJOR", "MINOR", "NOTE"} or not all(finding.get(k) for k in ("finding_id", "evidence", "disposition")):
                errors.append(f"{role}: malformed finding")
            if finding.get("severity") in {"CRITICAL", "MAJOR"}:
                if finding.get("disposition") != "RESOLVED" or not finding.get("resolution_evidence"):
                    errors.append(f"{role}: unresolved Critical/Major finding")
    return errors
