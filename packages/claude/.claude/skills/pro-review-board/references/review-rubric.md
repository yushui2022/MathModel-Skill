# Pro review board rubric

Run all five roles in isolated contexts. A reviewer receives the frozen evidence and
paper but not another reviewer's conclusions until the round is complete.

- `mathematical_correctness`: assumptions, derivations, units, constraints, numerical
  interpretation, uncertainty, and correspondence to the question.
- `code_reproducibility`: environment, commands, seeds, hashes, reruns, independent
  replication, and manual-tampering resistance.
- `source_provenance`: public access, authority, cross-validation, claim linkage,
  citation accuracy, and authorization boundaries.
- `paper_expression`: global argument, terminology, tables, figures, formulas,
  citations, pagination, and contest compliance.
- `adversarial_challenge`: leakage, hidden assumptions, cherry-picking, counterexamples,
  failure regimes, alternate explanations, and likely judge objections.

Classify findings as CRITICAL, MAJOR, MINOR, or NOTE. Every finding has an ID, evidence,
required repair, owner, and disposition. Apply repairs only after all five reviews in a
round are complete. Local draft repairs may be rechecked locally, but the final
complete round must put all five roles on the same current manuscript. Final PASS requires zero unresolved
Critical or Major findings in the final complete round. Repeating the same normalized
failure for three consecutive repair rounds is a recorded blocker.

In competition mode, assess every confirmed question under the reviewer's own
expertise in `subproblem_assessments`: `subproblem_id`, `verdict` (ADEQUATE or
INADEQUATE), and concrete `evidence` of at least 40 characters explaining the
relevant argument/result and section. Inspect the actual manuscript, not just the
author's coverage map. Missing questions, unsupported derivations, uninterpreted
results or token validation are Major even when the paper has 20 pages. Passing
word counts and markers does not justify an ADEQUATE verdict. Source reviews must
also assess questions using only supplied data; explain why no external claim is
needed rather than inventing citations. Length adjustments must be tied to the
checkpoint-approved scope. Test fixtures are never evidence of long-paper quality.
