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
