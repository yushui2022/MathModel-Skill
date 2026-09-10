# M3 linear-v1: independently checked optimization specifications

Use only when `pro_config.json.optimization_check_profile` is `linear-v1`.
This is a versioned **companion** to Pro schema 3.3, not a reinterpretation of
existing checkpoint approvals. LP/MILP arithmetic is implemented; prediction
leakage checking is not implemented.

## Establish the approved scope before computation

1. At P0, call normal `pro_preflight.py` with the additional option
   `--optimization-check-profile linear-v1` before checkpoint 1 approval.
   This writes `optimization_check_profile: "linear-v1"` into configuration and
   preserves it on later idempotent preflights even when the option is omitted.
   The existing checkpoint 1 config hash then binds profile selection. For an older
   project, explicitly enable this profile and return to the newly stale checkpoint
   1 and 2 decisions; do not manufacture or copy approval hashes. This adds no fourth
   checkpoint. Without the profile the M3 adapter reports `MIGRATION_REQUIRED`.
2. Before checkpoint 2 approval, freeze required numeric data under `data_cleaned/`
   or `research/`. Write `optimization_specs/<route>.json` for every candidate route
   declared LP/MILP. Include every variable, unit, bound, integer domain, objective,
   constraint, data SHA-256 and the fixed `linear-v1` tolerance profile. The objective
   `metric` names the scalar key the real run must emit in `metrics.json`.
3. Write `optimization_applicability.json` using companion schema `1.0`:
   `schema_version`, `profile`, `input_hashes`, and `routes` are its exact fields.
   `input_hashes` must exactly hash the current `problem_consensus.json`,
   `candidate_routes.json`, and `tournament_report.json`. Each route record has exactly
   `subproblem_id`, `route_id`, `scope`, `spec_path`, `rationale` (at least 40 characters).
   Cover **every candidate route**, including rejected routes, with globally unique
   route IDs. Scope is `LP`, `MILP`, or `outside_scope`; the latter requires null
   `spec_path` and a concrete reason. Registered linear model families cannot be
   relabeled outside scope; existing specification files cannot be left unregistered.
4. Run `pro_optimization.py --project-root <project> --preapproval` from the installed
   `pro-workflow-orchestrator/scripts/` directory. This reads files and diagnoses
   readiness only. Review the specification's meaning and applicability with the
   normal checkpoint 2 model-route decision, then run the normal
   `pro_checkpoint.py approve --checkpoint 2 --decision <actual user decision>`.
   With this profile enabled, the approval hashes automatically include applicability,
   every spec (including tolerances), and all declared frozen numeric inputs.

No label parser can prove that an arbitrary natural-language problem is non-linear.
The reviewer must check the preregistered applicability rationale and the mapping
from the original problem to the mathematical specification. Scope changes after
approval invalidate its hash; a missing result is a failure, never non-applicability.

## Actual runs and delivery

The real run specification must include its optimization specification file **and**
all that specification's data files in `inputs`. Keep original run specifications
under `code/` and use `pro_run_experiment.py`; never author successful receipts.
For a supported route, each successful run must produce
`experiments/<run_id>/optimization_result.json` with exactly:

- `schema_version: "1.0"`, the run's `run_id`, and the raw file `spec_sha256`;
- `values`: every declared variable ID and a finite numeric solution value;
- `reported_objective`: scalar value also emitted under the approved objective
  `metric` in the run's recorded `metrics.json`;
- `claim`: `feasible`, `heuristic`, or `optimal`;
- `certificate`: null or the supported bound certificate below.

Run the standalone checker for diagnostics:

```text
python <QA-skill>/scripts/check_optimization_spec.py --spec <spec.json> --result <optimization_result.json>
```

Then run `pro_optimization.py --project-root <project>` for full run/approval binding.
It checks all successful supported runs in the real manifest and requires checked
evidence for every selected supported route. It rechecks current receipt hashes and
the complete checkpoint 2 hash set. Missing legacy bindings report
`MIGRATION_REQUIRED`. The standard checkpoint 3 validator and final `pro_gate.py`
actually invoke this adapter when the profile is enabled; final verification does
not trust an earlier checker report. Specifications and applicability enter the
normal evidence inventory and freeze.

Do not pass a native runner self-reported `feasibility=true` into this checker.
The strict result schema rejects it. Residuals, variable bounds, integer distance
and objective accounting are independently recomputed using exact rational
representations of the JSON decimal numbers. JSON booleans, NaN/Infinity, duplicate
keys/IDs, unknown fields and undeclared variables are rejected.

## Fixed numerical scope

`tolerances` must exactly equal:

```json
{"feasibility_absolute":1e-7,"integrality_absolute":1e-7,"objective_absolute":1e-7,"objective_relative":1e-9}
```

Constraint/bound residuals use absolute declared units. Integer distance has its own
absolute tolerance. Objective comparison uses `atol + rtol * max(abs(a), abs(b))`.
Different scaling or tolerances require a newly versioned checker profile; they
cannot be relaxed after seeing an invalid solution. A near-integer feasible value
is checked within these declared tolerances, not asserted to be exactly integral.

## Supported evidence for optimality

The checker supports a directly verifiable `lagrangian_bound` certificate with
exact fields `kind` and `multipliers`. Multipliers cover all constraint IDs.
For an inequality they are nonnegative; equality multipliers may have either sign.
`ge` constraints are multiplied by -1 to form `Ax <= b`. For maximization the
objective is negated first. For minimization, the certificate forms
`c + A^T lambda` and minimizes its linear expression over the declared variable
bounds, yielding a global objective bound. An unbounded reduced-cost direction must
cancel **exactly**, rather than being rounded to zero. This bound is also valid
for the continuous relaxation of a MILP; it does not generally close a MILP gap.

Example: maximize `1 + 2*x` subject to `0 <= x <= 10`, `capacity: x <= 4`.
The solution `x=4` has objective 9. The certificate
`{"kind":"lagrangian_bound","multipliers":{"capacity":2}}` independently
establishes bound 9 and zero gap.

Only a feasible solution whose verified bound gap meets the fixed objective
tolerance is `CERTIFIED_WITHIN_TOLERANCE`. Missing, loose, or unsupported evidence
for an `optimal` claim returns `UNKNOWN`/`UNSUPPORTED` and blocks the M3 gate.
A solver status or quoted gap alone is not verified evidence. A feasible or
heuristic claim can pass feasibility without claiming optimality. Neither a
passing arithmetic check nor a certificate proves that the model encodes the
original problem correctly. Paper reviewers must also reject prose that claims
optimality beyond the checked scope.

The adapter returns `PASS` for checked applicable scope, `NOT_APPLICABLE` for a
freshly approved all-outside-scope inventory, or `BLOCKED` with precise errors.
Never describe `NOT_APPLICABLE` or legacy baseline Pro PASS as LP/MILP validation.
JSON Schemas: [spec](optimization-spec.schema.json), [result](optimization-result.schema.json).
Cross-file identities, finite numbers and semantic invariants are enforced by the
Python validator in addition to those structural schemas.
