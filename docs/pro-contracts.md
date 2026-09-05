# Pro workflow contracts

All JSON contracts use schema version `3.2` and include:

```json
{
  "schema_version": "3.2",
  "created_at_utc": "2026-01-01T00:00:00Z",
  "producer_role": "role-id",
  "input_hashes": {},
  "status": "PASS"
}
```

Required contracts are `pro_config.json`, `checkpoint_ledger.json`,
`instruction_manifest.json`, `instruction_audit.json`, `problem_consensus.json`,
`source_ledger.json`, `candidate_routes.json`,
`tournament_report.json`, `experiment_manifest.json`, `replication_report.json`,
`robustness_report.json`, `ablation_report.json`, `claim_evidence_map.json`,
`evidence_freeze.json`, `paper_plan.json`, `paper_audit.json`, `review_board_report.json`,
`render_manifest.json`, `visual_review.json`, `final_format_report.json`, and `pro_gate_report.json`.

Checkpoint 1 freezes configuration, input manifest, instruction inventory/audit, and
problem consensus. Checkpoint
2 freezes consensus, sources, candidates, and tournament decision. Checkpoint 3 freezes
the tournament and all experiment/replication/robustness/ablation reports. Any changed
approved file invalidates that checkpoint and all downstream states. Original inputs
are rehashed directly. All evidence files, including newly added files, are checked.
Experiment manifests index actual runner receipts; numerical comparisons read recorded
metrics. Final reviews are tied to the current source, plan and evidence freeze, and
must retain five distinct real execution records. Test fixture records are not reviews.

See `.claude/skills/pro-workflow-orchestrator/references/pro-contracts.md` for the
payload requirements and `.claude/skills/pro-model-tournament/references/` plus
`.claude/skills/pro-review-board/references/` for their rubrics.

The bundled frontier model catalog lives at
`.claude/skills/pro-workflow-orchestrator/references/model-profiles.json`. It records
canonical IDs, support tiers, effort aliases, phase effort and official vendor sources.
Unknown models remain runnable with a warning and must not receive reduced gates.
