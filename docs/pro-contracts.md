# Pro workflow contracts

All JSON contracts use schema version `3.3` and include:

```json
{
  "schema_version": "3.3",
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

`pro_config.json.paper_delivery` locks competition/short-report/smoke-test mode,
contest profile, counted-page scope, planning range and substantive body minimum
at checkpoint 1. Default competition scope is 18-24 counted pages and 8000 effective
body characters, configurable with a reason and user confirmation, not a universal
contest minimum. Short/test scopes cannot qualify as a complete competition paper.

`paper_plan.json.input_hashes` must equal the current config, consensus and freeze
hashes. `delivery_mode` must match config. Ordered `sections[]` have a `kind` used
for real PDF page accounting; all `##` headings must be planned. Competition plans
include `subproblem_coverage[]` with section IDs, frozen claim IDs and six paragraph
anchors for rationale, derivation, method, results, validation and limitations.
Results/validation anchors need a mapped frozen claim in the same paragraph.
Every final reviewer must assess every confirmed question with
`subproblem_assessments[].subproblem_id/verdict/evidence`; inadequate or empty
assessments block acceptance. Full definitions are in the formal writer's
`references/competition-authoring.md`.

`final_format_report.json.details.paper_scope` records counted/total pages and
actual section positions. Its input hashes, and final review input hashes, also
include config and consensus. `pro_gate_report.json.acceptance_scope` is
`COMPETITION_REPORT_CHECKED`, `SHORT_REPORT_ONLY`, `ENGINEERING_SMOKE_ONLY` or
`NOT_ACCEPTED`. None means prize quality or cross-model qualification.

See `.claude/skills/pro-workflow-orchestrator/references/pro-contracts.md` for the
payload requirements and `.claude/skills/pro-model-tournament/references/` plus
`.claude/skills/pro-review-board/references/` for their rubrics.

The bundled frontier model catalog lives at
`.claude/skills/pro-workflow-orchestrator/references/model-profiles.json`. It records
canonical IDs, support tiers, effort aliases, phase effort and official vendor sources.
Unknown models remain runnable with a warning and must not receive reduced gates.
