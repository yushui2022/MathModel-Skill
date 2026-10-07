# Pro forward evaluation matrix

Before a Pro release, run every case from a clean install on all preferred profiles:
Claude Fable 5.1, Claude Opus 5.5, GPT-6.1 Sol, and GPT-6 Astra.
Run compatibility smoke evaluations on Claude Opus 5
and Claude Sonnet 5, and retain regression coverage for Claude Fable 5 and GPT-5.6 Sol.
Archive the declared and canonical model IDs, reasoning profile, prompts, instruction
audit, checkpoint decisions, contract hashes, runtimes, failures, final gate, DOCX, and
PDF.

The 2026-10-07 catalog update verifies published configuration, not these model runs.
For the three newly checked profiles, compare `high` and `max` on the same task and
frozen inputs, recording actual host/API settings, token usage, elapsed time, tool
failures, argument coverage, and review findings. Do not infer a model's identity from
a gateway alias, or advertise speed/quality from synthetic contract tests. The host
must expose the required tools and independent contexts before a run can qualify.

| Case | Required capabilities | Acceptance focus |
|---|---|---|
| Prediction | temporal split, baseline, uncertainty | no leakage; stable interval; independent recomputation |
| Optimization | explicit variables and constraints | feasible solution; stress tests; solver-independent check |
| Graph | node/edge semantics and discrete result | exact replication; baseline; perturbation robustness |
| Open data | public research and provenance | valid URLs; two-source critical claims; claim-source trace |

For every run, all three checkpoints must be explicit, all critical numbers must have
two paths, final review must have zero unresolved Critical/Major findings, and the
DOCX/PDF final gate must PASS. A failed run remains in the evaluation archive.

Use `paper_delivery.mode=competition` with the actual multi-question contest task
and current event rules. Record the confirmed page range, actual counted PDF pages,
per-question argument coverage and all five question-level reviews. At least one
complete long paper near the approved 20-page planning target is required to claim
long-form readiness. A report shortened at user request validates only that smaller
scope, not the default long-paper workflow.

The five-page `examples/pro-3.2-optimization` paper is an engineering smoke example,
not long-form acceptance. `run_forward_benchmark.py` now selects `smoke-test`
explicitly. Synthetic 20-page pagination fixtures validate counting only; they are
not mathematical papers or a substitute for the above real-contest evaluation.
This upgrade does not claim that a fresh real-contest long-paper evaluation is complete.

The project may describe a profile as supported after synthetic tests pass. Describe it
as Pro-qualified only after its required forward cases pass without relaxing gates.
