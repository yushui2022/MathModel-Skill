# Pro Machine Contracts

Use schema `3.2`. Every contract has `schema_version`, `created_at_utc` (UTC),
`producer_role`, `input_hashes` and `status`. Duplicate JSON keys, nonfinite numbers,
absolute artifact paths and path escapes are rejected. Artifact paths are relative to
`paper_output_pro/`; original input paths are relative to the project. The configuration
binds approvals to that project location. Do not migrate or rewrite old PASS envelopes.

## P0-P2 and Approvals

- P0 inventories original inputs and installed instructions. Re-running it unchanged is
  idempotent. Modifying, adding or removing originals invalidates approval, even without
  re-running P0. Configuration records declared model, model profile, reasoning profile,
  capabilities, instruction precedence and execution policy.
- `instruction_audit.json`: current `instruction_manifest_sha256`; `reviewed_files`
  covering every locator/hash exactly once; resolved `conflicts`; empty
  `unresolved_conflicts`; exact `active_execution_contract` from the manifest.
- `problem_consensus.json`: at least three `independent_analyses` entries with
  `role_id/path/sha256`, each resolving to an isolated analysis with a substantive
  summary; `consensus/disagreements/assumptions/subproblems/attachment_roles`.
  Agreement may legitimately leave `disagreements` empty.
- `candidate_routes.json`: seven nonnegative `weights` summing to one;
  `subproblems[].subproblem_id/routes[]`. Routes have unique `route_id`,
  distinct `model_family`, `is_interpretable_baseline`, seven `scores` in 0-10,
  `experiment_plan` and `expected_evidence`. Use globally distinct route IDs.
- `tournament_report.json`: `decisions[]` with subproblem, selected and backup IDs,
  rejected routes and reasons, recommended experiment plan and implementation risks.
  `comparison_rules` maps each preregistered result ID to a rule. Numeric rules need
  `kind:numeric, atol, rtol`; exact rules `kind:exact`; statistical rules
  `kind:statistical, equivalence_margin, alpha`. Do not loosen rules after seeing results.
- CP1 binds configuration, input and instruction inventories/audit, consensus and analyses.
  CP2 adds candidates, decisions, source ledger and retrieved content/receipts.
  CP3 binds all computation evidence and claim links. Any upstream change invalidates
  that and all later checkpoints. Approval requires the user's explicit decision text.
  Use `pro_checkpoint.py validate --checkpoint N` to require all approvals through N;
  omitting N checks the latest already approved stage (or stage 1 if none). This
  freshness check does not approve later pending stages. Explicitly requesting a
  pending checkpoint never returns success; final delivery always requires all three.

## Public Sources

Run `pro_capture_source.py --project-root <project> --source-id S1 --url <public-url>`
after CP1. It saves actual public HTTP content and a retrieval receipt under research/.
The adapter rejects private addresses, credential-bearing URLs and unsuccessful HTTP
responses; it does not authenticate, bypass paywalls or certify semantic authority.

Each `source_ledger.json.sources[]` entry has `source_id/url/title/publisher/purpose`,
`accessed_at_utc/content_sha256/snapshot_path/retrieval_receipt/retrieval_receipt_sha256`,
`access_status:PUBLIC_OK`, `authorization_required:false` and `claim_ids`.
`critical_claims[]` has `claim_id/source_ids/cross_validation_required`.
A single-source exception needs `single_source_reason`. Confirm relevance and
publisher independence by inspecting the saved content, not by counting domain names.
For entirely user-supplied/constructed data, sources and critical_claims may be empty.

## Recorded Experiments

Create a JSON run specification under code/, then execute:

```bash
python <entry-scripts>/pro_run_experiment.py --project-root <project> --spec code/base.json
python <entry-scripts>/pro_run_experiment.py --project-root <project> --refresh-manifest
```

Specification example (not a PASS contract):

```json
{
  "run_id": "base-primary",
  "route_id": "q1-milp",
  "implementation_id": "highs-formulation",
  "script": "code/solve.py",
  "dependencies": [],
  "inputs": ["data_cleaned/input.json"],
  "args": ["--input", "data_cleaned/input.json", "--out", "{run_dir}"],
  "stochastic": false,
  "timeout_seconds": 1800
}
```

The script writes `{run_dir}/metrics.json` containing a nonempty numeric `metrics`
object, plus declared scientific outputs. Randomized specifications set stochastic=true,
an integer seed and pass `{seed}` to the program. Dependencies must include all local
computation helpers. Each unique run directory retains logs, failures, actual execution
environment, argv, seed, exit code and before/after hashes. The process watchdog can be
raised for long jobs; it is not a total workflow budget. This runner is not a security sandbox.

`experiment_manifest.json.runs[]` contains `run_id/receipt_path/receipt_sha256`.
Refresh after all concurrent runs finish. Never omit failed receipts.
Metric references are objects such as `{"run_id":"base-primary","metric":"cost"}`.

## Verification and Freeze

- `replication_report.json.critical_results[]`: `result_id`, at least two
  `replication_paths` metric references, `comparison_rule`, `independence_rationale`
  and `agreement_status`. The gate reads and compares real metrics, not just PASS.
  Different filenames alone are not independent algorithms; reviewers inspect code.
- `robustness_report.json`: nonempty `baseline_comparisons/sensitivity_tests/
  constraint_stress_tests`, each with `test_id/interpretation/measurements`.
  Measurements extend metric references with actual `value`; stress entries also need
  `feasibility_assessment`. `stochastic_methods[]` records `run_ids/metric/mean/variance/
  confidence_level/confidence_interval/target_half_width/interval_stable`.
  At least ten actual distinct seeds are required, and summary statistics are recomputed.
- `ablation_report.json.ablations[]`: `component/with_component/without_component/
  effect/interpretation`; effect is without minus with. Empty arrays require a
  substantive `not_applicable_reason`.
- `claim_evidence_map.json.claims[]`: `claim_id/statement/section_id/evidence_ids/
  external/source_ids/numeric_evidence`. Numeric evidence extends metric references
  with `decimals` and `display`. Claims must cover all preregistered critical results.
  A nonnumeric, source-backed statement may use `claim_type:qualitative`, a substantive
  `qualitative_rationale` and empty numeric evidence. Do not invent an experiment or
  number for a purely qualitative citation. Numeric claims remain the default.
- `pro_freeze_evidence.py` requires fresh CP3 and recomputes checks. Freeze includes
  the complete evidence file inventory, original-input binding, claims, reverse index
  and approval hash. Adding an unrecorded output invalidates it too.

## Manuscript and Review

`paper_plan.json` contains `title/language/target_characters`, ordered `sections[]`
(`section_id/title/minimum_characters`) and `figures[]` (`path/sha256`).
Write one `final_paper_source.md`, with real headings, explicit Markdown tables/images,
native-convertible math and removable `<!-- claim:C1 -->` markers in the corresponding
evidence paragraphs. Figures must be frozen. Use numeric displays with declared precision.
Run `pro_paper_audit.py`; avoid padding to satisfy the 80% minimum-length guard.

`pro_collect_reviews.py --round 1 --prepare` creates PENDING requests, not approvals.
Each real isolated reviewer fills its own `reviews/round-1/<role>.json`:
`role/isolated_context/checks_performed/assessment/findings`, current
`input_hashes` of source, freeze and plan; `execution` with
`mode:subagent|fresh-session/context_id/model/record_path/record_sha256`.
Findings use `finding_id/severity/evidence/disposition`; resolved CRITICAL/MAJOR
items also require `resolution_evidence`. Preserve the actual host execution record.
Collect without --prepare. The final round needs all five distinct contexts on the
same current inputs. Same-user writable records do not cryptographically prove
honesty; neither synthetic fixtures nor same-conversation role labels count as real reviews.

## Word/PDF Delivery

Run the formal formatter, then `pro_render_pdf.py`. The renderer records current
DOCX/PDF hashes, actual LibreOffice version/exit code and all page PNG hashes in
`render_manifest.json`. Inspect every page and write `visual_review.json` with
`render_manifest_sha256` and `pages[]` carrying `page/image_sha256/status/issues/
observations`. Unresolved issues block delivery.

Run `pro_format_check.py --project-root <project>` and `pro_gate.py`. These commands
regenerate expected DOCX structure from the formal source, compare text in both
directions against PDF and verify sections, numerical tokens, formulas, images and
current visual reviews. Formatting cannot be approved by manually writing PASS.
Actual scientific merit still requires the five-role assessment and real-task evaluation.

## Recovery

A successful retry resets the consecutive-failure counter. Stop on the same normalized
failure three consecutive times, missing user data/authorization, or a genuine host
capability gap. Do not impose an overall token/runtime budget or fabricate missing
capabilities to avoid reporting a blocker.
