from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path
from typing import Any
from difflib import SequenceMatcher

from authoring_contracts import (
    INTERNAL_LANGUAGE,
    PLACEHOLDERS,
    all_required_ids,
    approved_draft_errors,
    contract,
    duplicate_paragraphs,
    effective_chars,
    evidence_ids,
    flatten_numeric_requirements,
    formula_errors,
    fresh_evidence_gate,
    merge_requirements,
    numeric_variants,
    output_root,
    read_json,
    relative,
    safe_relative_path,
    section_issue_signature,
    sha256_file,
    slug,
    utc_now,
    validate_hashes,
    write_audit,
    write_json,
)


def issue(category: str, message: str, *, section_id: str, expected: list[str] | None = None) -> dict[str, Any]:
    return {
        "issue_id": f"{slug(section_id)}-{slug(category)}",
        "section_id": section_id,
        "category": category,
        "severity": "BLOCKING",
        "message": message,
        "expected_evidence": expected or [],
    }


def validate_common(text: str, section: dict[str, Any], section_id: str, *, require_marker: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    required = all_required_ids(section)
    declared = evidence_ids(text)
    length = effective_chars(text)
    target = max(1, int(section.get("target_chars") or 1))
    if length < math.ceil(target * 0.60):
        issues.append(issue("insufficient-length", f"effective characters {length} are below 60% of target {target}", section_id=section_id))
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    if not first_line.startswith("#"):
        issues.append(issue("missing-heading", "draft must start with a Markdown heading", section_id=section_id))
    lowered = text.casefold()
    for marker in PLACEHOLDERS:
        if marker.casefold() in lowered:
            issues.append(issue("placeholder", f"draft contains placeholder text: {marker}", section_id=section_id))
    for marker in INTERNAL_LANGUAGE:
        if marker.casefold() in lowered:
            issues.append(issue("internal-language", f"draft exposes workflow language: {marker}", section_id=section_id))
    if require_marker:
        missing = sorted(required - declared)
        if missing:
            issues.append(issue("evidence-coverage", f"draft does not declare required evidence IDs: {missing}", section_id=section_id, expected=missing))
    for evidence_id, value, labels in flatten_numeric_requirements(section):
        variants = numeric_variants(value)
        normalized_text = text.replace(",", "")
        matches = [
            match
            for candidate in variants
            if candidate
            for match in re.finditer(rf"(?<![\d.]){re.escape(candidate)}(?![\d.])", normalized_text)
        ]
        contextual_match = any(
            not labels
            or any(label.casefold() in normalized_text[max(0, match.start() - 100):match.end() + 100].casefold() for label in labels)
            for match in matches
        )
        if variants and not contextual_match:
            issues.append(issue("numeric-evidence", f"draft does not contain the recorded value for {evidence_id}", section_id=section_id, expected=[evidence_id]))
    requirements = section.get("requirements") or {}
    for kind in ("figures", "tables"):
        for item in requirements.get(kind, []):
            if not isinstance(item, dict):
                continue
            path = str(item.get("path") or item.get("expected_path") or "").replace("\\", "/")
            title = str(item.get("title") or "")
            identifier = str(item.get("evidence_id") or "")
            raw_id = str(item.get("figure_id") or item.get("table_id") or "")
            candidates = [value for value in (path, Path(path).name if path else "", title, raw_id) if value]
            if candidates and not any(value in text for value in candidates):
                issues.append(issue(f"{kind[:-1]}-reference", f"draft does not reference {identifier or path}", section_id=section_id, expected=[identifier]))
    for message in formula_errors(text):
        issues.append(issue("formula", message, section_id=section_id))
    duplicates = duplicate_paragraphs(text)
    if duplicates:
        issues.append(issue("duplicate-paragraph", f"draft contains {len(duplicates)} normalized duplicate paragraphs", section_id=section_id))
    return issues, {
        "effective_characters": length,
        "target_characters": target,
        "required_evidence_ids": sorted(required),
        "declared_evidence_ids": sorted(declared),
        "duplicate_paragraphs": len(duplicates),
    }


def plan_section(plan: dict[str, Any], section_id: str) -> dict[str, Any] | None:
    if section_id == "GLOBAL":
        return plan.get("global_unit")
    return next((item for item in plan.get("sections", []) if str(item.get("section_id")) == section_id), None)


def section_states_for_mode(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item["section_id"]): {
            "path": f"paper_output/drafts/sections/{slug(item['section_id'])}.md",
            "status": "PENDING",
            "attempts": 0,
            "same_issue_count": 0,
            "last_issue_signature": None,
            "last_attempt_sha256": None,
            "approved_sha256": None,
            "issues": [],
        }
        for item in plan.get("sections", [])
        if isinstance(item, dict) and item.get("section_id")
    }


def save_queue(
    project_root: Path,
    plan_path: Path,
    queue_issues: list[dict[str, Any]],
    status: str,
    extra_hashes: dict[str, str] | None = None,
) -> None:
    out = output_root(project_root)
    input_hashes = {relative(plan_path, project_root): sha256_file(plan_path)}
    input_hashes.update(extra_hashes or {})
    write_json(out / "qa" / "repair_queue.json", contract(
        producer_role="paper-formal-writer/repair-router",
        status=status,
        input_hashes=input_hashes,
        issues=queue_issues,
    ))


def state_inputs_fresh(project_root: Path, state: dict[str, Any], plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if str(plan.get("schema_version") or "") != "2.2" or str(plan.get("status") or "").upper() != "PASS":
        errors.append("writing plan envelope is not Standard 2.2 PASS")
    if str(state.get("schema_version") or "") != "2.2":
        errors.append("authoring state schema_version is not 2.2")
    errors.extend(validate_hashes(project_root, state.get("input_hashes"), "authoring state"))
    errors.extend(validate_hashes(project_root, plan.get("input_hashes"), "writing plan"))
    _, gate_errors = fresh_evidence_gate(project_root)
    errors.extend(gate_errors)
    return sorted(set(errors))


def validate_section(project_root: Path, section_id: str, plan: dict[str, Any], state: dict[str, Any], plan_path: Path) -> int:
    out = output_root(project_root)
    section = plan_section(plan, section_id)
    section_state = (state.get("sections") or {}).get(section_id)
    if not isinstance(section, dict) or not isinstance(section_state, dict):
        print(f"[BLOCKED] unknown authoring section: {section_id}", file=sys.stderr)
        return 1
    try:
        draft_path = safe_relative_path(project_root, section_state.get("path"))
    except ValueError as exc:
        print(f"[BLOCKED] {exc}", file=sys.stderr)
        return 1
    if not draft_path.is_file():
        print(f"[BLOCKED] missing draft: {section_state.get('path')}", file=sys.stderr)
        return 1
    text = draft_path.read_text(encoding="utf-8")
    issues, metrics = validate_common(text, section, section_id, require_marker=True)
    draft_hash = sha256_file(draft_path)
    signature = section_issue_signature(issues)
    changed_attempt = draft_hash != section_state.get("last_attempt_sha256")
    if changed_attempt:
        section_state["attempts"] = int(section_state.get("attempts") or 0) + 1
        if issues and signature == section_state.get("last_issue_signature"):
            section_state["same_issue_count"] = int(section_state.get("same_issue_count") or 0) + 1
        else:
            section_state["same_issue_count"] = 1 if issues else 0
        section_state["last_attempt_sha256"] = draft_hash
        section_state["last_issue_signature"] = signature if issues else None
    section_state["issues"] = issues
    queue: list[dict[str, Any]] = []
    if not issues:
        section_state["status"] = "PASS"
        section_state["approved_sha256"] = draft_hash
        state["status"] = "DRAFTING"
    elif section_id == "GLOBAL" and int(section_state.get("same_issue_count") or 0) >= 2:
        state["mode"] = "section"
        state["sections"] = section_states_for_mode(plan)
        state["status"] = "DRAFTING"
        queue = [{**item, "strategy": "section-rewrite", "attempt_count": section_state.get("attempts", 0)} for item in issues]
        print("[ROUTE] Global drafting failed twice with the same issue categories; switched to section mode.")
    else:
        count = int(section_state.get("same_issue_count") or 0)
        strategy = "micro-repair" if count >= 2 else "section-rewrite"
        queue = [{**item, "strategy": strategy, "attempt_count": section_state.get("attempts", 0)} for item in issues]
        if count >= 3:
            section_state["status"] = "BLOCKED"
            state["status"] = "BLOCKED"
            state["blocking_reason"] = f"{section_id} repeated the same blocking issue three times; use Lite or revise the evidence/requirements."
        else:
            section_state["status"] = "BLOCKED"
            state["status"] = "REPAIR_REQUIRED" if strategy == "micro-repair" else "DRAFTING"
    state["assembled"] = {"path": "paper_output/drafts/assembled_draft.md", "sha256": None, "status": "PENDING"}
    state["final"] = {"path": "paper_output/final_paper_source.md", "sha256": None, "status": "PENDING"}
    state["updated_at_utc"] = utc_now()
    write_json(out / "context" / "authoring_state.json", state)
    save_queue(
        project_root,
        plan_path,
        queue,
        "BLOCKED" if state["status"] == "BLOCKED" else ("PENDING" if queue else "PASS"),
        {relative(draft_path, project_root): draft_hash},
    )
    write_audit(
        out,
        scope=f"section:{section_id}",
        status="PASS" if not issues else "BLOCKED",
        input_hashes={relative(draft_path, project_root): draft_hash, relative(plan_path, project_root): sha256_file(plan_path)},
        issues=issues,
        metrics=metrics,
    )
    print(f"[{'PASS' if not issues else 'BLOCKED'}] Section {section_id} authoring audit")
    return 0 if not issues else 1


def validate_document(project_root: Path, scope: str, plan: dict[str, Any], state: dict[str, Any], plan_path: Path) -> int:
    out = output_root(project_root)
    record = state.get("assembled") if scope == "assembled" else state.get("final")
    if not isinstance(record, dict):
        print(f"[BLOCKED] missing {scope} state", file=sys.stderr)
        return 1
    try:
        path = safe_relative_path(project_root, record.get("path"))
    except ValueError as exc:
        print(f"[BLOCKED] {exc}", file=sys.stderr)
        return 1
    if not path.is_file():
        print(f"[BLOCKED] missing {scope} draft: {record.get('path')}", file=sys.stderr)
        return 1
    sections = [item for item in plan.get("sections", []) if isinstance(item, dict)]
    merged_section = {
        "section_id": scope.upper(),
        "title": scope,
        "target_chars": int((plan.get("target_chars") or {}).get("ideal") or sum(int(item.get("target_chars") or 0) for item in sections)),
        "requirements": merge_requirements(sections),
    }
    text = path.read_text(encoding="utf-8")
    issues, metrics = validate_common(text, merged_section, scope.upper(), require_marker=False)
    for message in approved_draft_errors(project_root, plan, state):
        issues.append(issue("stale-section", message, section_id=scope.upper()))
    for section in sections:
        title = str(section.get("title") or "").strip()
        if title and title not in text:
            issues.append(issue("section-coverage", f"document does not contain required section title: {title}", section_id=scope.upper()))
    if scope == "final":
        try:
            assembled_path = safe_relative_path(project_root, (state.get("assembled") or {}).get("path"))
        except ValueError as exc:
            issues.append(issue("stale-assembly", str(exc), section_id="FINAL"))
        else:
            if not assembled_path.is_file() or sha256_file(assembled_path) != (state.get("assembled") or {}).get("sha256"):
                issues.append(issue("stale-assembly", "assembled draft is missing or changed after assembly", section_id="FINAL"))
            else:
                assembled_text = assembled_path.read_text(encoding="utf-8")
                normalized_final = re.sub(r"\s+", "", text)
                normalized_assembled = re.sub(r"\s+", "", assembled_text)
                similarity = SequenceMatcher(None, normalized_assembled, normalized_final, autojunk=False).ratio()
                metrics["assembly_similarity"] = round(similarity, 6)
                if similarity >= 0.995:
                    issues.append(issue("global-revision", "final_paper_source.md is unchanged or only trivially changed from assembled_draft.md; a substantive global revision is required", section_id="FINAL"))
    current_hash = sha256_file(path)
    if not issues:
        record["status"] = "PASS"
        record["sha256"] = current_hash
        state["status"] = "PASS" if scope == "final" else "ASSEMBLED"
        state["blocking_reason"] = None
        save_queue(project_root, plan_path, [], "PASS", {relative(path, project_root): current_hash})
    else:
        record["status"] = "BLOCKED"
        record["sha256"] = current_hash
        state["status"] = "REPAIR_REQUIRED"
        queued = [{**item, "strategy": "section-rewrite", "attempt_count": 1} for item in issues]
        save_queue(project_root, plan_path, queued, "PENDING", {relative(path, project_root): current_hash})
    state["updated_at_utc"] = utc_now()
    write_json(out / "context" / "authoring_state.json", state)
    write_audit(
        out,
        scope=scope,
        status="PASS" if not issues else "BLOCKED",
        input_hashes={relative(path, project_root): current_hash, relative(plan_path, project_root): sha256_file(plan_path)},
        issues=issues,
        metrics=metrics,
    )
    print(f"[{'PASS' if not issues else 'BLOCKED'}] {scope} authoring audit")
    return 0 if not issues else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Standard section, assembled, or final authoring output.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--section")
    target.add_argument("--assembled", action="store_true")
    target.add_argument("--final", action="store_true")
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    out = output_root(project_root)
    plan_path = out / "plan" / "writing_plan.json"
    state_path = out / "context" / "authoring_state.json"
    try:
        plan = read_json(plan_path)
        state = read_json(state_path)
    except ValueError as exc:
        print(f"[BLOCKED] {exc}", file=sys.stderr)
        return 1
    freshness = state_inputs_fresh(project_root, state, plan)
    if freshness:
        state["status"] = "BLOCKED"
        state["blocking_reason"] = "; ".join(freshness)
        state["updated_at_utc"] = utc_now()
        write_json(state_path, state)
        for error in freshness:
            print(f"[BLOCKED] {error}", file=sys.stderr)
        return 1
    if args.section:
        return validate_section(project_root, args.section, plan, state, plan_path)
    return validate_document(project_root, "assembled" if args.assembled else "final", plan, state, plan_path)


if __name__ == "__main__":
    raise SystemExit(main())
