# Pro machine contracts

Every JSON contract is an object containing `schema_version`, `created_at_utc`,
`producer_role`, `input_hashes`, and `status`. Use schema version `3.0`, UTC ISO-8601
timestamps, SHA-256 hashes, and paths relative to the project root or
`paper_output_pro/`. A contract with missing metadata is invalid.

## Checkpoint contracts

- Checkpoint 1 freezes `pro_config.json`, `input_manifest.json`,
  `instruction_manifest.json`, `instruction_audit.json`, and `problem_consensus.json`.
- Checkpoint 2 freezes `problem_consensus.json`, `source_ledger.json`,
  `candidate_routes.json`, and `tournament_report.json`.
- Checkpoint 3 freezes `tournament_report.json`, `experiment_manifest.json`,
  `replication_report.json`, `robustness_report.json`, and `ablation_report.json`.
- `checkpoint_ledger.json` stores `PENDING`, `APPROVED`, or `REJECTED`, the user's
  decision, decision time, per-file hashes, and the canonical approval hash.
- Any changed or missing approved artifact invalidates that checkpoint and all later
  checkpoints. Never copy approval records between projects.

## Model and instruction contracts

`pro_config.json` preserves the user-declared model and effort for compatibility, and
adds `model_profile`, `reasoning_profile`, `model_profile_catalog`, capabilities, and
`execution_policy`. A matched profile identifies its canonical model ID, support tier,
phase effort, behavior flags, and official source URLs. An unknown profile is warned but
does not reduce any Pro gate.

`instruction_manifest.json` inventories project `AGENTS.md`/`CLAUDE.md` files that are
present plus every installed Pro `SKILL.md`, with locators and SHA-256 hashes.
`instruction_audit.json` must contain:

- `instruction_manifest_sha256` equal to the current manifest hash;
- `reviewed_files` containing every manifest locator and hash exactly once;
- `conflicts` with the applied resolution for each conflict;
- an empty `unresolved_conflicts` array;
- `active_execution_contract` exactly equal to the manifest's
  `required_execution_contract`.

Adding, removing, or modifying an inventoried instruction invalidates checkpoint 1 and
all downstream approvals. Re-run P0 and repeat the audit.

## Required payloads

`problem_consensus.json` contains at least three isolated analyses, consensus,
disagreements, assumptions, subproblems, and attachment roles.

`source_ledger.json` contains `sources[]` with URL, title, publisher, access time,
content hash, public-access status, purpose, and linked claim IDs. Critical external
claims should have two independent authoritative sources whenever feasible.

`candidate_routes.json` contains 3-5 materially different routes per subproblem,
including one interpretable baseline. `tournament_report.json` records the weighted
scores, selected and backup route, rejections, experiments, risks, and expected
evidence.

`experiment_manifest.json` records environment, commands, scripts, inputs, outputs,
seeds, exit codes, and hashes. Failed routes remain in the manifest.

`replication_report.json` records two independent implementations or recomputation
paths for every critical result, the comparison rule, tolerance or interval, and
agreement status. `robustness_report.json` records baselines, sensitivity, stress
tests, stochastic summaries, and confidence intervals. Randomized methods use at
least 10 distinct seeds and expand the run count when intervals are unstable.
`ablation_report.json` records applicable ablations or a defensible not-applicable
reason.

`evidence_freeze.json` is written only after checkpoint 3 is freshly approved. It
contains hashes for code, environment, inputs, outputs, seeds, commands, metrics,
figures, tables, and claim links. `review_board_report.json` records five independent
review roles and every repair round. `pro_gate_report.json` is the final machine gate.

## Stop policy

Continue repairing without a token, candidate-count, or wall-time budget. Stop only
for missing user data/authorization or after the same normalized failure occurs in
three consecutive repair attempts. Record all failed attempts.
