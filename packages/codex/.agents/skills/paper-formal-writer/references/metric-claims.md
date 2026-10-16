# Numerical Claim Bindings

Use this contract when Standard writes key numerical conclusions. A number near
a familiar label is insufficient: preserve the unit, sample population, split,
experiment and evidence strength. This is deterministic consistency checking,
not a proof of the model, experiment design or arbitrary natural-language claims.

## Before S6: Computed Metrics

The modeling program must emit each key metric in `results/metrics.json` with:

```json
{
  "metric_id": "Q1.test.rmse",
  "question_id": "Q1",
  "metric_name": "RMSE",
  "aliases": ["均方根误差"],
  "status": "computed",
  "value": 1.25,
  "unit": "万元",
  "split": "test",
  "sample_scope": "2024年留出样本",
  "claim_strength": "observed",
  "allowed_transforms": ["identity"],
  "source_table": {
    "path": "paper_output/tables/results.csv",
    "row": {"metric_id": "Q1.test.rmse"},
    "value_column": "value",
    "unit_column": "unit"
  }
}
```

- `metric_id` is unique and stable, including distinct IDs for train/test metrics.
- `split`: `train`, `test`, `validation`, `all`, or `not_applicable`. Use the last
  only for results without a sample split (for example, a deterministic objective).
- `sample_scope` names the actual evaluated population or optimization scenario.
  Never invent it during writing. Keep its label concise and reuse it in prose.
- `unit` is explicit; dimensionless quantities use `"1"`, not a missing unit.
- `source_table` selects exactly one CSV row. Export a CSV evidence table when
  the native output is XLSX/another format. Keep numerical cells machine-readable.
- Register the CSV and verification reports in execution `output_artifacts`.
  The writer matches the question and table to exactly one successful run.
  Optional `run_id` disambiguates multiple runs; otherwise it is resolved from
  the manifest, not fabricated by the writer.
- Only `identity` and `ratio_to_percent` are supported transformations. The
  latter requires source unit `1` and produces `%`. Emit a separately computed
  metric for currency/unit conversions, differences, ratios or improvements;
  do not add arbitrary arithmetic to the writing contract.

For `claim_strength: feasible` or `optimal`, supply `verification_path` pointing
to a JSON artifact from that same run. Required fields are `status: PASS`, the
matching `metric_id`, `unit` and `objective_value`, and `feasibility_verified: true`.
`optimal` additionally requires `optimality_verified: true`. The producer must
provide a real solver certificate/bound or mathematically justified check; a
feasibility-only checker, a zero exit code or a handwritten Boolean is not an
optimality certificate. The writer checks provenance and report consistency,
not the mathematical validity of arbitrary certificate implementations.

## Prepare And Migrate

After S6 PASS, rebuild the outline and run `prepare_authoring.py`. It resolves
numeric requirements from the computed metrics, checks source CSV cells and run
hashes, and freezes the catalog in `writing_plan.json`. Missing context blocks
preparation with the field name; return to modeling and regenerate evidence.
Do not fill missing context by editing a passed writing plan.

Old formal plans must be prepared again. `competition` and `short-report` use
the same checks. The explicit `smoke-test` delivery keeps compatibility with
installation fixtures and does not certify numerical claims.

## Write And Bind

Every draft with an active metric catalog has a sibling `.claims.json`:

- `drafts/sections/5.md` -> `drafts/sections/5.claims.json`
- `drafts/global_draft.md` -> `drafts/global_draft.claims.json`
- `final_paper_source.md` -> `final_paper_source.claims.json`

```json
{
  "schema_version": "1",
  "source_sha256": "SHA256_OF_THE_EXACT_MARKDOWN_BYTES",
  "claims": [{
    "metric_id": "Q1.test.rmse",
    "quote": "2024年留出样本的测试集 RMSE 为 1.25万元。",
    "value": 1.25,
    "unit": "万元",
    "transform": "identity",
    "assertion": "observed"
  }]
}
```

Use `claims: []` for a chapter without numerical claims. Hash with Python
`hashlib.sha256(path.read_bytes()).hexdigest()` after writing the Markdown.

For a key result sentence, state one metric value, its name/approved alias,
the recorded sample label, split and unit. Put interpretations, table cross
references and multi-metric comparisons in adjacent sentences. This intentionally
constrained format makes key claims auditable; it does not constrain every
sentence in the paper. A quote must match a complete visible sentence or table
row, not a comment, heading, code block, formula or arbitrary substring. Formula
definitions are excluded from result-occurrence scanning. Put the required
context in the row itself when binding a table row; inherited headers alone
are not parsed as context. English split labels are `training set`, `test set`,
`validation set`, `full sample`; Chinese labels are 训练集、测试集、验证集、全样本.
Do not omit the split in the abstract or change it during global revision.

`decimals: 0..8` explicitly allows decimal half-up rounding. Without it the
displayed value must match exactly. Use decimal/scientific notation without
thousands separators. For source `0.125` with approved `ratio_to_percent`, use
`value: 12.5`, `unit: "%"`; writing `0.125%` fails.

`assertion` is `observed`, `feasible`, or `optimal` and cannot exceed the recorded
verification strength. The audit also flags recognized unsupported optimality
wording. Review qualitative claims and paraphrases manually; do not treat a PASS
as semantic coverage of all possible language.

## Audit, Assembly And Export

Existing `validate_authoring.py --section/--assembled/--final` commands audit
bindings and report resolved experiment/table/sample references in
`qa/draft_audit.json`. Failures enter the existing repair queue.

Assembly merges the sidecars deterministically while removing evidence comments
from the Markdown. Global revision must update final quotes and the final source
hash. Reusing a stale sidecar fails. Changing any approved sidecar invalidates
S7 and blocks formal DOCX export, even when the Markdown did not change.

The sidecars are not rendered into Word. They are audit artifacts, not paper
content. Each recognized numerical occurrence of a registered metric must have
a valid binding; a correct sentence cannot excuse another incorrect occurrence.
Unregistered synonyms and implicit statements still require author review.
