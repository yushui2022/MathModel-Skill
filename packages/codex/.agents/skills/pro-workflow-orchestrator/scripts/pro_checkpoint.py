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
    check_original_inputs,
    safe_path,
)


def load_ledger(root: Path) -> dict:
    path = root / "checkpoint_ledger.json"
    if not path.is_file():
        raise FileNotFoundError("Run pro_preflight.py before using checkpoints")
    ledger = read_json(path)
    if not isinstance(ledger.get("checkpoints"), dict):
        raise ValueError("checkpoint_ledger.json has no checkpoints object")
    return ledger


def instruction_source_path(project_root: Path, item: dict) -> Path | None:
    scope = item.get("scope")
    if scope == "project":
        path = Path(str(item.get("path", "")))
        if path.is_absolute() or ".." in path.parts:
            return None
        candidate = (project_root / path).resolve()
        return candidate if candidate.is_relative_to(project_root.resolve()) else None
    if scope == "skill":
        skill_name = str(item.get("skill_name", ""))
        if not skill_name or Path(skill_name).name != skill_name:
            return None
        skill_root = Path(__file__).resolve().parents[2]
        candidate = (skill_root / skill_name / "SKILL.md").resolve()
        return candidate if candidate.is_relative_to(skill_root.resolve()) else None
    return None


def validate_instruction_audit(project_root: Path, root: Path) -> list[str]:
    errors: list[str] = []
    manifest_path = root / "instruction_manifest.json"
    audit_path = root / "instruction_audit.json"
    if not manifest_path.is_file() or not audit_path.is_file():
        return ["checkpoint 1 requires instruction_manifest.json and instruction_audit.json"]
    manifest = read_json(manifest_path)
    audit = read_json(audit_path)
    if audit.get("instruction_manifest_sha256") != sha256_file(manifest_path):
        errors.append("instruction audit does not match the current instruction manifest")
    files = manifest.get("files")
    reviewed = audit.get("reviewed_files")
    if not isinstance(files, list) or not isinstance(reviewed, list):
        return errors + ["instruction manifest files and audit reviewed_files must be arrays"]
    expected = {item.get("locator"): item.get("sha256") for item in files}
    actual = {item.get("locator"): item.get("sha256") for item in reviewed if isinstance(item, dict)}
    if expected != actual or len(reviewed) != len(expected):
        errors.append("instruction audit must review every current instruction source and hash")
    for item in files:
        source = instruction_source_path(project_root, item)
        if source is None or not source.is_file() or item.get("sha256") != sha256_file(source):
            errors.append(f"instruction source missing or stale: {item.get('locator')}")
    current_locators = {
        f"project://{name}"
        for name in ("AGENTS.md", "CLAUDE.md")
        if (project_root / name).is_file()
    }
    skill_root = Path(__file__).resolve().parents[2]
    current_locators.update(
        f"skill://{path.parent.name}/SKILL.md"
        for path in skill_root.glob("*/SKILL.md")
    )
    if set(expected) != current_locators:
        errors.append("instruction sources were added or removed after P0")
    unresolved = audit.get("unresolved_conflicts")
    if not isinstance(unresolved, list) or unresolved:
        errors.append("instruction audit has unresolved conflicts")
    required_contract = manifest.get("required_execution_contract")
    if audit.get("active_execution_contract") != required_contract:
        errors.append("instruction audit changed the required Pro execution contract")
    return errors


def instruction_sources_are_fresh(project_root: Path, root: Path) -> bool:
    try:
        return not validate_instruction_audit(project_root, root)
    except (OSError, ValueError):
        return False


def invalidate_stale(project_root: Path, root: Path, ledger: dict) -> list[str]:
    invalidated: list[str] = []
    stale_seen = False
    for number in ("1", "2", "3"):
        entry = ledger["checkpoints"][number]
        approval_stale = entry.get("status") == "APPROVED" and not approval_is_fresh(root, entry)
        if entry.get("status") == "APPROVED":
            try:
                approval_stale = approval_stale or checkpoint_hashes(root, number) != entry.get("artifact_hashes")
            except (ValueError, OSError, KeyError, TypeError):
                approval_stale = True
        instructions_stale = number == "1" and entry.get("status") == "APPROVED" and not instruction_sources_are_fresh(project_root, root)
        inputs_stale = number == "1" and bool(check_original_inputs(project_root, root))
        stale_seen = stale_seen or approval_stale or instructions_stale or inputs_stale
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


def validate_checkpoint_artifacts(project_root: Path, root: Path, number: str) -> list[str]:
    errors: list[str] = []
    from pro_contracts import CHECKPOINT_ARTIFACTS

    for relative in CHECKPOINT_ARTIFACTS[number]:
        errors.extend(validate_envelope(root / relative, {"PASS"}))
    if errors:
        return errors
    if number == "1":
        errors.extend(check_original_inputs(project_root, root))
        errors.extend(validate_instruction_audit(project_root, root))
        consensus = read_json(root / "problem_consensus.json")
        analyses = consensus.get("independent_analyses")
        if not isinstance(analyses, list) or len(analyses) < 3:
            errors.append("checkpoint 1 requires at least three independent analyses")
        else:
            role_ids = set()
            for item in analyses:
                role_ids.add(item.get("role_id"))
                path = safe_path(root, item.get("path", ""))
                if not path.is_file() or item.get("sha256") != sha256_file(path):
                    errors.append(f"independent analysis missing or stale: {item.get('path')}")
                else:
                    analysis = read_json(path)
                    errors.extend(validate_envelope(path, {"PASS"}))
                    if analysis.get("isolated_context") is not True or not analysis.get("summary"):
                        errors.append("independent analysis is empty or not isolated")
            if len(role_ids) < 3 or None in role_ids:
                errors.append("checkpoint 1 requires three distinct analysis roles")
        for field in ("consensus", "assumptions", "subproblems", "attachment_roles"):
            if not consensus.get(field):
                errors.append(f"problem_consensus.json requires {field}")
        if not isinstance(consensus.get("disagreements"), list):
            errors.append("disagreements must be an array; an empty array is allowed")
        manifest = read_json(root / "input_manifest.json")
        manifest_roles = {item.get("path"): item.get("role") for item in manifest.get("files", [])}
        consensus_roles = {item.get("path"): item.get("role") for item in consensus.get("attachment_roles", [])}
        if manifest_roles != consensus_roles:
            errors.append("problem consensus attachment roles differ from the input manifest")
    elif number == "2":
        from pro_validation import check_sources, check_tournament

        errors.extend(check_sources(root, read_json(root / "source_ledger.json")))
        errors.extend(check_tournament(read_json(root / "candidate_routes.json"), read_json(root / "tournament_report.json"), read_json(root / "problem_consensus.json")))
    elif number == "3":
        from pro_validation import check_ablation, receipts, check_replication, check_robustness, check_claims

        runs, execution_errors = receipts(root, read_json(root / "experiment_manifest.json"))
        errors.extend(execution_errors)
        errors.extend(check_replication(root, read_json(root / "replication_report.json"), runs, read_json(root / "tournament_report.json")))
        errors.extend(check_robustness(root, read_json(root / "robustness_report.json"), runs))
        errors.extend(check_ablation(root, read_json(root / "ablation_report.json"), runs))
        errors.extend(check_claims(root, read_json(root / "claim_evidence_map.json"), runs, read_json(root / "replication_report.json"), read_json(root / "source_ledger.json")))
    return errors


def require_checkpoints(project_root: Path, root: Path, through: int) -> list[str]:
    errors = []
    try:
        ledger = load_ledger(root)
        if invalidate_stale(project_root, root, ledger):
            write_json(root / "checkpoint_ledger.json", ledger)
        for number in range(1, through + 1):
            entry = ledger["checkpoints"].get(str(number), {})
            if entry.get("status") != "APPROVED" or not approval_is_fresh(root, entry):
                errors.append(f"checkpoint {number} must be freshly approved")
            errors.extend(validate_checkpoint_artifacts(project_root, root, str(number)))
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        errors.append(f"invalid checkpoint artifact: {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Approve, reject, or validate mandatory Pro checkpoints.")
    parser.add_argument("action", choices=("approve", "reject", "validate", "status"))
    parser.add_argument("--checkpoint", choices=("1", "2", "3"))
    parser.add_argument("--decision", default="")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    root = output_root(project_root, args.output_root)
    ledger_path = root / "checkpoint_ledger.json"
    ledger = load_ledger(root)
    invalidated = invalidate_stale(project_root, root, ledger)
    if invalidated:
        write_json(ledger_path, ledger)

    if args.action in {"approve", "reject"} and not args.checkpoint:
        parser.error("--checkpoint is required for approve/reject")
    if args.action == "approve":
        number = args.checkpoint
        assert number is not None
        if not args.decision.strip():
            raise SystemExit("[BLOCKED] --decision must record the user's explicit checkpoint decision")
        for prior in range(1, int(number)):
            entry = ledger["checkpoints"][str(prior)]
            if entry.get("status") != "APPROVED" or not approval_is_fresh(root, entry):
                raise SystemExit(f"[BLOCKED] Checkpoint {prior} must be freshly approved before checkpoint {number}")
        try:
            validation_errors = validate_checkpoint_artifacts(project_root, root, number)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            validation_errors = [f"invalid checkpoint contract: {exc}"]
        if validation_errors:
            for error in validation_errors:
                print(f"[BLOCKED] {error}")
            return 1
        hashes = checkpoint_hashes(root, number)
        ledger["checkpoints"][number] = {
            "status": "APPROVED",
            "decision": args.decision,
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
    if args.action == "validate":
        through = int(args.checkpoint) if args.checkpoint else max(
            (int(n) for n, item in ledger["checkpoints"].items() if item.get("status") == "APPROVED"), default=1)
        validation_errors = require_checkpoints(project_root, root, through)
        for error in validation_errors:
            print(f"[BLOCKED] {error}")
        if not validation_errors:
            print(f"[VALIDATED THROUGH] checkpoint {through}; later pending states are not approvals")
        return int(bool(invalidated or validation_errors))
    return 0 if args.action in {"approve", "reject", "status"} or not invalidated else 1


if __name__ == "__main__":
    raise SystemExit(main())
