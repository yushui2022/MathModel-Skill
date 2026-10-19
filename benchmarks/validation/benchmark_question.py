"""Acceptance fixture for the two declared synthetic tasks, not a general solver.

Copied to q1_model.py/q2_model.py in an isolated test project. Ground-truth
comparison lives only in the test, never in the production numerical helper.
"""
from pathlib import Path

from result_contract_io import (PROJECT_ROOT, RESULTS_DIR, TABLES_DIR, load_json,
                                run_question_scaffold, upsert_question_contracts, write_json)


def main():
    qid = Path(__file__).stem.removesuffix('_model').upper()
    route = load_json(PROJECT_ROOT / 'paper_output/plan/model_route.json', {})
    question = next(q for q in route['questions'] if q['question_id'] == qid)
    run_question_scaffold(question)
    # Input profiles are exploratory, not evidence for these two computed tasks.
    index = load_json(TABLES_DIR / 'table_index.json', {})
    index['tables'] = [t for t in index['tables'] if t['question_id'] != 'ALL']
    write_json(TABLES_DIR / 'table_index.json', index)
    result = next(q for q in load_json(RESULTS_DIR / 'model_results.json', {})['questions'] if q['question_id'] == qid)
    metrics = [m for m in load_json(RESULTS_DIR / 'metrics.json', {})['items'] if m['question_id'] == qid]
    tables = [t for t in load_json(TABLES_DIR / 'table_index.json', {})['tables'] if t['question_id'] == qid]
    summary = '; '.join(f"{m['metric_id']}={m['value']} {m['unit']}" for m in metrics)
    upsert_question_contracts(question, summary, metrics, tables,
                              [{'question_id': qid, 'conclusion_text': summary, 'evidence_status': 'computed'}],
                              result['outputs'], status='computed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
