from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

from pro_checkpoint import require_checkpoints
from pro_contracts import check_hashes, contract, output_root, read_json, sha256_file, validate_envelope, write_json
from pro_validation import (
    check_sources, check_tournament, check_replication, check_robustness,
    check_ablation, check_freeze, check_review, receipts,
)

CONTRACTS = (
    "pro_config.json", "input_manifest.json", "instruction_manifest.json", "instruction_audit.json",
    "checkpoint_ledger.json", "problem_consensus.json", "source_ledger.json", "candidate_routes.json",
    "tournament_report.json", "experiment_manifest.json", "replication_report.json", "robustness_report.json",
    "ablation_report.json", "claim_evidence_map.json", "evidence_freeze.json", "paper_plan.json",
    "review_board_report.json", "render_manifest.json", "visual_review.json", "final_format_report.json",
)


def check_experiments(root: Path, data: dict) -> list[str]:
    return receipts(root, data)[1]


def check_documents(root: Path, report: dict) -> list[str]:
    from pro_format_check import inspect_documents
    errors, _ = inspect_documents(root)
    expected = {n: sha256_file(root / n) for n in (
        "final_paper_source.md", "final_paper.docx", "final_paper.pdf",
        "paper_plan.json", "render_manifest.json", "visual_review.json",
        "pro_config.json", "problem_consensus.json",
    )}
    if report.get("input_hashes") != expected or report.get("status") != "PASS":
        errors.append("final format report is stale or not PASS")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Independently revalidate every Pro delivery invariant.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    project = args.project_root.resolve()
    root = output_root(project, args.output_root)
    errors = []
    for name in CONTRACTS:
        errors += validate_envelope(root / name, {"APPROVED"} if name == "checkpoint_ledger.json" else {"PASS"})
    checks = {}
    validators = {
        "checkpoints_and_evidence": lambda: require_checkpoints(project, root, 3),
        "freeze": lambda: check_freeze(root, read_json(root / "evidence_freeze.json")),
        "review": lambda: check_review(root, read_json(root / "review_board_report.json")),
        "delivery": lambda: check_documents(root, read_json(root / "final_format_report.json")),
    }
    for name, validator in validators.items():
        try:
            found = validator()
        except (ValueError, OSError, KeyError, TypeError, AttributeError, zipfile.BadZipFile) as exc:
            found = [f"{name}: invalid or missing artifact: {exc}"]
        checks[name] = "BLOCKED" if found else "PASS"
        errors += found
    try:
        mode = read_json(root / "pro_config.json").get("paper_delivery", {}).get("mode", "unknown")
    except (ValueError, AttributeError):
        mode = "unknown"
    if not isinstance(mode, str):
        mode = "unknown"
    scope = {"competition": "COMPETITION_REPORT_CHECKED", "short-report": "SHORT_REPORT_ONLY",
             "smoke-test": "ENGINEERING_SMOKE_ONLY"}.get(mode, "UNKNOWN")
    write_json(root / "pro_gate_report.json", contract(
        producer_role="pro-final-gate", status="BLOCKED" if errors else "PASS",
        input_hashes={n: sha256_file(root / n) for n in CONTRACTS if (root / n).is_file()},
        errors=sorted(set(errors)), checks=checks, delivery_mode=mode,
        acceptance_scope=scope if not errors else "NOT_ACCEPTED",
    ))
    for error in sorted(set(errors)):
        print(f"[BLOCKED] {error}")
    print(f"[{'BLOCKED' if errors else 'PASS'}] Pro final gate ({scope}; not a prize or model qualification)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
