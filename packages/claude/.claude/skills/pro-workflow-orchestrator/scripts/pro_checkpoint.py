from __future__ import annotations

import argparse
from pathlib import Path

from pro_contracts import (
    approval_is_fresh,
    canonical_json_hash,
    checkpoint_hashes,
    contract,
    output_root,
    read_json,
    sha256_file,
    utc_now,
    validate_envelope,
    write_json,
)


def load_ledger(root: Path) -> dict:
    path = root / "checkpoint_ledger.json"
    if not path.is_file():
        raise FileNotFoundError("Run pro_preflight.py before using checkpoints")
    ledger = read_json(path)
    if not isinstance(ledger.get("checkpoints"), dict):
        raise ValueError("checkpoint_ledger.json has no checkpoints object")
    return ledger


def invalidate_stale(root: Path, ledger: dict) -> list[str]:
    invalidated: list[str] = []
    stale_seen = False
    for number in ("1", "2", "3"):
        entry = ledger["checkpoints"][number]
        stale_seen = stale_seen or (entry.get("status") == "APPROVED" and not approval_is_fresh(root, entry))
        if stale_seen and entry.get("status") != "PENDING":
            entry.update({
                "status": "PENDING",
                "decision": "invalidated because approved evidence changed",
                "decided_at_utc": utc_now(),
                "artifact_hashes": {},
                "approval_hash": None,
            })
            invalidated.append(number)
    if invalidated:
        ledger["status"] = "PENDING"
        ledger["created_at_utc"] = utc_now()
    return invalidated


def validate_checkpoint_artifacts(root: Path, number: str) -> list[str]:
    errors: list[str] = []
    from pro_contracts import CHECKPOINT_ARTIFACTS

    for relative in CHECKPOINT_ARTIFACTS[number]:
        errors.extend(validate_envelope(root / relative, {"PASS"}))
    if errors:
        return errors
    if number == "1":
        consensus = read_json(root / "problem_consensus.json")
        analyses = consensus.get("independent_analyses")
        if not isinstance(analyses, list) or len(analyses) < 3:
            errors.append("checkpoint 1 requires at least three independent analyses")
        else:
            role_ids = set()
            for item in analyses:
                role_ids.add(item.get("role_id"))
                path = root / Path(item.get("path", ""))
                if not path.is_file() or item.get("sha256") != sha256_file(path):
                    errors.append(f"independent analysis missing or stale: {item.get('path')}")
            if len(role_ids) < 3 or None in role_ids:
                errors.append("checkpoint 1 requires three distinct analysis roles")
        for field in ("consensus", "disagreements", "assumptions", "subproblems", "attachment_roles"):
            if not consensus.get(field):
                errors.append(f"problem_consensus.json requires {field}")
        manifest = read_json(root / "input_manifest.json")
        manifest_roles = {item.get("path"): item.get("role") for item in manifest.get("files", [])}
        consensus_roles = {item.get("path"): item.get("role") for item in consensus.get("attachment_roles", [])}
        if manifest_roles != consensus_roles:
            errors.append("problem consensus attachment roles differ from the input manifest")
    elif number == "2":
        from pro_gate import check_sources, check_tournament

        errors.extend(check_sources(read_json(root / "source_ledger.json")))
        errors.extend(check_tournament(read_json(root / "candidate_routes.json"), read_json(root / "tournament_report.json")))
    elif number == "3":
        from pro_gate import check_ablation, check_experiments, check_replication, check_robustness

        errors.extend(check_experiments(root, read_json(root / "experiment_manifest.json")))
        errors.extend(check_replication(read_json(root / "replication_report.json")))
        errors.extend(check_robustness(read_json(root / "robustness_report.json")))
        errors.extend(check_ablation(read_json(root / "ablation_report.json")))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Approve, reject, or validate mandatory Pro checkpoints.")
    parser.add_argument("action", choices=("approve", "reject", "validate", "status"))
    parser.add_argument("--checkpoint", choices=("1", "2", "3"))
    parser.add_argument("--decision", default="")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    root = output_root(args.project_root.resolve(), args.output_root)
    ledger_path = root / "checkpoint_ledger.json"
    ledger = load_ledger(root)
    invalidated = invalidate_stale(root, ledger)

    if args.action in {"approve", "reject"} and not args.checkpoint:
        parser.error("--checkpoint is required for approve/reject")
    if args.action == "approve":
        number = args.checkpoint
        assert number is not None
        for prior in range(1, int(number)):
            entry = ledger["checkpoints"][str(prior)]
            if entry.get("status") != "APPROVED" or not approval_is_fresh(root, entry):
                raise SystemExit(f"[BLOCKED] Checkpoint {prior} must be freshly approved before checkpoint {number}")
        validation_errors = validate_checkpoint_artifacts(root, number)
        if validation_errors:
            for error in validation_errors:
                print(f"[BLOCKED] {error}")
            return 1
        hashes = checkpoint_hashes(root, number)
        ledger["checkpoints"][number] = {
            "status": "APPROVED",
            "decision": args.decision or "approved by user",
            "decided_at_utc": utc_now(),
            "artifact_hashes": hashes,
            "approval_hash": canonical_json_hash(hashes),
        }
        for later in range(int(number) + 1, 4):
            ledger["checkpoints"][str(later)] = {
                "status": "PENDING",
                "decision": "invalidated by upstream checkpoint decision",
                "decided_at_utc": utc_now(),
                "artifact_hashes": {},
                "approval_hash": None,
            }
    elif args.action == "reject":
        number = args.checkpoint
        assert number is not None
        for current in range(int(number), 4):
            ledger["checkpoints"][str(current)] = {
                "status": "REJECTED" if current == int(number) else "PENDING",
                "decision": args.decision or ("rejected by user" if current == int(number) else "invalidated by upstream rejection"),
                "decided_at_utc": utc_now(),
                "artifact_hashes": {},
                "approval_hash": None,
            }

    ledger["created_at_utc"] = utc_now()
    ledger["status"] = "APPROVED" if all(item.get("status") == "APPROVED" for item in ledger["checkpoints"].values()) else "PENDING"
    ledger["input_hashes"] = {"pro_config.json": sha256_file(root / "pro_config.json")} if (root / "pro_config.json").is_file() else {}
    write_json(ledger_path, ledger)

    if invalidated:
        print(f"[INVALIDATED] stale checkpoints: {', '.join(invalidated)}")
    for number in ("1", "2", "3"):
        print(f"checkpoint {number}: {ledger['checkpoints'][number]['status']}")
    return 0 if args.action in {"approve", "reject", "status"} or not invalidated else 1


if __name__ == "__main__":
    raise SystemExit(main())
