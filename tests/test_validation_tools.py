"""Split-design and optional solver regressions. No model services are called."""
from __future__ import annotations

import copy
import builtins
import importlib.util
import itertools
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

SCRIPTS = Path(__file__).resolve().parents[1] / 'packages/claude/.claude/skills/model-code-and-result-generator/scripts'
sys.path.insert(0, str(SCRIPTS))
from validation_tools import validation_splits, backtest_regression
from solver_evidence import solve_linear_problem, validate_solver_report

HAS_SCIPY = importlib.util.find_spec('scipy') is not None


class SplitTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame({'date': pd.date_range('2024-01-01', periods=12).strftime('%Y-%m-%d'),
                                   'x': range(12), 'y': [2 * x + 3 for x in range(12)],
                                   'group': ['a'] * 4 + ['b'] * 4 + ['c'] * 4})
        self.config = {'kind': 'rolling_origin', 'time_column': 'date', 'min_train_size': 4, 'test_size': 2}

    def run_backtest(self, **changes):
        return backtest_regression(self.frame, **{
            'target': 'y', 'features': ['x'], 'validation': self.config, 'unit': 'kg',
            'feature_availability': {'x': 'known_in_advance'}, **changes})

    def test_rolling_folds_have_disjoint_evaluation_rows(self):
        folds = validation_splits(self.frame, self.config)
        self.assertEqual(len(folds), 4)
        self.assertEqual(folds[0]['train_rows'], [0, 1, 2, 3])
        self.assertEqual(folds[-1]['test_rows'], [10, 11])
        evaluated = [i for f in folds for i in f['test_rows']]
        self.assertEqual(len(evaluated), len(set(evaluated)))
        for f in folds:
            self.assertLess(max(f['train_rows']), min(f['test_rows']))

    def test_gap_and_bounded_training_window(self):
        folds = validation_splits(self.frame, {**self.config, 'gap': 1, 'window': 3})
        self.assertEqual(folds[0]['train_rows'], [1, 2, 3])
        self.assertEqual(folds[0]['test_rows'], [5, 6])
        self.assertEqual(folds[-1]['train_rows'], [5, 6, 7])

    def test_temporal_holdout_is_last_window(self):
        folds = validation_splits(self.frame, {'kind': 'temporal_holdout', 'time_column': 'date', 'test_size': 3, 'gap': 2})
        self.assertEqual(folds[0]['test_rows'], [9, 10, 11])
        self.assertEqual(folds[0]['train_rows'], list(range(7)))

    def test_same_timestamp_never_split_between_train_and_test(self):
        self.frame.loc[4, 'date'] = self.frame.loc[3, 'date']
        fold = validation_splits(self.frame, self.config)[0]
        self.assertIn(4, fold['train_rows'])
        self.assertNotIn(4, fold['test_rows'])

    def test_unsorted_or_ambiguous_time_rejected(self):
        for times in (list(reversed(self.frame.date)), list(range(12)), ['not-a-date'] * 12,
                      ['01/02/2024'] * 12, [''] * 12):
            with self.subTest(times=times), self.assertRaises(ValueError):
                validation_splits(self.frame.assign(date=times), self.config)

    def test_datetime_dtype_and_timezone_are_supported(self):
        self.frame['date'] = pd.to_datetime(self.frame.date).dt.tz_localize('Asia/Shanghai')
        result = self.run_backtest()
        self.assertEqual(result['folds'][0]['cutoff'], '2024-01-03T16:00:00+00:00')

    def test_optional_solver_missing_does_not_break_prediction_tools(self):
        original = builtins.__import__

        def blocked(name, *args, **kwargs):
            if name == 'scipy' or name.startswith('scipy.'):
                raise ImportError('simulated optional dependency absence')
            return original(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=blocked):
            self.assertEqual(self.run_backtest()['status'], 'PASS')
            with self.assertRaisesRegex(RuntimeError, 'optional'):
                solve_linear_problem({'c': [1], 'bounds': [[0, 1]]}, metric_id='x', unit='1')

    def test_invalid_configuration_rejected(self):
        for changes in ({'test_size': 0}, {'test_size': True}, {'min_train_size': 20}, {'step': 1},
                        {'gap': -1}, {'window': 0}, {'time_column': 'missing'}, {'typo': 1}, {'kind': 'random'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validation_splits(self.frame, {**self.config, **changes})

    def test_group_holdout_never_mixes_entities(self):
        fold = validation_splits(self.frame, {'kind': 'group_holdout', 'group_column': 'group', 'test_groups': ['b']})[0]
        self.assertEqual(fold['test_rows'], [4, 5, 6, 7])
        self.assertTrue(set(self.frame.iloc[fold['train_rows']].group).isdisjoint(self.frame.iloc[fold['test_rows']].group))

    def test_bad_group_contracts_rejected(self):
        for groups in ([], ['missing'], ['a', 'a'], ['a', 'b', 'c'], [True]):
            with self.subTest(groups=groups), self.assertRaises(ValueError):
                validation_splits(self.frame, {'kind': 'group_holdout', 'group_column': 'group', 'test_groups': groups})
        self.frame.loc[0, 'group'] = None
        with self.assertRaises(ValueError):
            validation_splits(self.frame, {'kind': 'group_holdout', 'group_column': 'group', 'test_groups': ['b']})

    def test_known_linear_relation_and_naive_reference(self):
        report = self.run_backtest()
        self.assertEqual(report['status'], 'PASS')
        for f in report['folds']:
            self.assertAlmostEqual(f['fit']['coefficients']['x'], 2)
            self.assertAlmostEqual(f['fit']['intercept'], 3)
        naive = [m for m in report['metrics'] if m['metric_name'] == 'last_value_RMSE']
        self.assertAlmostEqual(naive[0]['value'], np.sqrt(10))
        pooled = next(m for m in report['metrics'] if m['metric_key'] == 'pooled.RMSE')
        self.assertLess(pooled['value'], 1e-10)
        json.dumps(report, allow_nan=False)

    def test_last_fold_test_values_do_not_change_its_training(self):
        first = self.run_backtest()['folds'][-1]['fit']
        self.frame.loc[10:, 'x'] = [1000, 2000]
        self.frame.loc[10:, 'y'] = [-999, -888]
        second = self.run_backtest()['folds'][-1]['fit']
        self.assertEqual(first['coefficients'], second['coefficients'])
        self.assertEqual(first['preprocessing'], second['preprocessing'])

    def test_future_features_and_delayed_labels_rejected(self):
        self.frame['available'] = self.frame.date
        with self.assertRaisesRegex(ValueError, 'unavailable'):
            self.run_backtest(feature_availability={'x': 'available'})
        self.frame['available'] = '2023-12-01'
        self.run_backtest(feature_availability={'x': 'available'})
        self.frame['available'] = '2025-01-01'
        with self.assertRaisesRegex(ValueError, 'labels unavailable'):
            self.run_backtest(target_available_at='available')

    def test_availability_and_units_must_be_explicit(self):
        for changes in ({'unit': ''}, {'feature_availability': {}}, {'features': ['y']}, {'features': ['x', 'x']}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.run_backtest(**changes)

    def test_group_regression_and_panel_scope(self):
        report = self.run_backtest(validation={'kind': 'group_holdout', 'group_column': 'group', 'test_groups': ['c']})
        self.assertEqual(report['metrics'][-1]['n_test'], 4)
        self.assertEqual({r['row_index'] for r in report['predictions']}, {8, 9, 10, 11})
        self.frame.loc[4, 'date'] = self.frame.loc[3, 'date']
        with self.assertRaisesRegex(ValueError, 'one series'):
            self.run_backtest()

    def test_dataframe_index_not_used_as_row_identity(self):
        expected = self.run_backtest()
        self.frame.index = [999] * len(self.frame)
        actual = self.run_backtest()
        self.assertEqual(actual['predictions'], expected['predictions'])
        self.assertEqual(actual['input_hashes'], expected['input_hashes'])


@unittest.skipUnless(HAS_SCIPY, 'optional scipy not installed')
class SolverTests(unittest.TestCase):
    def setUp(self):
        self.problem = {'c': [3, 1], 'bounds': [[0, 2], [0, 2]], 'A_ub': [[1, 1]], 'b_ub': [3],
                        'integer_indices': [0, 1], 'sense': 'max'}

    def solve(self, **changes):
        return solve_linear_problem({**self.problem, **changes}, metric_id='Q1.objective', unit='kg')

    def test_integer_optimum_independently_enumerated(self):
        expected = max(3 * x + y for x, y in itertools.product(range(3), repeat=2) if x + y <= 3)
        report = self.solve()
        self.assertEqual(report['objective_value'], expected)
        self.assertTrue(report['optimality_verified'])
        self.assertEqual(report['best_bound'], expected)
        self.assertEqual(report['solver_status'], 'OPTIMAL')
        self.assertEqual(validate_solver_report(report)['status'], 'PASS')
        json.dumps(report, allow_nan=False)

    def test_minimization_signs_and_continuous_variables(self):
        report = self.solve(c=[-3, -1], sense='min')
        self.assertEqual(report['objective_value'], -7)
        self.assertEqual(report['best_bound'], -7)
        continuous = self.solve(integer_indices=[], A_eq=[[1, 0]], b_eq=[1.5])
        self.assertAlmostEqual(continuous['objective_value'], 6)
        self.assertTrue(continuous['feasibility_verified'])

    def test_infeasible_and_unbounded_are_failed_records(self):
        infeasible = self.solve(b_ub=[-1])
        self.assertEqual(infeasible['solver_status'], 'INFEASIBLE')
        self.assertEqual(infeasible['status'], 'FAIL')
        self.assertIsNone(infeasible['objective_value'])
        unbounded = self.solve(integer_indices=[], bounds=[[0, None], [0, None]], A_ub=None, b_ub=None)
        self.assertEqual(unbounded['solver_status'], 'UNBOUNDED')
        self.assertFalse(unbounded['optimality_verified'])

    def test_limit_with_incumbent_is_not_optimal(self):
        from scipy.optimize import OptimizeResult
        fake = OptimizeResult(status=1, message='time limit', x=np.array([1., 1.]), fun=-4.,
                              mip_dual_bound=-7., mip_gap=.75)
        with patch('scipy.optimize.milp', return_value=fake):
            report = self.solve()
        self.assertEqual(report['solver_status'], 'FEASIBLE')
        self.assertEqual(report['absolute_gap'], 3)
        self.assertFalse(report['optimality_verified'])
        report['optimality_verified'] = True
        with self.assertRaises(ValueError):
            validate_solver_report(report)

    def test_positive_gap_success_does_not_prove_optimality(self):
        from scipy.optimize import OptimizeResult
        fake = OptimizeResult(status=0, message='gap tolerance reached', x=np.array([1., 1.]), fun=-4.,
                              mip_dual_bound=-7., mip_gap=.75)
        with patch('scipy.optimize.milp', return_value=fake):
            report = self.solve()
        self.assertEqual(report['solver_status'], 'FEASIBLE')

    def test_unknown_or_bad_incumbent_never_passes(self):
        from scipy.optimize import OptimizeResult
        for fake in (OptimizeResult(status=1, message='limit', x=None, fun=None),
                     OptimizeResult(status=0, message='inconsistent', x=np.array([2., 2.]), fun=-8.)):
            with patch('scipy.optimize.milp', return_value=fake):
                report = self.solve()
            self.assertEqual(report['status'], 'FAIL')

    def test_changed_problem_verdict_and_objective_rejected(self):
        original = self.solve()
        for field, value in [('objective_value', 999), ('checks', []), ('best_bound', 99), ('status', 'FAIL')]:
            report = copy.deepcopy(original)
            report[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_solver_report(report)
        report = copy.deepcopy(original)
        report['problem']['c'][0] = 99
        with self.assertRaisesRegex(ValueError, 'hash'):
            validate_solver_report(report)

    def test_corrupted_incumbent_and_wrong_bound_cannot_keep_pass(self):
        report = self.solve()
        report['solver']['result']['x'] = [2, 2]
        with self.assertRaises(ValueError):
            validate_solver_report(report)
        report = self.solve()
        report['solver']['result']['best_bound'] = 6
        with self.assertRaisesRegex(ValueError, 'wrong side'):
            validate_solver_report(report)

    def test_bare_boolean_cannot_certify_optimum(self):
        with self.assertRaises(ValueError):
            validate_solver_report({'status': 'PASS', 'optimality_verified': True})

    def test_invalid_problem_rejected_before_solving(self):
        for changes in ({'c': [1]}, {'b_ub': None}, {'sense': 'maximize'}, {'integer_indices': [9]},
                        {'unknown_option': True}, {'bounds': [[2, 1], [0, 2]]}):
            with self.subTest(changes=changes), self.assertRaises((ValueError, TypeError)):
                self.solve(**changes)


if __name__ == '__main__':
    unittest.main()
