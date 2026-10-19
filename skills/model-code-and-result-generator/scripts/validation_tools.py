"""Explicit holdouts and OLS backtests; no automatic choice of validation design."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from modeling_tools import regression_baseline


def _integer(value, name, minimum=1):
    if type(value) is not int or value < minimum:
        raise ValueError(f'{name} must be an integer >= {minimum}')
    return value


def _column(frame, name):
    if not frame.columns.is_unique or name not in frame or frame.empty:
        raise ValueError(f'Missing column, duplicate columns or empty dataset: {name}')
    values = frame[name]
    if values.isna().any() or values.astype(str).str.strip().eq('').any():
        raise ValueError(f'Missing values in validation column: {name}')
    return values.reset_index(drop=True)


def _times(frame, column):
    # Dates are explicit. Numeric timestamps require a caller-supplied conversion.
    values = _column(frame, column).astype(str)
    if not values.str.fullmatch(r'\d{4}-\d{2}-\d{2}(?:[T ].+)?').all():
        raise ValueError('Use explicit ISO dates, not numeric/ambiguous timestamps')
    try:
        return pd.to_datetime(values, format='ISO8601', errors='raise', utc=True)
    except (ValueError, TypeError) as exc:
        raise ValueError(f'Invalid timestamp column: {column}') from exc


def validation_splits(frame, config):
    """Return positional folds. Temporal sizes count distinct timestamps, not rows."""
    if not isinstance(config, dict):
        raise ValueError('validation must be an explicit object')
    kind = config.get('kind')
    if kind == 'group_holdout':
        allowed = {'kind', 'group_column', 'test_groups'}
        if set(config) - allowed:
            raise ValueError('Unknown group validation fields')
        groups = _column(frame, config.get('group_column'))
        selected = config.get('test_groups')
        if not isinstance(selected, list) or not selected:
            raise ValueError('Declare nonempty test_groups')
        if any(not isinstance(g, (str, int)) or isinstance(g, bool) for g in selected):
            raise ValueError('Group IDs must be strings or integers matching the data')
        if len(set(selected)) != len(selected) or not set(selected) <= set(groups):
            raise ValueError('Unknown or duplicate test groups')
        test = np.flatnonzero(groups.isin(selected)).tolist()
        train = np.flatnonzero(~groups.isin(selected)).tolist()
        if not train or not test:
            raise ValueError('Both training and test groups are required')
        return [{'fold_id': 'fold-001', 'train_rows': train, 'test_rows': test,
                 'test_groups': selected, 'cutoff': None}]
    if kind not in ('temporal_holdout', 'rolling_origin'):
        raise ValueError('Choose temporal_holdout, rolling_origin or group_holdout')
    allowed = {'kind', 'time_column', 'test_size', 'gap'}
    if kind == 'rolling_origin':
        allowed |= {'min_train_size', 'step', 'window'}
    if set(config) - allowed:
        raise ValueError('Unknown temporal validation fields')
    times = _times(frame, config.get('time_column'))
    if not times.is_monotonic_increasing:
        raise ValueError('Sort the dataset by time explicitly before validation')
    unique = times.drop_duplicates().reset_index(drop=True)
    size = _integer(config.get('test_size'), 'test_size')
    gap = _integer(config.get('gap', 0), 'gap', 0)
    start = len(unique) - gap - size if kind == 'temporal_holdout' else config.get('min_train_size')
    start = _integer(start, 'min_train_size')
    step = _integer(config.get('step', size), 'step')
    if step < size:
        raise ValueError('Overlapping test windows are not supported; step must be >= test_size')
    window = config.get('window')
    if window is not None:
        _integer(window, 'window')
    folds = []
    for stop in range(start, len(unique) - gap - size + 1, step):
        train_times = unique[max(0, stop - window) if window else 0:stop]
        test_times = unique[stop + gap:stop + gap + size]
        folds.append({'fold_id': f'fold-{len(folds) + 1:03d}',
                      'train_rows': np.flatnonzero(times.isin(train_times)).tolist(),
                      'test_rows': np.flatnonzero(times.isin(test_times)).tolist(),
                      'cutoff': train_times.iloc[-1].isoformat(),
                      'test_start': test_times.iloc[0].isoformat(),
                      'test_end': test_times.iloc[-1].isoformat()})
    if not folds:
        raise ValueError('Not enough timestamps for the requested validation')
    return folds


def backtest_regression(frame, *, target, features, validation, unit, feature_availability,
                        target_available_at=None):
    """Compare train-only OLS and simple baselines on identical held-out samples.

    feature_availability maps each feature to 'known_in_advance' or an ISO-date
    availability column. It is a declared assumption, not proof of data provenance.
    """
    if not isinstance(unit, str) or not unit.strip():
        raise ValueError('Declare the target unit (use 1 for dimensionless quantities)')
    if not isinstance(features, list) or not features or len(set(features)) != len(features):
        raise ValueError('Declare unique feature names')
    if not isinstance(feature_availability, dict) or set(feature_availability) != set(features):
        raise ValueError('Declare availability for every feature')
    folds = validation_splits(frame, validation)
    temporal = validation['kind'] != 'group_holdout'
    if not temporal and (target_available_at is not None or
                         any(v != 'known_in_advance' for v in feature_availability.values())):
        raise ValueError('Group holdout has no forecast cutoff; use known_in_advance and review its meaning')
    results, predictions, metrics = [], [], []
    for fold in folds:
        if temporal:
            cutoff = pd.Timestamp(fold['cutoff'])
            for feature, availability in feature_availability.items():
                if availability != 'known_in_advance':
                    available = _times(frame, availability)
                    if (available.iloc[fold['train_rows'] + fold['test_rows']] > cutoff).any():
                        raise ValueError(f'Feature unavailable at forecast origin: {feature}/{fold["fold_id"]}')
            if target_available_at is not None:
                available = _times(frame, target_available_at)
                if (available.iloc[fold['train_rows']] > cutoff).any():
                    raise ValueError('Training labels unavailable at forecast origin')
        fit = regression_baseline(frame, target=target, features=features,
                                  train_rows=fold['train_rows'], test_rows=fold['test_rows'])
        rows = [{**p, 'fold_id': fold['fold_id']} for p in fit['predictions']]
        values = dict(fit['metrics'])
        if temporal:
            times = _times(frame, validation['time_column'])
            origin_rows = [i for i in fold['train_rows'] if times.iloc[i] == pd.Timestamp(fold['cutoff'])]
            # Pooled panel data need an entity-specific naive baseline, never a cross-entity last value.
            if len(origin_rows) != 1 or times.duplicated().any():
                raise ValueError('Backtest supports one series; split panel data by entity explicitly')
            last = float(frame.iloc[origin_rows[-1]][target])
            for row in rows:
                row['last_value_prediction'] = last
            values['last_value_RMSE'] = float(np.sqrt(np.mean([(p['actual'] - last) ** 2 for p in rows])))
        if not all(np.isfinite(v) for v in values.values()):
            raise ValueError('Nonfinite backtest metric')
        scope = (f'{fold["fold_id"]} [{fold["test_start"]}, {fold["test_end"]}]'
                 if temporal else f'{fold["fold_id"]} groups={fold["test_groups"]!r}')
        for name, value in values.items():
            metrics.append({'metric_key': f'{fold["fold_id"]}.{name}', 'metric_name': name,
                            'value': value, 'unit': unit, 'split': 'test', 'sample_scope': scope,
                            'fold_id': fold['fold_id'], 'n_test': len(rows)})
        predictions.extend(rows)
        results.append({**fold, 'fit': fit})
    # Pooled errors weight samples, rather than averaging per-fold RMSEs.
    for name, key in [('RMSE', 'predicted'), ('baseline_RMSE', 'baseline_prediction')]:
        value = float(np.sqrt(np.mean([(p['actual'] - p[key]) ** 2 for p in predictions])))
        if not np.isfinite(value):
            raise ValueError('Nonfinite pooled error')
        metrics.append({'metric_key': f'pooled.{name}', 'metric_name': name, 'value': value,
                        'unit': unit, 'split': 'test', 'sample_scope': 'pooled disjoint held-out samples',
                        'fold_id': 'pooled', 'n_test': len(predictions)})
    return {'schema_version': '1', 'generated_at': datetime.now(timezone.utc).isoformat(),
            'generated_by': 'validation_tools.backtest_regression', 'status': 'PASS',
            'environment': {'numpy': np.__version__, 'pandas': pd.__version__},
            'input_hashes': {'dataframe_csv': hashlib.sha256(frame.to_csv(index=False, lineterminator='\n').encode()).hexdigest()},
            'validation': validation, 'feature_availability': feature_availability,
            'target_available_at': target_available_at, 'folds': results,
            'predictions': predictions, 'metrics': metrics,
            'acceptance_scope': 'Declared split and availability only; not task suitability or an untouched final test set'}
