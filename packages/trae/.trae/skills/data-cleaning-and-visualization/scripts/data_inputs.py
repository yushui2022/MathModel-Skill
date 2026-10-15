"""Manifest-bound inputs shared by the Standard data helpers."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PureWindowsPath


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def project_path(root: Path, value: object) -> Path:
    if not isinstance(value, str) or not value.strip() or '\x00' in value:
        raise ValueError('Expected a nonempty project-relative path')
    text = value.replace('\\', '/')
    if Path(text).is_absolute() or PureWindowsPath(text).drive or ':' in text or '..' in text.split('/'):
        raise ValueError(f'Path must be project-relative: {value}')
    path = (root / text).resolve()
    if path == root.resolve() or not path.is_relative_to(root.resolve()):
        raise ValueError(f'Path escapes project: {value}')
    return path


def modeling_inputs(root: Path) -> tuple[list[Path], list[dict]]:
    manifest_path = project_path(root, 'paper_output/input_manifest.json')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if not isinstance(manifest, dict) or not isinstance(manifest.get('entries'), list):
        raise ValueError('Invalid input manifest; rerun preflight before cleaning')
    files, skipped, seen = [], [], set()
    for entry in manifest['entries']:
        if not isinstance(entry, dict):
            raise ValueError('Invalid input manifest entry')
        path = project_path(root, entry.get('path'))
        if path in seen:
            raise ValueError(f'Duplicate input: {entry.get("path")}')
        seen.add(path)
        if entry.get('role') != 'raw_data' or entry.get('usable_for_modeling') is not True:
            skipped.append({'path': entry.get('path'), 'role': entry.get('role'),
                            'reason': 'not approved raw modeling data'})
            continue
        if not path.is_file() or sha256_file(path) != entry.get('sha256'):
            raise ValueError(f'Input missing or changed; rerun preflight: {entry.get("path")}')
        files.append(path)
    return sorted(files, key=lambda p: p.as_posix()), skipped


def current_cleaning_report(root: Path) -> dict:
    path = project_path(root, 'paper_output/data_cleaned/cleaning_report.json')
    report = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(report, dict) or report.get('status') != 'PASS':
        raise ValueError('Cleaning has not passed; inspect cleaning_report.json')
    hashes = report.get('input_hashes')
    if not isinstance(hashes, dict) or 'paper_output/input_manifest.json' not in hashes:
        raise ValueError('Cleaning report has no input provenance')
    for name, expected in hashes.items():
        target = project_path(root, name)
        if not target.is_file() or sha256_file(target) != expected:
            raise ValueError(f'Cleaning input changed: {name}')
    for dataset in report['datasets']:
        output = project_path(root, dataset['cleaned_output'])
        if not output.is_file() or sha256_file(output) != dataset['output_sha256']:
            raise ValueError(f'Cleaned output changed: {dataset["cleaned_output"]}')
    return report
