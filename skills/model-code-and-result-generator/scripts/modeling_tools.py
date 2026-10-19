"""Small, explicit numerical tools. No model selection or official-gate bypass."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Installed skills share the data helper; generated contest code gets a copy.
if not Path(__file__).with_name('data_inputs.py').is_file():
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'data-cleaning-and-visualization/scripts'))
from data_inputs import current_cleaning_report, project_path


def load_current_dataset(root: Path, *, source: str | None = None,
                         sheet: str | None = None) -> tuple[pd.DataFrame, Path]:
    """Select one current, hashed dataset by original source and worksheet."""
    root = root.resolve()
    report = current_cleaning_report(root)
    requested = project_path(root, source) if source is not None else None
    matches = [item for item in report['datasets']
               if (requested is None or project_path(root, item['path']) == requested)
               and (sheet is None or item.get('sheet') == sheet)]
    if len(matches) != 1:
        raise ValueError('Select exactly one current dataset using data_source and sheet; '
                         f'found {len(matches)} matches')
    path = project_path(root, matches[0]['cleaned_output'])
    # Preserve identifier spelling and missing-token meaning until fields are bound.
    frame = pd.read_csv(path, encoding='utf-8-sig', dtype=str, keep_default_na=False)
    if frame.empty or list(frame.columns) != matches[0].get('columns'):
        raise ValueError('Selected dataset is empty or its columns disagree with the cleaning report')
    return frame, path


def _rows(values, size: int, name: str) -> np.ndarray:
    values = list(values)
    if not values or any(type(i) is not int or not 0 <= i < size for i in values):
        raise ValueError(f'{name} must contain valid zero-based positional row indices')
    if len(set(values)) != len(values):
        raise ValueError(f'{name} contains duplicate row indices')
    return np.asarray(values, dtype=int)


def _numeric(frame: pd.DataFrame, columns: list[str]) -> np.ndarray:
    selected = frame[columns].replace(r'^\s*$', np.nan, regex=True)
    try:
        values = selected.apply(pd.to_numeric, errors='raise').to_numpy(dtype=float)
    except (ValueError, TypeError) as exc:
        raise ValueError('Selected fields must be numeric; declare missing tokens explicitly upstream') from exc
    if np.isinf(values).any():
        raise ValueError('Infinite input values are not allowed')
    return values


def regression_baseline(frame: pd.DataFrame, *, target: str, features: list[str],
                        train_rows: list[int], test_rows: list[int]) -> dict:
    """Fit train-only preprocessing + OLS; evaluate against a train-mean baseline.

    Row indices are positional, not DataFrame labels. The caller must choose a
    task-appropriate temporal/group split and features available at prediction time.
    """
    if not isinstance(target, str) or not isinstance(features, list) or not features:
        raise ValueError('Explicit target and nonempty feature names are required')
    if any(not isinstance(c, str) for c in features) or len(set(features)) != len(features):
        raise ValueError('Feature names must be unique strings')
    if target in features or not frame.columns.is_unique:
        raise ValueError('Target leakage or duplicate column names')
    if any(c not in frame.columns for c in [target, *features]):
        raise ValueError('A declared target or feature is missing')
    train, test = _rows(train_rows, len(frame), 'train_rows'), _rows(test_rows, len(frame), 'test_rows')
    if set(train) & set(test):
        raise ValueError('Training and test rows must be disjoint')
    if len(train) < max(2, len(features) + 1):
        raise ValueError('Too few training rows for the declared linear model')
    x, y = _numeric(frame, features), _numeric(frame, [target]).ravel()
    if np.isnan(y[np.r_[train, test]]).any():
        raise ValueError('Observed targets are required; never impute evaluation labels')
    train_x = x[train]
    if np.isnan(train_x).all(axis=0).any():
        raise ValueError('A feature is entirely missing in the training set')
    medians = np.nanmedian(train_x, axis=0)
    train_x = np.where(np.isnan(train_x), medians, train_x)
    test_x = np.where(np.isnan(x[test]), medians, x[test])
    center, scale = train_x.mean(axis=0), train_x.std(axis=0)
    scale = np.where(scale == 0, 1.0, scale)
    design = np.column_stack([np.ones(len(train)), (train_x - center) / scale])
    test_design = np.column_stack([np.ones(len(test)), (test_x - center) / scale])
    if not np.isfinite(design).all() or not np.isfinite(test_design).all():
        raise ValueError('Numeric overflow during preprocessing')
    coefficients, _, rank, _ = np.linalg.lstsq(design, y[train], rcond=None)
    predicted = test_design @ coefficients
    residual = y[test] - predicted
    baseline = np.full(len(test), y[train].mean())
    metrics = {'RMSE': float(np.sqrt(np.mean(residual ** 2))),
               'MAE': float(np.mean(np.abs(residual))),
               'baseline_RMSE': float(np.sqrt(np.mean((y[test] - baseline) ** 2)))}
    slope = coefficients[1:] / scale
    intercept = float(coefficients[0] - center @ slope)
    if not all(np.isfinite(v) for v in [*metrics.values(), intercept, *slope, *predicted]):
        raise ValueError('Non-finite regression outputs')
    return {
        'status': 'computed_baseline', 'method': 'OLS_with_train_only_median_and_scaling',
        'target': target, 'features': features, 'train_rows': train.tolist(), 'test_rows': test.tolist(),
        'n_train': len(train), 'n_test': len(test), 'metrics': metrics,
        'preprocessing': {'medians': dict(zip(features, medians.tolist())),
                          'centers': dict(zip(features, center.tolist())),
                          'scales': dict(zip(features, scale.tolist()))},
        'coefficients': dict(zip(features, slope.tolist())), 'intercept': intercept,
        'predictions': [{'row_index': int(i), 'actual': float(y[i]), 'predicted': float(p),
                         'residual': float(r), 'baseline_prediction': float(b)}
                        for i, p, r, b in zip(test, predicted, residual, baseline)],
        'warnings': ['Rank-deficient design; coefficients are not uniquely identifiable']
                    if rank < design.shape[1] else [],
        'acceptance_scope': 'Held-out numeric baseline only; task suitability requires review',
    }


def _finite_array(value, name: str, ndim: int) -> np.ndarray:
    try:
        array = np.asarray(value, dtype=float)
    except (ValueError, TypeError) as exc:
        raise ValueError(f'{name} must be numeric') from exc
    if array.ndim != ndim or not np.isfinite(array).all():
        raise ValueError(f'{name} has invalid dimensions or non-finite values')
    return array


def verify_linear_solution(*, c, x, bounds, A_ub=None, b_ub=None, A_eq=None, b_eq=None,
                           integer_indices=(), reported_objective=None,
                           atol: float = 1e-7, rtol: float = 1e-9) -> dict:
    """Recompute c @ x, A_ub @ x <= b_ub, equalities, bounds and integrality.

    bounds is explicit: each (lower, upper) endpoint may be None for no bound.
    PASS proves only the supplied feasibility/objective checks, never optimality.
    """
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not np.isfinite(v) or v < 0
           for v in (atol, rtol)):
        raise ValueError('Tolerances must be finite nonnegative numbers')
    c, x = _finite_array(c, 'c', 1), _finite_array(x, 'x', 1)
    if len(x) == 0 or c.shape != x.shape:
        raise ValueError('c and x must have the same nonzero length')
    bounds = list(bounds)
    if len(bounds) != len(x):
        raise ValueError('Declare one bound pair per decision variable')
    checks = []

    def check(name, lhs, rhs, equality=False, relative=True):
        if not np.isfinite(lhs) or not np.isfinite(rhs):
            raise ValueError(f'Numeric overflow in {name}')
        tolerance = atol + (rtol * max(abs(lhs), abs(rhs)) if relative else 0)
        violation = abs(lhs - rhs) if equality else max(0.0, lhs - rhs)
        if not np.isfinite(violation) or not np.isfinite(tolerance):
            raise ValueError(f'Numeric overflow in {name}')
        checks.append({'constraint': name, 'lhs': float(lhs), 'rhs': float(rhs),
                       'violation': float(violation), 'tolerance': float(tolerance),
                       'passed': bool(violation <= tolerance)})

    for label, matrix, vector, equality in [('inequality', A_ub, b_ub, False),
                                            ('equality', A_eq, b_eq, True)]:
        if matrix is None and vector is None:
            continue
        if matrix is None or vector is None:
            raise ValueError(f'{label} requires both matrix and right-hand side')
        matrix, vector = _finite_array(matrix, label, 2), _finite_array(vector, label, 1)
        if matrix.shape != (len(vector), len(x)):
            raise ValueError(f'{label} dimensions disagree')
        for i, (lhs, rhs) in enumerate(zip(matrix @ x, vector)):
            check(f'{label}[{i}]', lhs, rhs, equality)
    for i, pair in enumerate(bounds):
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError('Each bound must be a (lower, upper) pair')
        lower, upper = pair
        for value in pair:
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                                      or not np.isfinite(value)):
                raise ValueError('Use finite bound values or None')
        if lower is not None and upper is not None and lower > upper:
            raise ValueError('Lower bound exceeds upper bound')
        if lower is not None:
            check(f'lower_bound[{i}]', lower, x[i])
        if upper is not None:
            check(f'upper_bound[{i}]', x[i], upper)
    indices = list(integer_indices)
    if any(type(i) is not int or not 0 <= i < len(x) for i in indices) or len(set(indices)) != len(indices):
        raise ValueError('Invalid or duplicate integer variable indices')
    for i in indices:
        check(f'integer[{i}]', x[i], np.rint(x[i]), equality=True, relative=False)
    feasible = all(item['passed'] for item in checks)
    objective = float(c @ x)
    if not np.isfinite(objective):
        raise ValueError('Non-finite objective')
    if reported_objective is not None:
        reported = _finite_array(reported_objective, 'reported_objective', 0)
        check('reported_objective', objective, float(reported), equality=True)
    return {'status': 'PASS' if all(item['passed'] for item in checks) else 'FAIL',
            'feasible': feasible, 'objective': objective, 'checks': checks,
            'optimality_verified': False, 'acceptance_scope': 'Declared linear constraints and objective only'}
