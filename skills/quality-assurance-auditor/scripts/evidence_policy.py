"""Shared fail-closed rules for Standard evidence producers and consumers."""
from pathlib import Path, PureWindowsPath

POLICY_VERSION = 2
ACCEPTED_STATES = frozenset({'computed', 'verified', 'validated', 'pass'})


def accepted_status(item):
    if not isinstance(item, dict):
        return False
    states = [item[key] for key in ('status', 'evidence_status') if key in item]
    return bool(states) and all(isinstance(s, str) and s.strip().lower() in ACCEPTED_STATES for s in states)


def policy_errors(report):
    if not isinstance(report, dict) or type(report.get('policy_version')) is not int or report['policy_version'] != POLICY_VERSION:
        return ['Evidence policy changed; rerun evidence_gate.py (old PASS reports are not reusable)']
    return []


def project_artifact(root, value):
    if not isinstance(value, str) or not value.strip() or '\x00' in value:
        raise ValueError('Evidence path must be a nonempty project-relative string')
    text = value.strip().replace('\\', '/')
    if Path(text).is_absolute() or PureWindowsPath(text).drive or ':' in text or '..' in text.split('/'):
        raise ValueError(f'Evidence path must be project-relative: {value}')
    root = root.resolve()
    path = (root / text).resolve()
    if path == root or not path.is_relative_to(root):
        raise ValueError(f'Evidence path escapes project: {value}')
    return path
