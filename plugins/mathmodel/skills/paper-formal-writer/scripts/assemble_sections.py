from __future__ import annotations

import argparse
import sys
from pathlib import Path

from authoring_contracts import output_root, read_json, relative, safe_relative_path, sha256_file, strip_markers, utc_now, validate_hashes, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministically assemble passed Standard authoring drafts.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
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
    errors = validate_hashes(project_root, state.get("input_hashes"), "authoring state")
    errors.extend(validate_hashes(project_root, plan.get("input_hashes"), "writing plan"))
    units: list[tuple[str, dict]] = []
    if state.get("mode") == "global":
        units = [("GLOBAL", (state.get("sections") or {}).get("GLOBAL", {}))]
    else:
        units = [
            (str(item.get("section_id")), (state.get("sections") or {}).get(str(item.get("section_id")), {}))
            for item in plan.get("sections", [])
            if isinstance(item, dict) and item.get("section_id")
        ]
    parts: list[str] = []
    for section_id, record in units:
        if not isinstance(record, dict) or record.get("status") != "PASS":
            errors.append(f"section {section_id} is not PASS")
            continue
        try:
            path = safe_relative_path(project_root, record.get("path"))
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not path.is_file() or sha256_file(path) != record.get("approved_sha256"):
            errors.append(f"section {section_id} changed after validation")
            continue
        parts.append(strip_markers(path.read_text(encoding="utf-8")))
    if errors:
        state["status"] = "BLOCKED"
        state["blocking_reason"] = "; ".join(sorted(set(errors)))
        state["updated_at_utc"] = utc_now()
        write_json(state_path, state)
        for error in sorted(set(errors)):
            print(f"[BLOCKED] {error}", file=sys.stderr)
        return 1
    assembled_path = out / "drafts" / "assembled_draft.md"
    assembled_path.parent.mkdir(parents=True, exist_ok=True)
    assembled_path.write_text("\n\n".join(part.strip() for part in parts if part.strip()) + "\n", encoding="utf-8")
    state["status"] = "ASSEMBLED"
    state["assembled"] = {
        "path": relative(assembled_path, project_root),
        "sha256": sha256_file(assembled_path),
        "status": "PASS",
    }
    state["final"] = {"path": "paper_output/final_paper_source.md", "sha256": None, "status": "PENDING"}
    state["blocking_reason"] = None
    state["updated_at_utc"] = utc_now()
    write_json(state_path, state)
    print(f"[PASS] Assembled validated drafts without renumbering: {relative(assembled_path, project_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
