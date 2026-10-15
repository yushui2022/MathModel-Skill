"""Offline numerical and integration regressions, without model/API calls."""
from __future__ import annotations

import itertools
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from openpyxl import Workbook

REPO = Path(__file__).resolve().parents[1]
SKILLS = REPO / 'packages/claude/.claude/skills'
SCRIPTS = SKILLS / 'model-code-and-result-generator/scripts'
sys.path.insert(0, str(SCRIPTS))
from modeling_tools import load_current_dataset, regression_baseline, verify_linear_solution
from data_inputs import sha256_file, current_cleaning_report


class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame({'x': list(range(8)), 'y': [3 + 2 * i for i in range(8)]})
        self.options = {'target': 'y', 'features': ['x'], 'train_rows': [0, 1, 2, 3, 4], 'test_rows': [5, 6, 7]}

    def evaluate(self, **changes):
        return regression_baseline(self.frame, **{**self.options, **changes})

    def test_known_linear_answer_and_training_mean_baseline(self):
        result = self.evaluate()
        self.assertAlmostEqual(result['coefficients']['x'], 2)
        self.assertAlmostEqual(result['intercept'], 3)
        self.assertLess(result['metrics']['RMSE'], 1e-10)
        expected = np.sqrt(np.mean((np.array([13, 15, 17]) - 7) ** 2))
        self.assertAlmostEqual(result['metrics']['baseline_RMSE'], expected)
        self.assertEqual([p['row_index'] for p in result['predictions']], [5, 6, 7])
        json.dumps(result, allow_nan=False)

    def test_test_data_cannot_change_training_preprocessing_or_fit(self):
        self.frame.loc[1, 'x'] = np.nan
        first = self.evaluate()
        self.frame.loc[5:, 'x'] = [10000, np.nan, 20000]
        self.frame.loc[5:, 'y'] = [-1000, 900, 2000]
        second = self.evaluate()
        self.assertEqual(first['preprocessing'], second['preprocessing'])
        self.assertEqual(first['coefficients'], second['coefficients'])
        self.assertEqual(first['intercept'], second['intercept'])
        self.assertEqual(second['preprocessing']['medians']['x'], 2.5)

    def test_empty_training_feature_not_rescued_by_test_values(self):
        self.frame.loc[:4, 'x'] = np.nan
        with self.assertRaisesRegex(ValueError, 'entirely missing'):
            self.evaluate()

    def test_missing_target_never_imputed(self):
        for row in (0, 7):
            with self.subTest(row=row):
                original = self.frame.loc[row, 'y']
                self.frame.loc[row, 'y'] = np.nan
                with self.assertRaisesRegex(ValueError, 'never impute'):
                    self.evaluate()
                self.frame.loc[row, 'y'] = original

    def test_invalid_and_overlapping_splits(self):
        for change in ({'test_rows': [4, 5]}, {'test_rows': [5, 5]}, {'test_rows': []},
                       {'test_rows': [8]}, {'train_rows': [0]}, {'test_rows': [True]},
                       {'test_rows': [5.0]}, {'test_rows': [-1]}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.evaluate(**change)

    def test_explicit_field_contract(self):
        for features in ([], ['y'], ['x', 'x'], ['absent']):
            with self.subTest(features=features), self.assertRaises(ValueError):
                self.evaluate(features=features)

    def test_missing_tokens_infinity_and_unexpected_text(self):
        self.frame['x'] = self.frame['x'].astype(object)
        self.frame.loc[0, 'x'] = ''
        self.evaluate()
        for bad in ('NA', 'not-a-number', np.inf):
            self.frame.loc[0, 'x'] = bad
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.evaluate()

    def test_constant_column_reports_nonidentifiability(self):
        self.frame['x'] = 1
        result = self.evaluate()
        self.assertTrue(result['warnings'])
        self.assertTrue(np.isfinite(result['metrics']['RMSE']))

    def test_dataframe_index_labels_do_not_change_split(self):
        expected = self.evaluate()
        self.frame.index = [20] * 8
        self.assertEqual(expected, self.evaluate())


class LinearVerificationTests(unittest.TestCase):
    def check_solution(self, **changes):
        options = {'c': [-3, -1], 'x': [2, 1], 'bounds': [(0, 2), (0, 2)],
                   'A_ub': [[1, 1]], 'b_ub': [3], 'integer_indices': [0, 1],
                   'reported_objective': -7}
        return verify_linear_solution(**{**options, **changes})

    def test_known_integer_problem_matches_exhaustive_reference(self):
        optimum = min(-3 * x - y for x, y in itertools.product(range(3), repeat=2) if x + y <= 3)
        result = self.check_solution()
        self.assertEqual(result['objective'], optimum)
        self.assertEqual(result['status'], 'PASS')
        self.assertFalse(result['optimality_verified'])
        json.dumps(result, allow_nan=False)

    def test_inequalities_equalities_bounds_and_integrality(self):
        cases = [({'x': [2, 2]}, 'inequality[0]'),
                 ({'A_eq': [[1, -1]], 'b_eq': [0]}, 'equality[0]'),
                 ({'x': [-1, 1]}, 'lower_bound[0]'),
                 ({'x': [3, 0]}, 'upper_bound[0]'),
                 ({'x': [1.5, 1]}, 'integer[0]')]
        for changes, name in cases:
            with self.subTest(name=name):
                result = self.check_solution(**changes)
                self.assertFalse(result['feasible'])
                self.assertTrue(any(c['constraint'] == name and not c['passed'] for c in result['checks']))

    def test_objective_mismatch_distinct_from_feasibility(self):
        result = self.check_solution(reported_objective=-8)
        self.assertTrue(result['feasible'])
        self.assertEqual(result['status'], 'FAIL')

    def test_integer_tolerance_does_not_grow_with_solution_magnitude(self):
        result = verify_linear_solution(c=[1], x=[1e9 + .5], bounds=[(None, None)], integer_indices=[0])
        self.assertFalse(result['feasible'])

    def test_tolerance_and_unbounded_variables(self):
        result = verify_linear_solution(c=[1], x=[-2], bounds=[(None, None)], A_eq=[[1]], b_eq=[-2 + 1e-9])
        self.assertEqual(result['status'], 'PASS')

    def test_malformed_problem_rejected(self):
        cases = [{'c': [1]}, {'x': [np.nan, 1]}, {'b_ub': None}, {'A_ub': [[1]]},
                 {'bounds': [(2, 0), (0, 2)]}, {'bounds': [(0, np.inf), (0, 2)]},
                 {'integer_indices': [0, 0]}, {'integer_indices': [2]}, {'atol': -1},
                 {'rtol': np.inf}, {'reported_objective': np.nan}]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.check_solution(**changes)


class ModelingIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='mathmodel-tools-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.output = self.root / 'paper_output'
        self.output.mkdir()
        (self.root / 'problem_files').mkdir()
        self.source = self.root / 'problem_files/data.csv'
        self.source.write_text('id,x,y\n001,0,3\n002,1,5\n003,2,7\n004,3,9\n005,4,11\n', encoding='utf-8')
        self.import_data()

    def run_script(self, script):
        return subprocess.run([sys.executable, str(script)], cwd=self.root, capture_output=True,
                              text=True, encoding='utf-8', timeout=60,
                              env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1'})

    def import_data(self, sources=None):
        entries = [{'path': p.relative_to(self.root).as_posix(), 'role': 'raw_data',
                    'usable_for_modeling': True, 'sha256': sha256_file(p)} for p in (sources or [self.source])]
        (self.output / 'input_manifest.json').write_text(json.dumps({'entries': entries}), encoding='utf-8')
        result = self.run_script(SKILLS / 'data-cleaning-and-visualization/scripts/clean_data.py')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def build(self):
        plan = self.output / 'plan'
        plan.mkdir(exist_ok=True)
        question = {'question_id': 'Q1', 'task_type': 'forecasting', 'data_source': 'problem_files/data.csv',
                    'sheet': None, 'regression': {'target': 'y', 'features': ['x'],
                                                 'train_rows': [0, 1, 2], 'test_rows': [3, 4]}}
        (plan / 'model_route.json').write_text(json.dumps({'questions': [question]}), encoding='utf-8')
        result = self.run_script(SCRIPTS / 'build_result_contracts.py')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return self.output / 'code/modeling/run_modeling.py'

    def test_history_excluded_and_identifiers_preserved(self):
        first = current_cleaning_report(self.root)['datasets'][0]['cleaned_output']
        self.source.write_text(self.source.read_text(encoding='utf-8').replace('001,0,3', '001,0,999'), encoding='utf-8')
        self.import_data()
        frame, path = load_current_dataset(self.root, source='problem_files\\data.csv')
        self.assertEqual(frame.loc[0, 'id'], '001')
        self.assertEqual(frame.loc[0, 'y'], '999')
        self.assertNotEqual(path, self.root / first)
        self.assertTrue((self.root / first).is_file())
        generator = runpy.run_path(str(SCRIPTS / 'build_result_contracts.py'))
        generator['find_cleaned_csv_files'].__globals__['BASE_DIR'] = self.root
        self.assertEqual(generator['find_cleaned_csv_files'](), [path])

    def test_multisheet_requires_explicit_selection(self):
        workbook = Workbook()
        workbook.active.title = 'first'
        workbook.active.append(['id', 'value'])
        workbook.active.append(['001', 1])
        other = workbook.create_sheet('second')
        other.append(['id', 'value'])
        other.append(['002', 2])
        source = self.root / 'problem_files/multiple.xlsx'
        workbook.save(source)
        self.import_data([source])
        with self.assertRaises(ValueError):
            load_current_dataset(self.root, source='problem_files/multiple.xlsx')
        frame, _ = load_current_dataset(self.root, source='problem_files/multiple.xlsx', sheet='second')
        self.assertEqual(frame.loc[0, 'value'], '2')
        with self.assertRaises(ValueError):
            load_current_dataset(self.root, source='problem_files/missing.csv')

    def test_changed_output_or_source_rejected(self):
        _, path = load_current_dataset(self.root)
        original = path.read_bytes()
        path.write_bytes(original + b'changed')
        with self.assertRaises(ValueError):
            load_current_dataset(self.root)
        path.write_bytes(original)
        self.source.write_text('changed', encoding='utf-8')
        with self.assertRaises(ValueError):
            load_current_dataset(self.root)

    def test_missing_report_does_not_scan_old_files(self):
        (self.output / 'data_cleaned/cleaning_report.json').unlink()
        result = self.run_script(SCRIPTS / 'build_result_contracts.py')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Run data cleaning', result.stdout)

    def test_unapproved_dataset_cannot_enter_current_report(self):
        report_path = self.output / 'data_cleaned/cleaning_report.json'
        report = json.loads(report_path.read_text(encoding='utf-8'))
        report['datasets'][0]['path'] = 'problem_files/answer.csv'
        report_path.write_text(json.dumps(report), encoding='utf-8')
        with self.assertRaises(ValueError):
            load_current_dataset(self.root)

    def test_real_generated_run_and_helper_integrity(self):
        runner = self.build()
        result = self.run_script(runner)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        receipt = json.loads((self.output / 'results/run_manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(receipt['status'], 'PASS')
        baseline = json.loads((self.output / 'results/q1_baseline.json').read_text(encoding='utf-8'))
        self.assertLess(baseline['metrics']['RMSE'], 1e-10)
        names = {item['path'] for item in receipt['runs'][0]['input_files']}
        self.assertIn('paper_output/code/modeling/modeling_tools.py', names)
        self.assertIn('paper_output/data_cleaned/cleaning_report.json', names)
        with patch.object(Path, 'cwd', return_value=self.root):
            gate = runpy.run_path(str(SKILLS / 'quality-assurance-auditor/scripts/evidence_gate.py'))
        results = json.loads((self.output / 'results/model_results.json').read_text(encoding='utf-8'))
        question = results['questions'][0]
        self.assertEqual(gate['run_manifest_failures'](question, receipt), [])
        helper = runner.with_name('modeling_tools.py')
        helper.write_text(helper.read_text(encoding='utf-8') + '\n# changed\n', encoding='utf-8')
        self.assertTrue(gate['run_manifest_failures'](question, receipt))

    def test_changed_input_invalidates_previous_success(self):
        runner = self.build()
        self.assertEqual(self.run_script(runner).returncode, 0)
        self.source.write_text('changed', encoding='utf-8')
        result = self.run_script(runner)
        self.assertNotEqual(result.returncode, 0)
        receipt = json.loads((self.output / 'results/run_manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(receipt['status'], 'FAIL')

    def test_input_change_during_run_is_not_recertified(self):
        runner = self.build()
        question = runner.with_name('q1_model.py')
        question.write_text("from pathlib import Path\nPath('../../data_cleaned/cleaning_report.json').write_text('{}')\n", encoding='utf-8')
        result = self.run_script(runner)
        self.assertNotEqual(result.returncode, 0)
        receipt = json.loads((self.output / 'results/run_manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(receipt['status'], 'FAIL')
        self.assertTrue(receipt['runs'][0]['integrity_failure'])


if __name__ == '__main__':
    unittest.main()
