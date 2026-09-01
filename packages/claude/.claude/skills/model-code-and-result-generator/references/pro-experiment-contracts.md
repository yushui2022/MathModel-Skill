# Pro experiment contract details

Each `experiment_manifest.json` run records a stable `run_id`, `route_id`, command,
working directory, environment lock or package inventory, distinct seeds, exit code,
status, failure reason when applicable, and path-to-SHA-256 objects for scripts, inputs,
and outputs. Paths are relative to `paper_output_pro/`.

`replication_report.json` identifies each critical result and two independent
`implementation_id` values, their outputs, the preregistered comparison rule, tolerance
or distribution criterion, and `agreement_status`.

`robustness_report.json` contains non-empty baseline comparisons, sensitivity tests,
constraint stress tests, and stochastic method summaries. Every stochastic summary has
at least 10 unique seeds, mean, variance, confidence interval, interval stability, and
an expansion record when unstable.

`ablation_report.json` contains component/effect records or a defensible
`not_applicable_reason`. Failed and rejected runs remain in the experiment manifest.
