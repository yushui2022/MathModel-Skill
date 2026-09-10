#!/usr/bin/env python3
"""Codex Skill fallback client for the same service used by MCP and the panel."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from runtime.service import ServiceClient, ensure_service


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("open", "status", "run", "job", "cancel"))
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--type", dest="job_type", choices=("preflight", "model_run", "evidence_check", "format_check", "final_check"))
    parser.add_argument("--model")
    parser.add_argument("--reasoning")
    parser.add_argument("--spec")
    parser.add_argument("--job-id")
    parser.add_argument("--cursor", type=int, default=0)
    parser.add_argument("--idempotency-key")
    args = parser.parse_args()
    try:
        descriptor = ensure_service(args.project_root)
        client = ServiceClient(descriptor)
        if args.action == "open":
            result = {k: descriptor[k] for k in ("project_id", "project_root", "dashboard_url")}
        elif args.action == "status":
            result = client.request("GET", "/api/status")
        elif args.action == "run":
            if not args.job_type:
                parser.error("run requires --type")
            options = {k: v for k, v in {"model": args.model, "reasoning": args.reasoning, "spec": args.spec}.items() if v is not None}
            result = client.request("POST", "/api/jobs", {"type": args.job_type, "options": options, "idempotency_key": args.idempotency_key})
        else:
            if not args.job_id or not args.job_id.isalnum():
                parser.error("job/cancel requires a valid --job-id")
            result = client.request("POST", f"/api/jobs/{args.job_id}/cancel", {}) if args.action == "cancel" else client.request("GET", f"/api/jobs/{args.job_id}?cursor={args.cursor}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
