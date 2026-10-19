# Evidence Hardening Validation

Date: 2026-10-19
Edition: latex
Version: dated branch snapshot; evidence policy 2
Local environment: Windows, Python 3.11.1.

## Scope

Backport evidence-status and artifact-integrity safeguards without merging editions or changing their installation architecture. The Standard branch and existing competition examples were not modified.

## Results

17 export-integrity tests, 10 evidence tests, 4 preview tests and 5 legacy workflow groups passed (36 total).

- Canonical payloads synchronized to the edition's supported platforms.
- Skill Creator validation passed for all SKILL.md entries.
- Archives rebuilt from canonical sources; tracked archive contents and repeat-build consistency checked locally.
- GitHub's other operating systems and Python 3.12 are not local test results.

## Regression Coverage

- Explicit failed, unknown, empty or contradictory statuses cannot be hidden by a positive enclosing status.
- Raster images are actually decoded; generated CSV/TSV/XLSX data tables are parsed.
- Fresh hashes do not make corrupted content acceptable.
- Figures and tables must belong to the question's declared output artifacts; unknown/duplicate question IDs and non-finite metrics are rejected.
- Old policy PASS reports cannot authorize formal Word/TeX export. Source-only output remains SOURCE_ONLY, never PDF acceptance.

## Commands

```text
python tests/test_latex_integrity.py
python tests/test_evidence_gate.py
python tests/test_preview_evidence.py
python tests/run_tests.py
python scripts/sync_latex_hotfix.py --check
python scripts/build_release_packages.py
```

## Limits

No XeLaTeX executable was available. Compiler success paths use test doubles; no claim of actual TeX rendering or full competition acceptance is made.
File hashes record integrity, not an adversarial sandbox or proof of scientific correctness. Reviewing the original problem, checking units and interpretation, and testing real contest cases remain necessary.
No tags or releases were created for this update.
