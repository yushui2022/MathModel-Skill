# Pro workflow contracts

All JSON contracts use schema version `3.0` and include:

```json
{
  "schema_version": "3.0",
  "created_at_utc": "2026-01-01T00:00:00Z",
  "producer_role": "role-id",
  "input_hashes": {},
  "status": "PASS"
}
```

Required contracts are `pro_config.json`, `checkpoint_ledger.json`,
`problem_consensus.json`, `source_ledger.json`, `candidate_routes.json`,
`tournament_report.json`, `experiment_manifest.json`, `replication_report.json`,
`robustness_report.json`, `ablation_report.json`, `evidence_freeze.json`,
`review_board_report.json`, `final_format_report.json`, and `pro_gate_report.json`.

Checkpoint 1 freezes configuration, input manifest, and problem consensus. Checkpoint
2 freezes consensus, sources, candidates, and tournament decision. Checkpoint 3 freezes
the tournament and all experiment/replication/robustness/ablation reports. Any changed
approved file invalidates that checkpoint and all downstream states.

See `.claude/skills/pro-workflow-orchestrator/references/pro-contracts.md` for the
payload requirements and `.claude/skills/pro-model-tournament/references/` plus
`.claude/skills/pro-review-board/references/` for their rubrics.
