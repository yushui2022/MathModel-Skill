# Evidence Hardening Validation

Date: 2026-10-19
Edition: pro
Version: 3.3.0-pro.4
Local environment: Windows, Python 3.11.1.

## Scope

Backport evidence-status and artifact-integrity safeguards without merging editions or changing their installation architecture. The Standard branch and existing competition examples were not modified.

## Results

99 cases passed with REQUIRE_LIBREOFFICE=1, including real DOCX-to-PDF rendering.

- Canonical payloads synchronized to the edition's supported platforms.
- Skill Creator validation passed for all SKILL.md entries.
- Archives rebuilt from canonical sources; tracked archive contents and repeat-build consistency checked locally.
- GitHub's other operating systems and Python 3.12 are not local test results.

## Regression Coverage

- Explicit failed, unknown, empty or contradictory statuses cannot be hidden by a positive enclosing status.
- Raster images are actually decoded; generated CSV/TSV/XLSX data tables are parsed.
- Fresh hashes do not make corrupted content acceptable.
- Invalid generated assets cause FAILED receipts even with a zero process exit. Failed runs stay as diagnostic history but cannot supply indexed or manuscript evidence.
- Checkpoint 3, freeze validation and manuscript figures verify successful experiment origin; copied assets require explicit receipt links.

## Commands

```text
python tests/run_pro_tests.py
python scripts/check_skills.py
python scripts/build_release_packages.py --verify
```

## Limits

Synthetic role and approval records test the machinery, not real independent model assessments. No paid model was called.
File hashes record integrity, not an adversarial sandbox or proof of scientific correctness. Reviewing the original problem, checking units and interpretation, and testing real contest cases remain necessary.
No tags or releases were created for this update.
