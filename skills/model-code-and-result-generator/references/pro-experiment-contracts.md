# Pro Experiment Contracts

Use schema 3.2. The complete field specification and run-spec example are in
`pro-workflow-orchestrator/references/pro-contracts.md`.

1. Preregister result IDs and comparison rules in the approved tournament.
2. Write separate primary and verification code under code/. Declare all local helpers.
3. Execute each specification with pro_run_experiment.py. Actual receipts record
   environment, command arguments, seeds, script/input/output hashes and exit codes.
   Failed attempts stay on disk. No manually authored successful execution receipts.
4. Collect all receipts with --refresh-manifest after the parallel batch completes.
   Manifest runs contain run_id, receipt_path and receipt_sha256.
5. Reference real metrics by run_id and metric. Replication paths need independent
   implementations and matching preregistered rules, not merely matching PASS strings.
6. Robustness measurements include their recorded value and interpretation. Summaries
   of stochastic runs must cover all successful randomized runs, at least ten distinct
   seeds and a numerically verified confidence interval/precision target.
7. Claim numeric references must belong to the replication evidence they cite. Retain
   source links for external claims; register critical external claims for cross-validation.
8. Freeze only after a new explicit checkpoint 3 decision.

A duplicate optimum can yield different valid assignments; compare exact discrete
invariants only when the task actually requires a unique discrete answer. For numerical
objectives, separately verify feasibility and objective accounting. Scenario sensitivity
and seed variability are not substitutes for out-of-sample validation.
