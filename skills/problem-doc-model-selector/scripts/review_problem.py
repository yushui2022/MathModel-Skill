"""Record an explicit Agent review of ambiguous extraction, bound to its inputs.

This records review, not proof of mathematical correctness. It never approves
results or changes a downstream gate. Review the original before confirming.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PureWindowsPath


def content_hash(analysis):
    payload = {key: analysis.get(key) for key in ('documents', 'questions', 'global_constraints', 'review_requirements')}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()


def review_errors(root, analysis):
    if not isinstance(analysis, dict) or not analysis.get('questions'):
        return ['Problem analysis has no questions']
    requirements = analysis.get('review_requirements')
    # Legacy hand-authored analyses remain supported; new extraction includes this field.
    if requirements is None:
        return []
    errors = []
    for doc in analysis.get('documents', []):
        name = str(doc.get('path', '')).replace('\\', '/')
        path = (root / name).resolve()
        if not name or Path(name).is_absolute() or PureWindowsPath(name).drive or '..' in name.split('/') or not path.is_relative_to(root.resolve()):
            errors.append(f'Unsafe problem document path: {name}')
        elif not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != doc.get('sha256'):
            errors.append(f'Problem document changed; rerun analysis: {name}')
    if requirements:
        review = analysis.get('review_record') or {}
        if (review.get('status') != 'APPROVED' or not str(review.get('reviewer') or '').strip()
                or not str(review.get('note') or '').strip() or not review.get('reviewed_at_utc')
                or review.get('content_sha256') != content_hash(analysis)):
            errors.append('Problem extraction needs source review: ' + '; '.join(requirements))
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, default=Path.cwd())
    parser.add_argument('--reviewer', required=True)
    parser.add_argument('--note', required=True, help='What was visually checked and corrected')
    parser.add_argument('--confirm', required=True, action='store_true')
    args = parser.parse_args()
    root = args.project_root.resolve()
    path = root / 'paper_output/step1/problem_analysis.json'
    analysis = json.loads(path.read_text(encoding='utf-8'))
    if not args.reviewer.strip() or not args.note.strip():
        parser.error('reviewer and note must not be empty')
    analysis['review_record'] = {'status': 'APPROVED', 'reviewer': args.reviewer, 'note': args.note,
                                'reviewed_at_utc': datetime.now(timezone.utc).isoformat(),
                                'content_sha256': content_hash(analysis)}
    errors = review_errors(root, analysis)
    if errors:
        raise SystemExit('\n'.join(errors))
    path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Problem review recorded. Regenerate downstream plans if they already exist.')


if __name__ == '__main__':
    main()
