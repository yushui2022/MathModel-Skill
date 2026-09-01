from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Pro public-source provenance.")
    parser.add_argument("--ledger", type=Path, default=Path("paper_output_pro/source_ledger.json"))
    args = parser.parse_args()
    errors: list[str] = []
    try:
        data = json.loads(args.ledger.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[FAIL] {exc}")
        return 1
    sources = data.get("sources")
    if not isinstance(sources, list):
        errors.append("sources[] is required")
        sources = []
    by_id = {}
    for source in sources:
        source_id = source.get("source_id")
        if not source_id:
            errors.append("source_id is required")
            continue
        by_id[source_id] = source
        parsed = urlparse(str(source.get("url", "")))
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            errors.append(f"{source_id}: invalid URL")
        for field in ("title", "publisher", "accessed_at_utc", "content_sha256", "purpose", "claim_ids"):
            if not source.get(field):
                errors.append(f"{source_id}: missing {field}")
        if source.get("access_status") != "PUBLIC_OK" or source.get("authorization_required") is True:
            errors.append(f"{source_id}: source is not authorized public evidence")
    for claim in data.get("critical_claims", []):
        resolved = [by_id[item] for item in claim.get("source_ids", []) if item in by_id]
        if not resolved:
            errors.append(f"{claim.get('claim_id')}: no valid source")
        if claim.get("cross_validation_required", True) and len({item.get('publisher') for item in resolved}) < 2:
            errors.append(f"{claim.get('claim_id')}: needs two independent publishers")
    for error in errors:
        print(f"[FAIL] {error}")
    print(f"[{'PASS' if not errors else 'BLOCKED'}] Pro source ledger")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
