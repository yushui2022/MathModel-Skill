from __future__ import annotations

import argparse
import sys
from pathlib import Path

from authoring_contracts import (
    collect_requirements,
    contract,
    fresh_evidence_gate,
    merge_requirements,
    output_root,
    read_json,
    relative,
    safe_relative_path,
    sha256_file,
    slug,
    write_json,
)


def build_sections(outline: dict) -> list[dict]:
    result = [{
        "section_id": "abstract",
        "title": "摘要",
        "target_chars": int((outline.get("front_matter") or {}).get("abstract_target_words") or 700),
        "requirements": {"evidence": [], "figures": [], "tables": [], "formulas": []},
    }]
    for raw in outline.get("sections") or []:
        if not isinstance(raw, dict) or not raw.get("section_id"):
            continue
        section_id = str(raw["section_id"])
        result.append({
            "section_id": section_id,
            "title": str(raw.get("title") or section_id),
            "target_chars": int(raw.get("target_words") or 600),
            "requirements": collect_requirements(raw),
        })
    return result


def state_sections(project_root: Path, sections: list[dict]) -> dict[str, dict]:
    return {
        item["section_id"]: {
            "path": f"paper_output/drafts/sections/{slug(item['section_id'])}.md",
            "status": "PENDING",
            "attempts": 0,
            "same_issue_count": 0,
            "last_issue_signature": None,
            "last_attempt_sha256": None,
            "approved_sha256": None,
            "issues": [],
        }
        for item in sections
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare the Standard 2.2 adaptive authoring contracts.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--mode", choices=("auto", "global", "section"), default="auto")
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    out = output_root(project_root)
    outline_path = out / "plan" / "paper_outline.json"
    if not outline_path.is_file():
        print("[BLOCKED] missing paper_output/plan/paper_outline.json", file=sys.stderr)
        return 1
    gate, errors = fresh_evidence_gate(project_root)
    if errors:
        for error in errors:
            print(f"[BLOCKED] {error}", file=sys.stderr)
        return 1
    try:
        outline = read_json(outline_path)
    except ValueError as exc:
        print(f"[BLOCKED] {exc}", file=sys.stderr)
        return 1
    sections = build_sections(outline)
    ideal = int((outline.get("target_words") or {}).get("ideal") or sum(item["target_chars"] for item in sections))
    mode = args.mode
    reason = "explicit user or operator selection"
    if mode == "auto":
        mode = "global" if ideal <= 6000 else "section"
        reason = f"auto selected {mode} because ideal target is {ideal} effective characters"
    writing_plan_path = out / "plan" / "writing_plan.json"
    input_hashes = {
        relative(outline_path, project_root): sha256_file(outline_path),
        relative(out / "qa" / "evidence_gate_report.json", project_root): sha256_file(out / "qa" / "evidence_gate_report.json"),
    }
    for path_text, expected in (gate.get("input_hashes") or {}).items():
        path = safe_relative_path(project_root, path_text)
        if path.is_file():
            input_hashes[relative(path, project_root)] = expected
    plan = contract(
        producer_role="paper-formal-writer/prepare-authoring",
        status="PASS",
        input_hashes=input_hashes,
        requested_mode=args.mode,
        mode=mode,
        mode_reason=reason,
        target_chars=outline.get("target_words") or {"ideal": ideal},
        evidence_gate_sha256=sha256_file(out / "qa" / "evidence_gate_report.json"),
        evidence_marker="<!-- mathmodel-evidence: evidence-id-1, evidence-id-2 -->",
        global_constraints={
            "numbering_style": outline.get("numbering_style") or "1 / 1.1 / 1.1.1",
            "formal_source": "paper_output/final_paper_source.md",
            "require_global_revision": True,
            "forbid_placeholders": True,
            "forbid_internal_workflow_language": True,
        },
        sections=sections,
    )
    write_json(writing_plan_path, plan)
    for relative_dir in ("drafts/sections", "drafts/repairs", "drafts/legacy", "context", "qa"):
        (out / relative_dir).mkdir(parents=True, exist_ok=True)
    section_states = state_sections(project_root, sections)
    if mode == "global":
        global_section = {
            "section_id": "GLOBAL",
            "title": "完整论文草稿",
            "target_chars": ideal,
            "requirements": merge_requirements(sections),
        }
        section_states = {
            "GLOBAL": {
                "path": "paper_output/drafts/global_draft.md",
                "status": "PENDING",
                "attempts": 0,
                "same_issue_count": 0,
                "last_issue_signature": None,
                "last_attempt_sha256": None,
                "approved_sha256": None,
                "issues": [],
            }
        }
        plan["global_unit"] = global_section
        write_json(writing_plan_path, plan)
    state = contract(
        producer_role="paper-formal-writer/authoring-state",
        status="PLANNED",
        input_hashes={relative(writing_plan_path, project_root): sha256_file(writing_plan_path)},
        mode=mode,
        sections=section_states,
        assembled={"path": "paper_output/drafts/assembled_draft.md", "sha256": None, "status": "PENDING"},
        final={"path": "paper_output/final_paper_source.md", "sha256": None, "status": "PENDING"},
        blocking_reason=None,
    )
    write_json(out / "context" / "authoring_state.json", state)
    write_json(out / "qa" / "repair_queue.json", contract(
        producer_role="paper-formal-writer/repair-router",
        status="PASS",
        input_hashes={relative(writing_plan_path, project_root): sha256_file(writing_plan_path)},
        issues=[],
    ))
    print(f"[PASS] Standard authoring prepared in {mode} mode: {relative(writing_plan_path, project_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
