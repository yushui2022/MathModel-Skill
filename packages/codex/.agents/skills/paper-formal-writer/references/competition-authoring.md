# Complete Competition Papers

Read this before P7. A five-page constructed example validates the tool chain, not
the ability to solve and explain a complete competition problem. Length and checks
are necessary diagnostics, not evidence of originality, sound modeling or a prize.

## Scope Is Decided Before Writing

P0 stores `paper_delivery` in `pro_config.json`; checkpoint 1 binds it together with
the confirmed questions. Default `competition` plans 18-24 counted pages and at
least 8000 effective body characters. These are configurable project defaults,
not competition rules or a character-to-page conversion. Normally aim near 20
pages with the actual task's reasoning and evidence. The lower page target blocks
undersized delivery; exceeding the planning upper target is recorded, not a rule
violation unless the contest's hard cap is exceeded.

Only explicitly requested `short-report` and `smoke-test` use a smaller scope.
P0 requires `--scope-reason` for either mode or a custom length. Show any change
to the user at checkpoint 1, never silently downgrade when a draft is hard to write.
Re-running P0 without scope arguments preserves the existing selection. Older
contracts without `paper_delivery` require a new P0 and approvals, not a hidden default.

Built-in dated profiles (verify applicability to the actual event):

| Profile | Target counts | Hard page cap | Abstract |
|---|---|---|---|
| `generic` | abstract + body + references | none assumed | task-specific |
| `cumcm-2026` | body only | 30 body pages | at most 1 page |
| `mcm-2026` | entire solution including references/appendices | 25 | at most 1 page |

CUMCM electronic papers start with the abstract, without identifying cover sheets;
no contents page. MCM excludes only the trailing AI-use report from its page cap;
a shared solution/AI page still counts. A page belongs to every section actually
occupying it. Start the body, appendices and AI report on appropriate boundaries.
Official references:
[CUMCM 2026](https://www.mcm.edu.cn/html_cn/node/4cd596519c9eb9fbd866398f6df0caa3.html),
[MCM 2026 problem instructions](https://www.contest.comap.com/undergraduate/contests/mcm/contests/2026/problems/2026_MCM_Problem_C.pdf).
The profiles implement length accounting, not every contest rule. Independently check
anonymity, fonts, required letters/memos, submission files and AI-use disclosure.
For another contest/year, use generic only after checking its instructions; record and
review its specific constraints instead of claiming one of these dated profiles applies.

## Plan the Actual Argument

Start with the confirmed subproblems and frozen claims, not a page-filling template.
Allocate most space to model choices, derivations, computed findings and validation;
keep repeated problem restatements and generic algorithm introductions short.
A three-question paper might need one abstract page, 2-3 pages of framing/data,
10-12 pages of question-specific work, 3-4 pages of validation/discussion and concise
conclusions/references. Adjust this planning example to the questions and page cap.

Each confirmed question needs these substantive dimensions, wherever they fit:

- `rationale`: why the chosen route matches the task and data; why a simpler baseline
  or rejected alternative is insufficient. Do not claim novelty merely from model names.
- `derivation`: definitions, assumptions, units, objective/equations, constraints and
  their derivation. Explain how the mathematical form represents the original question.
- `method`: implementation details needed to reproduce the solution, convergence/gap
  or stopping criteria, and the applicable numerical assumptions.
- `results`: answer the question explicitly with frozen outcomes, meaningful comparisons
  and interpreted figures/tables. Distinguish estimated facts from optimized decisions.
- `validation`: show what the independent recomputation and task-appropriate stress,
  held-out evaluation or counterexample establish, and what they do not establish.
- `limitations`: conditions under which the answer could fail, uncertainties, and
  their effect on the recommendation. Avoid a generic limitations paragraph for all questions.

These need not be six headings per question. A proof-based question uses mathematical
formulation/proof and applicable verification instead of inventing empirical experiments.
Shared methods may be explained once and referenced, but each question needs its own
connection to the method, result and limitations. Do not duplicate a shared passage to
meet a character minimum. Missing facts or results require earlier-stage work and fresh
approvals; they cannot be manufactured during authoring.

## Paper Plan Contract

`paper_plan.json` uses the common envelope. `input_hashes` must equal the current
hashes of `pro_config.json`, `problem_consensus.json`, `evidence_freeze.json`.
Use `delivery_mode` matching the approved policy, plus `title`, `language`,
`target_characters`, `figures` and ordered `sections`.

Every section corresponds to exactly one `##` heading (not a nested `###`), with
`section_id/title/minimum_characters/kind`. Kind is `abstract`, `body`, `references`,
`appendix`, `ai-disclosure` or `frontmatter`. Include all top-level sections; keep
appendices and the single AI disclosure last. Claim `section_id` values were frozen
in P6, so preserve those IDs while organizing the text. Figures use frozen path/SHA-256.

For competition mode, `subproblem_coverage` covers each confirmed subproblem exactly
once. Each item has `subproblem_id`, `section_ids` pointing to body sections,
`claim_ids` from the frozen map, and an `arguments` object with all six dimensions.
Each dimension references a section and unique removable paragraph anchor, e.g.:

```json
"derivation": {"section_id": "q1-model", "anchor": "q1:derivation"}
```

Write `<!-- argument:q1:derivation -->` at the end of the relevant paragraph.
The anchor must occur once in the referenced section, next to at least 80 effective
characters of real argument. This tiny structural minimum only rejects empty stubs;
it does not mean an 80-character derivation is adequate. Results and validation
paragraphs also need a mapped `<!-- claim:C1 -->`. The existing claim audit checks
required numeric values there. Other evidence paragraphs retain their claim markers.

The complete paper must reach 80% of its declared target, and its body must meet
the independently checkpoint-bound minimum. Abstracts, references, appendices,
code fences, comments and headings cannot replace substantive body length.

## Write, Review, Render

Write complete chapters into one official `final_paper_source.md` over as many turns
as necessary. Keep a concise continuity note for symbols, claims, figure numbering
and unfinished sections when context is tight. Do not equate a single response with
a complete paper. Then perform a global revision for consistency and argument flow.

Run `pro_paper_audit.py`; repair real omissions. Each of the five independent final
reviewers must assess every question in `subproblem_assessments`, using
`subproblem_id/verdict/evidence`. `ADEQUATE` needs a concrete explanation with section,
derivation/result and task relevance, not a renamed PASS. Any inadequate question
blocks final approval even when length and structural markers pass.

Render from the one reviewed source, inspect every PDF page, then run
`pro_format_check.py` and `pro_gate.py`. The format report records actual section
pages and the scope-adjusted count. Unidentifiable/ambiguous headings block accounting;
do not supply guessed page numbers. Do not enlarge fonts, spacing, figures or appendices
to pass a length check. If the task genuinely supports only a short report, explicitly
reconfirm that scope instead. Smoke/short PASS has no competition-paper acceptance.
