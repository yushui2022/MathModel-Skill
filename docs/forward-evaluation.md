# Pro forward evaluation matrix

Before a Pro release, run each case from a clean install on both Claude Fable 5 and
GPT-5.6 Sol Ultra. Archive the declared model, reasoning effort, prompts, checkpoint
decisions, contract hashes, runtimes, failures, final gate, DOCX, and PDF.

| Case | Required capabilities | Acceptance focus |
|---|---|---|
| Prediction | temporal split, baseline, uncertainty | no leakage; stable interval; independent recomputation |
| Optimization | explicit variables and constraints | feasible solution; stress tests; solver-independent check |
| Graph | node/edge semantics and discrete result | exact replication; baseline; perturbation robustness |
| Open data | public research and provenance | valid URLs; two-source critical claims; claim-source trace |

For every run, all three checkpoints must be explicit, all critical numbers must have
two paths, final review must have zero unresolved Critical/Major findings, and the
DOCX/PDF final gate must PASS. A failed run remains in the evaluation archive.
