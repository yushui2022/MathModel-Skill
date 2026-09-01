from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate isolated Pro problem analyses and consensus.")
    parser.add_argument("--output-root", type=Path, default=Path("paper_output_pro"))
    args = parser.parse_args()
    root = args.output_root.resolve()
    errors: list[str] = []
    try:
        consensus = json.loads((root / "problem_consensus.json").read_text(encoding="utf-8"))
        manifest = json.loads((root / "input_manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[FAIL] {exc}")
        return 1
    analyses = consensus.get("independent_analyses")
    if not isinstance(analyses, list) or len(analyses) < 3:
        errors.append("at least three independent analyses are required")
    else:
        role_ids = set()
        for item in analyses:
            path = root / item.get("path", "")
            role_ids.add(item.get("role_id"))
            if not path.is_file() or item.get("sha256") != sha256(path):
                errors.append(f"analysis missing or hash mismatch: {item.get('path')}")
            else:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("isolated_context") is not True:
                    errors.append(f"analysis is not marked isolated: {item.get('path')}")
        if len(role_ids) < 3 or None in role_ids:
            errors.append("independent analyses require at least three distinct role_id values")
    for field in ("consensus", "disagreements", "assumptions", "subproblems", "attachment_roles"):
        if not consensus.get(field):
            errors.append(f"problem_consensus.json requires {field}")
    manifest_roles = {item.get("path"): item.get("role") for item in manifest.get("files", [])}
    consensus_roles = {item.get("path"): item.get("role") for item in consensus.get("attachment_roles", [])}
    if manifest_roles != consensus_roles:
        errors.append("attachment_roles differ from the P0 input manifest")
    for error in errors:
        print(f"[FAIL] {error}")
    print(f"[{'PASS' if not errors else 'BLOCKED'}] Pro problem consensus")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
