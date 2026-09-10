from __future__ import annotations

import argparse
from pathlib import Path

from pro_checkpoint import require_checkpoints
from pro_contracts import canonical_json_hash, contract, output_root, read_json, write_json
from pro_validation import evidence_files


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze verified evidence after the user's checkpoint 3 decision.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    project = args.project_root.resolve()
    root = output_root(project, args.output_root)
    errors = require_checkpoints(project, root, 3)
    if errors:
        for error in errors:
            print(f"[BLOCKED] {error}")
        return 1
    claims = read_json(root / "claim_evidence_map.json")["claims"]
    reverse = {}
    for item in claims:
        for key in [*item["evidence_ids"], *item.get("source_ids", [])]:
            reverse.setdefault(key, []).append(item["claim_id"])
    hashes = evidence_files(root)
    content = {
        "checkpoint_3_approval_hash": read_json(root / "checkpoint_ledger.json")["checkpoints"]["3"]["approval_hash"],
        "file_hashes": hashes, "claims": claims,
        "reverse_index": {k: sorted(set(v)) for k, v in sorted(reverse.items())},
    }
    write_json(root / "evidence_freeze.json", contract(
        producer_role="pro-evidence-freezer", status="PASS", input_hashes=hashes,
        **content, snapshot_sha256=canonical_json_hash(content),
    ))
    print(f"[PASS] Frozen {len(hashes)} verified evidence files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
