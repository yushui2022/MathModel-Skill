# Pro Paper Quality

Machine PASS verifies declared artifacts and invariants. It is not proof that the
model is appropriate, the prose is insightful, or the paper deserves a prize.

## Argument Before Length

- Answer every confirmed subproblem with a decision, evidence and limitations.
- Separate supplied facts, estimated quantities, assumptions and optimized decisions.
- State what the result changes compared with a meaningful baseline. Abstracts need
  measured outcomes, not promises to apply an algorithm.
- Introduce symbols and units consistently; explain why constraints encode the task.
- Report unsuccessful routes, binding constraints and plausible counterexamples.
- Write one coherent manuscript. Do not inflate length with repeated methodology.

## Domain-Specific Checks

- Prediction: split data before preprocessing; avoid temporal/entity leakage; report
  held-out performance and calibration. More random seeds do not replace external validation.
- Optimization: independently test feasibility and objective accounting; give a solver
  bound, gap or exhaustive certificate when claiming optimality. Two agreeing heuristics
  are not a proof. Alternative optimal assignments need not be identical.
- Graph models: specify directedness, weights, connectivity and treatment of missing edges.
- Open data: inspect retrieved content and publisher independence. A URL or hash does not
  establish authority, relevance or independent measurement.
- Sensitivity: distinguish a fixed policy under disturbance from reoptimization after
  observing the disturbance. Scenario ranges are not statistical confidence intervals.

## Review and Visual Evidence

Use five real isolated contexts, concurrently or in fresh sequential sessions. Role
labels within one conversation are not isolation. If the host cannot supply this,
report the capability gap and do not fabricate a review PASS.

Local repairs can be checked locally during drafting, but final approval requires all
five roles to review the same current manuscript, plan and freeze. Each extra experiment
must address an unresolved question; repeated generic self-critique is not evidence.

Inspect every rendered page image. Verify glyphs, formulas, readable figures and tables,
page breaks, captions and citation placement. Text extraction cannot detect all layout
failures. Record actual observations in `visual_review.json`.
