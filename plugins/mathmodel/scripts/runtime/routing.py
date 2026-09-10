"""Small task handoffs; Pro status alone decides gate progress."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROUTES = {
    "P0": ("pro-workflow-orchestrator", ["pro_config.json", "input_manifest.json", "instruction_audit.json"]),
    "P1": ("problem-doc-model-selector", ["problem_consensus.json", "checkpoint_ledger.json"]),
    "P2": ("pro-model-tournament", ["source_ledger.json", "candidate_routes.json", "tournament_report.json"]),
    "P3": ("model-code-and-result-generator", ["code/", "experiment_manifest.json"]),
    "P4": ("model-code-and-result-generator", ["replication_report.json"]),
    "P5": ("quality-assurance-auditor", ["replication_report.json", "robustness_report.json", "ablation_report.json"]),
    "P6": ("pro-workflow-orchestrator", ["claim_evidence_map.json", "evidence_freeze.json"]),
    "P7": ("paper-formal-writer", ["paper_plan.json", "final_paper_source.md", "paper_audit.json"]),
    "P8": ("pro-review-board", ["review_board_report.json"]),
    "P9": ("paper-formal-writer", ["final_paper.docx", "final_paper.pdf", "final_format_report.json", "pro_gate_report.json"]),
}


def make_handoff(packet: dict, plugin_root: Path) -> dict:
    workflow = packet["workflow"]
    phase = workflow.get("next_step", "P0")
    fallback, outputs = ROUTES.get(phase, ("pro-workflow-orchestrator", []))
    skill = workflow.get("recommended_skill") or fallback
    if not (plugin_root / "skills" / skill / "SKILL.md").is_file():
        skill = "pro-workflow-orchestrator"
    refs = sorted({(f["source"]["path"], f["source"].get("sha256", "")) for f in packet.get("facts", [])})
    revision = hashlib.sha256(json.dumps({"project": packet["project"]["id"], "phase": phase,
        "guard_revision": workflow.get("revision"), "refs": refs}, sort_keys=True).encode()).hexdigest()
    question = packet.get("focus", {}).get("question_id")
    return {"task_id": hashlib.sha256(f"{revision}:{question}:{skill}".encode()).hexdigest()[:24],
            "question_ids": [question] if question else [], "skill_id": skill,
            "skill_path": str(plugin_root / "skills" / skill / "SKILL.md"), "input_revision": revision,
            "expected_outputs": ["paper_output_pro/" + p for p in outputs],
            "acceptance_checks": ["Read live Pro status; require fresh approvals and artifact hashes.",
                                  "Process success or role completion does not grant stage PASS."],
            "next_on_failure": "Return changed inputs and concrete failures to pro-workflow-orchestrator; retain prior runs.",
            "action": workflow.get("next_action", ""), "blocked_by": workflow.get("blockers", [])[:3]}
