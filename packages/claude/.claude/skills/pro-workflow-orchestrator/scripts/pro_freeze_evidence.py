from __future__ import annotations

import argparse
from pathlib import Path

from pro_contracts import approval_is_fresh, canonical_json_hash, contract, hash_paths, output_root, read_json, write_json


REQUIRED_REPORTS = (
    "experiment_manifest.json",
    "replication_report.json",
    "robustness_report.json",
    "ablation_report.json",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze Pro evidence after checkpoint 3 approval.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    root = output_root(project_root, args.output_root)
    errors: list[str] = []
    ledger = read_json(root / "checkpoint_ledger.json")
    checkpoints = ledger.get("checkpoints", {})
    for number in ("1", "2", "3"):
        checkpoint = checkpoints.get(number, {})
        if checkpoint.get("status") != "APPROVED" or not approval_is_fresh(root, checkpoint):
            errors.append(f"checkpoint {number} must be freshly approved")
    from pro_checkpoint import validate_instruction_audit

    errors.extend(validate_instruction_audit(project_root, root))
    for name in REQUIRED_REPORTS:
        path = root / name
        if not path.is_file():
            errors.append(f"missing {name}")
            continue
        if read_json(path).get("status") != "PASS":
            errors.append(f"{name} status is not PASS")

    claim_map_path = root / "claim_evidence_map.json"
    claims: list[dict] = []
    if not claim_map_path.is_file():
        errors.append("missing claim_evidence_map.json")
    else:
        claim_map = read_json(claim_map_path)
        claims = claim_map.get("claims", [])
        if not isinstance(claims, list) or not claims:
            errors.append("claim_evidence_map.json requires claims[]")
        for item in claims if isinstance(claims, list) else []:
            if not item.get("claim_id") or not item.get("evidence_ids"):
                errors.append("every claim needs claim_id and evidence_ids")
            if item.get("external") and not item.get("source_ids"):
                errors.append(f"external claim {item.get('claim_id')} needs source_ids")

    tracked: list[Path] = []
    for directory in ("code", "experiments", "figures", "tables"):
        base = root / directory
        if base.is_dir():
            tracked.extend(path for path in base.rglob("*") if path.is_file())
    for name in (
        "pro_config.json", "input_manifest.json", "instruction_manifest.json", "instruction_audit.json",
        "problem_consensus.json", "source_ledger.json",
        "candidate_routes.json", "tournament_report.json", *REQUIRED_REPORTS, "claim_evidence_map.json",
    ):
        path = root / name
        if path.is_file():
            tracked.append(path)
    if not tracked:
        errors.append("no evidence files were found")
    if errors:
        for error in errors:
            print(f"[BLOCKED] {error}")
        return 1

    file_hashes = hash_paths(tracked, root)
    reverse_index: dict[str, list[str]] = {}
    for item in claims:
        for evidence_id in item.get("evidence_ids", []):
            reverse_index.setdefault(evidence_id, []).append(item["claim_id"])
        for source_id in item.get("source_ids", []):
            reverse_index.setdefault(source_id, []).append(item["claim_id"])
    payload = contract(
        producer_role="p6-evidence-freezer",
        status="PASS",
        input_hashes=file_hashes,
        checkpoint_3_approval_hash=checkpoints["3"]["approval_hash"],
        file_hashes=file_hashes,
        claims=claims,
        reverse_index={key: sorted(set(value)) for key, value in sorted(reverse_index.items())},
        snapshot_sha256=canonical_json_hash({
            "checkpoint_3_approval_hash": checkpoints["3"]["approval_hash"],
            "file_hashes": file_hashes,
            "claims": claims,
            "reverse_index": reverse_index,
        }),
    )
    write_json(root / "evidence_freeze.json", payload)
    print(f"[PASS] Frozen {len(file_hashes)} Pro evidence files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
