# Formal Artifact Evidence

All paths below are relative to `paper_output_pro/`, never to another edition's output.

Metric payloads may omit status. When they declare `status` or `evidence_status`, every declared value must be computed/verified/validated/pass (case-insensitive). Keep solver termination details such as optimal or infeasible in a separate `solver_status`; never label infeasible or failed computations as successful evidence.

- Keep formal plots and data tables in their successful experiment directory when possible.
- A copied artifact needs an index entry linking its exact bytes to `run_id` and `output_path`.
- `figure_index.json.figures[]` and `table_index.json.tables[]` (legacy `tables/table_index.json` also supported) require a path and a positive status. All declared status fields must agree on acceptance.
- Raster images must decode and must not be tiny or blank. Formal indexed tables are UTF-8 CSV/TSV or XLSX, with unique nonempty headers and actual data rows. Each XLSX sheet must be valid.
- Generated previews have `evidence_role: exploratory`; they are not formal evidence even if someone changes status to computed. Keep unused previews outside the frozen evidence folders, under `drafts/`, and remove their entries from the formal indexes.
- An unregistered file in `figures/` or `tables/` is not accepted merely because it exists. Failed experiments remain in the manifest but cannot supply formal evidence.
- The runner marks invalid generated images/tables as FAILED even when the process exits zero. Keep their receipts and files as diagnostic history, rerun under a new ID after fixing the producer, and do not reference failed outputs in formal indexes.
- Content checks run before checkpoint 3 approval and when validating an evidence freeze. After changing an artifact or index, validate checkpoints, request renewed approval where stale, and freeze again.

Example for a copied table:

```json
{
  "tables": [{
    "path": "tables/costs.csv",
    "status": "computed",
    "run_id": "cost-comparison",
    "output_path": "experiments/cost-comparison/costs.csv"
  }]
}
```

This validates recorded provenance and file structure, not whether an algorithm or a scientific interpretation is correct. Independent replication, claim tracing and the review board remain mandatory.
