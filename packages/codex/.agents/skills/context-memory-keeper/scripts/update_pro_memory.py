from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def normalize_failure(value: str) -> str:
    value = re.sub(r"[A-Fa-f0-9]{32,64}", "<hash>", value.casefold())
    value = re.sub(r"\d+(?:\.\d+)?", "<number>", value)
    return re.sub(r"\s+", " ", value).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Update resumable MathModel Pro workflow memory.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--phase", required=True, choices=[f"P{i}" for i in range(10)])
    parser.add_argument("--next-action", required=True)
    parser.add_argument("--failure", default="")
    parser.add_argument("--blocker", default="")
    args = parser.parse_args()
    root = args.project_root.resolve() / "paper_output_pro"
    context_dir = root / "context"
    context_dir.mkdir(parents=True, exist_ok=True)
    memory_path = context_dir / "workflow_memory.json"
    previous = load(memory_path)
    failure_history = previous.get("failure_history", []) if isinstance(previous.get("failure_history"), list) else []
    if args.failure:
        signature = normalize_failure(args.failure)
        prior_count = failure_history[-1].get("consecutive_count", 0) if failure_history and failure_history[-1].get("signature") == signature else 0
        failure_history.append({"signature": signature, "message": args.failure, "at_utc": utc_now(), "consecutive_count": prior_count + 1})
    ledger = load(root / "checkpoint_ledger.json")
    tracked_names = (
        "pro_config.json", "input_manifest.json", "instruction_manifest.json", "instruction_audit.json",
        "problem_consensus.json", "source_ledger.json",
        "candidate_routes.json", "tournament_report.json", "experiment_manifest.json",
        "replication_report.json", "robustness_report.json", "ablation_report.json",
        "evidence_freeze.json", "review_board_report.json", "final_format_report.json", "pro_gate_report.json",
    )
    hashes = {name: sha256(root / name) for name in tracked_names if (root / name).is_file()}
    payload = {
        "schema_version": "3.0",
        "updated_at_utc": utc_now(),
        "current_phase": args.phase,
        "next_action": args.next_action,
        "checkpoint_statuses": {key: value.get("status") for key, value in ledger.get("checkpoints", {}).items()},
        "model_profile": load(root / "pro_config.json").get("model_profile", {}),
        "reasoning_profile": load(root / "pro_config.json").get("reasoning_profile", {}),
        "artifact_hashes": hashes,
        "failure_history": failure_history[-30:],
        "blocked": bool(args.blocker) or (bool(failure_history) and failure_history[-1].get("consecutive_count", 0) >= 3),
        "blocker": args.blocker or None,
    }
    memory_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# MathModel Pro workflow memory",
        "",
        f"- Phase: `{payload['current_phase']}`",
        f"- Next action: {payload['next_action']}",
        f"- Checkpoints: `{payload['checkpoint_statuses']}`",
        f"- Blocked: `{payload['blocked']}`",
        f"- Tracked artifacts: `{len(hashes)}`",
    ]
    (context_dir / "workflow_memory.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[PASS] Updated Pro memory at phase {args.phase}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
