from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path
from urllib.parse import urlparse

from pro_contracts import approval_is_fresh, contract, output_root, read_json, sha256_file, validate_envelope, write_json


CONTRACTS = (
    "pro_config.json",
    "input_manifest.json",
    "checkpoint_ledger.json",
    "problem_consensus.json",
    "source_ledger.json",
    "candidate_routes.json",
    "tournament_report.json",
    "experiment_manifest.json",
    "replication_report.json",
    "robustness_report.json",
    "ablation_report.json",
    "evidence_freeze.json",
    "review_board_report.json",
    "final_format_report.json",
)
REVIEW_ROLES = {
    "mathematical_correctness",
    "code_reproducibility",
    "source_provenance",
    "paper_expression",
    "adversarial_challenge",
}
TOURNAMENT_DIMENSIONS = {
    "task_fit", "data_feasibility", "validation_strength", "robustness",
    "interpretability", "innovation_value", "implementation_risk",
}


def check_sources(data: dict) -> list[str]:
    errors: list[str] = []
    sources = data.get("sources")
    if not isinstance(sources, list):
        return ["source_ledger.json requires sources[]"]
    by_id = {}
    for source in sources:
        if not isinstance(source, dict) or not source.get("source_id"):
            errors.append("source ledger entry missing source_id")
            continue
        by_id[source["source_id"]] = source
        parsed = urlparse(str(source.get("url", "")))
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            errors.append(f"{source['source_id']}: invalid public URL")
        for field in ("title", "publisher", "accessed_at_utc", "content_sha256", "purpose", "claim_ids"):
            if not source.get(field):
                errors.append(f"{source['source_id']}: missing {field}")
        if source.get("access_status") != "PUBLIC_OK" or source.get("authorization_required") is True:
            errors.append(f"{source['source_id']}: source is inaccessible or needs authorization")
    for claim in data.get("critical_claims", []):
        source_ids = claim.get("source_ids", [])
        resolved = [by_id[item] for item in source_ids if item in by_id]
        if len(resolved) < 1:
            errors.append(f"critical claim {claim.get('claim_id')} has no valid source")
        if claim.get("cross_validation_required", True):
            publishers = {item.get("publisher") for item in resolved}
            if len(resolved) < 2 or len(publishers) < 2:
                errors.append(f"critical claim {claim.get('claim_id')} lacks two independent publishers")
    return errors


def check_tournament(candidates: dict, report: dict) -> list[str]:
    errors: list[str] = []
    decisions = {item.get("subproblem_id"): item for item in report.get("decisions", []) if isinstance(item, dict)}
    subproblems = candidates.get("subproblems")
    if not isinstance(subproblems, list) or not subproblems:
        return ["candidate_routes.json requires subproblems[]"]
    for subproblem in subproblems:
        subproblem_id = subproblem.get("subproblem_id")
        routes = subproblem.get("routes", [])
        route_ids = [item.get("route_id") for item in routes if isinstance(item, dict)]
        if not 3 <= len(routes) <= 5:
            errors.append(f"{subproblem_id}: tournament requires 3-5 routes")
        if not any(item.get("is_interpretable_baseline") is True for item in routes if isinstance(item, dict)):
            errors.append(f"{subproblem_id}: tournament lacks an interpretable baseline")
        for route in routes:
            scores = route.get("scores") if isinstance(route, dict) else None
            route_id = route.get("route_id") if isinstance(route, dict) else "<invalid>"
            if not isinstance(scores, dict) or set(scores) != TOURNAMENT_DIMENSIONS:
                errors.append(f"{subproblem_id}/{route_id}: incomplete seven-dimension scores")
            elif any(not isinstance(value, (int, float)) or not 0 <= value <= 10 for value in scores.values()):
                errors.append(f"{subproblem_id}/{route_id}: score outside [0, 10]")
        decision = decisions.get(subproblem_id, {})
        selected = decision.get("selected_route_id")
        backup = decision.get("backup_route_id")
        if selected not in route_ids or backup not in route_ids or selected == backup:
            errors.append(f"{subproblem_id}: invalid selected/backup route")
        rejected = {item.get("route_id") for item in decision.get("rejected_routes", []) if item.get("reason")}
        if rejected != set(route_ids) - {selected, backup}:
            errors.append(f"{subproblem_id}: missing route rejection reasons")
    return errors


def check_experiments(root: Path, data: dict) -> list[str]:
    errors: list[str] = []
    runs = data.get("runs")
    if not isinstance(runs, list) or not runs:
        return ["experiment_manifest.json requires runs[]"]
    for run in runs:
        for field in ("run_id", "route_id", "command", "script_hashes", "input_hashes", "output_hashes", "exit_code"):
            if field not in run:
                errors.append(f"experiment run missing {field}")
        if run.get("status") == "FAILED" and not run.get("failure_reason"):
            errors.append(f"failed run {run.get('run_id')} has no failure_reason")
        for field in ("script_hashes", "input_hashes", "output_hashes"):
            hashes = run.get(field)
            if not isinstance(hashes, dict) or not hashes:
                errors.append(f"experiment run {run.get('run_id')} has empty {field}")
                continue
            for relative, expected in hashes.items():
                path = root / Path(relative)
                if not path.is_file() or sha256_file(path) != expected:
                    errors.append(f"experiment run {run.get('run_id')} has stale {field}: {relative}")
    return errors


def check_replication(data: dict) -> list[str]:
    errors: list[str] = []
    results = data.get("critical_results")
    if not isinstance(results, list) or not results:
        return ["replication_report.json requires critical_results[]"]
    for result in results:
        paths = result.get("replication_paths", [])
        if len(paths) < 2 or len({item.get("implementation_id") for item in paths if isinstance(item, dict)}) < 2:
            errors.append(f"{result.get('result_id')}: fewer than two independent replication paths")
        if result.get("agreement_status") != "PASS" or not result.get("comparison_rule"):
            errors.append(f"{result.get('result_id')}: replication agreement is incomplete")
    return errors


def check_robustness(data: dict) -> list[str]:
    errors: list[str] = []
    for field in ("baseline_comparisons", "sensitivity_tests", "constraint_stress_tests"):
        if not data.get(field):
            errors.append(f"robustness_report.json requires {field}")
    for item in data.get("stochastic_methods", []):
        seeds = item.get("seeds", [])
        if len(set(seeds)) < 10:
            errors.append(f"{item.get('method_id')}: randomized method requires at least 10 unique seeds")
        if not item.get("mean") and item.get("mean") != 0:
            errors.append(f"{item.get('method_id')}: missing mean")
        if "variance" not in item or not item.get("confidence_interval"):
            errors.append(f"{item.get('method_id')}: missing variance or confidence interval")
        if item.get("interval_stable") is not True and not item.get("expanded_run_record"):
            errors.append(f"{item.get('method_id')}: unstable interval was not expanded")
    return errors


def check_ablation(data: dict) -> list[str]:
    tests = data.get("ablations")
    if isinstance(tests, list) and tests:
        return [] if all(item.get("component") and item.get("effect") for item in tests) else ["ablation entry missing component/effect"]
    return [] if data.get("not_applicable_reason") else ["ablation_report.json needs ablations[] or not_applicable_reason"]


def check_freeze(root: Path, data: dict) -> list[str]:
    errors: list[str] = []
    hashes = data.get("file_hashes")
    if not isinstance(hashes, dict) or not hashes:
        return ["evidence_freeze.json requires file_hashes"]
    for relative, expected in hashes.items():
        path = root / Path(relative)
        if not path.is_file() or sha256_file(path) != expected:
            errors.append(f"frozen evidence changed: {relative}")
    if not data.get("claims") or not data.get("reverse_index"):
        errors.append("evidence freeze lacks bidirectional claim tracing")
    return errors


def check_review(data: dict) -> list[str]:
    errors: list[str] = []
    rounds = data.get("rounds")
    if not isinstance(rounds, list) or not rounds:
        return ["review_board_report.json requires rounds[]"]
    reviews = rounds[-1].get("reviews", [])
    if {item.get("role") for item in reviews} != REVIEW_ROLES:
        errors.append("final review round does not contain exactly five required roles")
    unresolved = [finding for review in reviews for finding in review.get("findings", []) if finding.get("severity") in {"CRITICAL", "MAJOR"} and finding.get("disposition") != "RESOLVED"]
    if unresolved:
        errors.append(f"final review round has {len(unresolved)} unresolved Critical/Major findings")
    return errors


def check_documents(root: Path, report: dict) -> list[str]:
    errors: list[str] = []
    source = root / "final_paper_source.md"
    docx = root / "final_paper.docx"
    pdf = root / "final_paper.pdf"
    for path in (source, docx, pdf):
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"missing or empty final artifact: {path.name}")
    if docx.is_file():
        try:
            with zipfile.ZipFile(docx) as archive:
                xml = archive.read("word/document.xml").decode("utf-8")
            if len(re.sub(r"<[^>]+>", "", xml).strip()) < 200:
                errors.append("DOCX has insufficient extractable document text")
        except (OSError, KeyError, zipfile.BadZipFile, UnicodeDecodeError) as exc:
            errors.append(f"DOCX is damaged: {exc}")
    if pdf.is_file():
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(pdf))
            text = "".join(page.extract_text() or "" for page in reader.pages)
            if not reader.pages or len(text.strip()) < 200:
                errors.append("PDF has no pages or insufficient extractable text")
        except Exception as exc:  # pypdf surfaces several parser exception types
            errors.append(f"PDF is damaged or unreadable: {exc}")
    for field in ("formula_check", "figure_check", "pagination_check", "citation_check", "docx_pdf_consistency"):
        if report.get(field, {}).get("status") != "PASS":
            errors.append(f"final_format_report.json {field} is not PASS")
    expected = {
        "final_paper_source.md": source,
        "final_paper.docx": docx,
        "final_paper.pdf": pdf,
    }
    recorded = report.get("input_hashes", {})
    for name, path in expected.items():
        if path.is_file() and recorded.get(name) != sha256_file(path):
            errors.append(f"final format report is stale for {name}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the final MathModel Skill Pro gate.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    root = output_root(args.project_root.resolve(), args.output_root)
    errors: list[str] = []
    for name in CONTRACTS:
        errors.extend(validate_envelope(root / name, {"PASS", "APPROVED"}))
    data: dict[str, dict] = {}
    for name in CONTRACTS:
        if (root / name).is_file():
            try:
                data[name] = read_json(root / name)
            except ValueError as exc:
                errors.append(str(exc))

    ledger = data.get("checkpoint_ledger.json", {})
    for number in ("1", "2", "3"):
        entry = ledger.get("checkpoints", {}).get(number, {})
        if entry.get("status") != "APPROVED" or not approval_is_fresh(root, entry):
            errors.append(f"checkpoint {number} is not freshly approved")
    if "source_ledger.json" in data:
        errors.extend(check_sources(data["source_ledger.json"]))
    if "candidate_routes.json" in data and "tournament_report.json" in data:
        errors.extend(check_tournament(data["candidate_routes.json"], data["tournament_report.json"]))
    if "experiment_manifest.json" in data:
        errors.extend(check_experiments(root, data["experiment_manifest.json"]))
    if "replication_report.json" in data:
        errors.extend(check_replication(data["replication_report.json"]))
    if "robustness_report.json" in data:
        errors.extend(check_robustness(data["robustness_report.json"]))
    if "ablation_report.json" in data:
        errors.extend(check_ablation(data["ablation_report.json"]))
    if "evidence_freeze.json" in data:
        errors.extend(check_freeze(root, data["evidence_freeze.json"]))
    if "review_board_report.json" in data:
        errors.extend(check_review(data["review_board_report.json"]))
    if "final_format_report.json" in data:
        errors.extend(check_documents(root, data["final_format_report.json"]))

    report = contract(
        producer_role="p9-pro-final-gate",
        status="PASS" if not errors else "BLOCKED",
        input_hashes={name: sha256_file(root / name) for name in CONTRACTS if (root / name).is_file()},
        errors=sorted(set(errors)),
        checks={
            "checkpoints": "PASS" if not any("checkpoint" in item for item in errors) else "BLOCKED",
            "research": "PASS" if not any("source" in item or "claim" in item for item in errors) else "BLOCKED",
            "evidence": "PASS" if not any(token in item for item in errors for token in ("experiment", "replication", "robustness", "ablation", "frozen")) else "BLOCKED",
            "review": "PASS" if not any("review" in item or "Critical/Major" in item for item in errors) else "BLOCKED",
            "delivery": "PASS" if not any(token in item for item in errors for token in ("DOCX", "PDF", "final artifact", "format report")) else "BLOCKED",
        },
    )
    write_json(root / "pro_gate_report.json", report)
    for error in report["errors"]:
        print(f"[BLOCKED] {error}")
    print(f"[{'PASS' if not errors else 'BLOCKED'}] Pro final gate")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
