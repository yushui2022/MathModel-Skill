"""Optional SciPy/HiGHS adapter with independently recomputed primal checks.

Reports are reproducibility records, not cryptographic or formal optimality proofs.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone

import numpy as np

from modeling_tools import verify_linear_solution


def _digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, allow_nan=False,
                                     separators=(',', ':')).encode()).hexdigest()


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('Expected a finite number')
    return float(value)


def _problem(problem):
    if not isinstance(problem, dict) or set(problem) - {
        'c', 'bounds', 'A_ub', 'b_ub', 'A_eq', 'b_eq', 'integer_indices', 'sense'
    }:
        raise ValueError('Declare only supported linear problem fields')
    value = json.loads(json.dumps(problem, allow_nan=False))
    sense = value.pop('sense', 'min')
    if sense not in ('min', 'max'):
        raise ValueError('sense must be min or max')
    # Validate dimensions, bounds and integer indices before calling the solver.
    verify_linear_solution(x=[0.] * len(value.get('c', [])), **value)
    return value, sense


def _assessment(report):
    problem, sense = _problem(report['problem'])
    if report.get('input_hashes', {}).get('linear_problem') != _digest(report['problem']):
        raise ValueError('Linear problem hash changed')
    solver = report['solver']
    if solver.get('name') != 'scipy.optimize.milp/HiGHS' or not isinstance(solver.get('version'), str) or not solver['version']:
        raise ValueError('Unsupported or unversioned solver evidence')
    options = solver['options']
    if _number(options['time_limit']) <= 0 or _number(options['mip_rel_gap']) < 0:
        raise ValueError('Invalid solver limits')
    raw = solver['result']
    code = raw.get('status')
    if type(code) is not int or code not in range(5):
        raise ValueError('Invalid solver status')
    atol, rtol = _number(report['tolerances']['atol']), _number(report['tolerances']['rtol'])
    if min(atol, rtol) < 0 or atol > 1e-5 or rtol > 1e-7:
        raise ValueError('Verification tolerances exceed supported limits')
    verified, objective = None, None
    x = raw.get('x')
    if x is not None:
        objective = _number(raw.get('objective'))
        verified = verify_linear_solution(**problem, x=x, reported_objective=objective, atol=atol, rtol=rtol)
        objective = verified['objective']
    feasible = verified is not None and verified['status'] == 'PASS' and code in (0, 1)
    bound, gap = raw.get('best_bound'), raw.get('relative_gap')
    for value in (bound, gap):
        if value is not None:
            _number(value)
    if gap is not None and gap < 0:
        raise ValueError('Negative relative gap')
    close_bound = False
    absolute_gap = None
    if objective is not None and bound is not None:
        absolute_gap = (objective - bound) if sense == 'min' else (bound - objective)
        tolerance = atol + rtol * max(abs(objective), abs(bound))
        if absolute_gap < -tolerance:
            raise ValueError('Best bound is on the wrong side of the incumbent')
        close_bound = abs(absolute_gap) <= tolerance
    integer = bool(problem.get('integer_indices'))
    optimal = feasible and code == 0 and (not integer or (close_bound and gap is not None and gap <= 1e-7))
    status = ('OPTIMAL' if optimal else 'FEASIBLE') if feasible else {
        0: 'ERROR', 1: 'UNKNOWN', 2: 'INFEASIBLE', 3: 'UNBOUNDED', 4: 'ERROR'
    }[code]
    return {'status': 'PASS' if feasible else 'FAIL', 'solver_status': status,
            'feasibility_verified': bool(feasible), 'optimality_verified': bool(optimal),
            'objective_value': objective, 'best_bound': bound, 'absolute_gap': absolute_gap,
            'relative_gap': gap, 'checks': verified['checks'] if verified else []}


def validate_solver_report(report):
    """Recompute numerical checks; do not accept a self-declared boolean verdict."""
    try:
        if report.get('schema_version') != 'solver-evidence/1' or report.get('generated_by') != 'solver_evidence.solve_linear_problem':
            raise ValueError('Missing supported solver evidence; a boolean is not an optimality record')
        expected = _assessment(report)
        if any(report.get(key) != value for key, value in expected.items()):
            raise ValueError('Solver report verdict disagrees with recomputed evidence')
        return expected
    except (KeyError, TypeError, OverflowError) as exc:
        raise ValueError('Malformed solver evidence') from exc


def solve_linear_problem(problem, *, metric_id, unit, time_limit=60., mip_rel_gap=0.,
                         atol=1e-7, rtol=1e-9):
    """Solve a declared linear minimization/maximization; never guess constraints.

    Requires optional scipy>=1.11,<2. An unsuccessful solve returns a FAIL record,
    not invented values. Positive MIP gaps never establish exact optimality.
    """
    if not isinstance(metric_id, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]+', metric_id):
        raise ValueError('Declare a stable metric_id')
    if not isinstance(unit, str) or not unit.strip():
        raise ValueError('Declare an objective unit')
    if _number(time_limit) <= 0 or _number(mip_rel_gap) < 0:
        raise ValueError('Invalid solver limits')
    if not 0 <= _number(atol) <= 1e-5 or not 0 <= _number(rtol) <= 1e-7:
        raise ValueError('Invalid verification tolerances')
    data, sense = _problem(problem)
    try:
        import scipy
        from scipy.optimize import Bounds, LinearConstraint, milp
    except ImportError as exc:
        raise RuntimeError('Optimization requires the optional requirements-modeling.txt dependencies') from exc
    sign = 1 if sense == 'min' else -1
    constraints = []
    if data.get('A_ub') is not None:
        constraints.append(LinearConstraint(data['A_ub'], -np.inf, data['b_ub']))
    if data.get('A_eq') is not None:
        constraints.append(LinearConstraint(data['A_eq'], data['b_eq'], data['b_eq']))
    bounds = Bounds([p[0] if p[0] is not None else -np.inf for p in data['bounds']],
                    [p[1] if p[1] is not None else np.inf for p in data['bounds']])
    integrality = np.zeros(len(data['c']), dtype=int)
    integrality[data.get('integer_indices', [])] = 1
    options = {'time_limit': float(time_limit), 'mip_rel_gap': float(mip_rel_gap)}
    result = milp(np.asarray(data['c']) * sign, integrality=integrality,
                  bounds=bounds, constraints=constraints, options=options)

    def finite_or_none(value):
        return float(value) if value is not None and np.isfinite(value) else None

    bound = finite_or_none(result.get('mip_dual_bound'))
    objective = finite_or_none(result.get('fun'))
    report = {'schema_version': 'solver-evidence/1', 'generated_by': 'solver_evidence.solve_linear_problem',
              'generated_at': datetime.now(timezone.utc).isoformat(), 'metric_id': metric_id, 'unit': unit,
              'problem': {**data, 'sense': sense}, 'tolerances': {'atol': atol, 'rtol': rtol},
              'solver': {'name': 'scipy.optimize.milp/HiGHS', 'version': scipy.__version__, 'options': options,
                         'result': {'status': int(result.status), 'message': str(result.message),
                                    'x': result.x.tolist() if result.x is not None else None,
                                    'objective': objective * sign if objective is not None else None,
                                    'best_bound': bound * sign if bound is not None else None,
                                    'relative_gap': finite_or_none(result.get('mip_gap'))}},
              'acceptance_scope': 'Declared linear model and solver tolerances, not formal proof or correctness of problem formulation'}
    report['input_hashes'] = {'linear_problem': _digest(report['problem'])}
    report.update(_assessment(report))
    return report
