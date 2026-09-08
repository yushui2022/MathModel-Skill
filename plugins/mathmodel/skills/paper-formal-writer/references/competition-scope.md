# Competition Scope

Scope is stored in `writing_plan.json.delivery` and bound to authoring/format hashes. Regenerate the plan and rerun downstream audits after a scope change. Old plans without delivery scope must be prepared again.

The default is a complete competition manuscript: a 14000-character planning target, an 8000-effective-character main-paper floor, and 18 rendered pages before appendices. These are guardrails against accidentally delivering an abstract, not scoring criteria or universal contest rules. Read the actual task's length rules; explicitly justify custom floors or a requested short report. The scripts do not infer a contest-specific upper page limit.

Each question follows the existing Standard `5.1`, `5.2`, ... model hierarchy and needs substantial prose under its own heading (at least 300 effective characters as a skeleton check). Explain problem-specific assumptions, variables, objective/constraints, derivation, implementation, computed answers, validation and limitations. A numeric mention alone is not an explanation.

When short, locate the missing argument: derive an unexplained formula, justify a data transformation, interpret the baseline difference, quantify uncertainty, discuss failure conditions, or connect results to the question. Add only supported material. Do not invent experiments or expand through repetitive definitions, huge figures, inflated spacing, code dumps or empty pages.

HTML comments, fenced code, headings and image URLs do not contribute to the effective-character floor. Appendices are excluded. The PDF check conservatively excludes a page containing the appendix boundary, so begin the appendix on a new page and inspect the rendered boundary. Raw page count is not a sufficient quality test; inspect all pages.

`short-report` and `smoke-test` require a nonempty scope reason. They test a smaller declared deliverable, not full competition readiness. Automated checks cannot verify that a reason was genuinely supplied by a user, nor judge novelty or mathematical merit. Report the actual scope and remaining limitations honestly.
