"""Independent, bounded LP/MILP solution checking; no solver imports or execution.

Numbers are evaluated as exact rational representations of their JSON decimal values.
This validates the declared mathematical specification, not its fit to natural language.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path

SCHEMA_VERSION = "1.0"
PROFILE = "linear-v1"
TOLERANCES = {"feasibility_absolute": 1e-7, "integrality_absolute": 1e-7,
              "objective_absolute": 1e-7, "objective_relative": 1e-9}


class ContractError(ValueError):
    pass


def load_json(path: Path) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ContractError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject(value):
        raise ContractError(f"non-finite JSON number: {value}")

    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs,
                       parse_constant=reject)
    if type(value) is not dict:
        raise ContractError("JSON root must be an object")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fields(value, required: set[str], location: str) -> dict:
    if type(value) is not dict or set(value) != required:
        actual = set(value) if type(value) is dict else set()
        raise ContractError(f"{location}: exact fields required; missing={sorted(required-actual)}, extra={sorted(actual-required)}")
    return value


def identifier(value, location: str) -> str:
    if type(value) is not str or not value.strip() or len(value) > 200:
        raise ContractError(f"{location}: non-empty string of at most 200 characters required")
    return value


def number(value, location: str) -> Fraction:
    if type(value) not in (int, float) or (type(value) is float and not math.isfinite(value)):
        raise ContractError(f"{location}: finite JSON number required (not boolean/string)")
    return Fraction(str(value))


def hash_value(value, location: str) -> str:
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ContractError(f"{location}: lowercase SHA-256 required")
    return value


def rows(value, location: str, *, allow_empty: bool = False) -> list:
    if type(value) is not list or (not value and not allow_empty) or len(value) > 10000:
        raise ContractError(f"{location}: array with {'0' if allow_empty else '1'}..10000 entries required")
    return value


def coefficients(value, variable_ids: set[str], location: str) -> dict[str, Fraction]:
    if type(value) is not dict or not set(value) <= variable_ids:
        raise ContractError(f"{location}: coefficients reference an undeclared variable")
    return {key: number(item, f"{location}/{key}") for key, item in value.items()}


def validate_spec(spec: dict) -> dict:
    fields(spec, {"schema_version", "profile", "problem_id", "subproblem_id", "route_id", "model_class",
                  "input_hashes", "variables", "objective", "constraints", "tolerances"}, "spec")
    if spec["schema_version"] != SCHEMA_VERSION or spec["profile"] != PROFILE:
        raise ContractError("unsupported optimization schema/profile")
    for key in ("problem_id", "subproblem_id", "route_id"):
        identifier(spec[key], key)
    if spec["model_class"] not in ("LP", "MILP"):
        raise ContractError("model_class must be LP or MILP")
    if type(spec["input_hashes"]) is not dict or not spec["input_hashes"]:
        raise ContractError("spec requires non-empty frozen input_hashes")
    for key, value in spec["input_hashes"].items():
        identifier(key, "input path")
        hash_value(value, f"input_hashes/{key}")
    fields(spec["tolerances"], set(TOLERANCES), "tolerances")
    for key, value in TOLERANCES.items():
        if number(spec["tolerances"][key], key) != number(value, key):
            raise ContractError(f"{PROFILE} fixes {key}={value}; a changed tolerance needs a new profile")
    variables = {}
    for var in rows(spec["variables"], "variables"):
        fields(var, {"id", "unit", "domain", "lower", "upper"}, "variable")
        key = identifier(var["id"], "variable id")
        identifier(var["unit"], f"{key}/unit")
        if key in variables or var["domain"] not in ("continuous", "integer", "binary"):
            raise ContractError(f"{key}: duplicate variable or unknown domain")
        lower = None if var["lower"] is None else number(var["lower"], f"{key}/lower")
        upper = None if var["upper"] is None else number(var["upper"], f"{key}/upper")
        if lower is not None and upper is not None and lower > upper:
            raise ContractError(f"{key}: lower bound exceeds upper bound")
        if var["domain"] == "binary" and (lower != 0 or upper != 1):
            raise ContractError(f"{key}: binary variables require explicit bounds 0 and 1")
        variables[key] = {**var, "lower": lower, "upper": upper}
    discrete = any(var["domain"] != "continuous" for var in variables.values())
    if (spec["model_class"] == "MILP") != discrete:
        raise ContractError("LP/MILP model_class disagrees with declared variable domains")
    ids = set(variables)
    objective = fields(spec["objective"], {"sense", "unit", "metric", "constant", "coefficients"}, "objective")
    if objective["sense"] not in ("min", "max"):
        raise ContractError("objective sense must be min or max")
    identifier(objective["unit"], "objective/unit")
    identifier(objective["metric"], "objective/metric")
    parsed_objective = {**objective, "constant": number(objective["constant"], "objective/constant"),
                        "coefficients": coefficients(objective["coefficients"], ids, "objective/coefficients")}
    constraints = {}
    for row in rows(spec["constraints"], "constraints", allow_empty=True):
        fields(row, {"id", "unit", "coefficients", "sense", "rhs"}, "constraint")
        key = identifier(row["id"], "constraint id")
        identifier(row["unit"], f"{key}/unit")
        if key in constraints or row["sense"] not in ("le", "eq", "ge"):
            raise ContractError(f"{key}: duplicate constraint or unknown sense")
        constraints[key] = {**row, "coefficients": coefficients(row["coefficients"], ids, key),
                            "rhs": number(row["rhs"], f"{key}/rhs")}
    return {"variables": variables, "objective": parsed_objective, "constraints": constraints}


def display(value: Fraction):
    """Keep the report JSON finite even when a finite input product exceeds float range."""
    try:
        converted = float(value)
        if math.isfinite(converted):
            return converted
    except OverflowError:
        pass
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def dot(coefs: dict, values: dict) -> Fraction:
    return sum((coefficient * values[key] for key, coefficient in coefs.items()), Fraction(0))


def objective_tolerance(left: Fraction, right: Fraction) -> Fraction:
    return number(TOLERANCES["objective_absolute"], "tol") + number(TOLERANCES["objective_relative"], "tol") * max(abs(left), abs(right))


def dual_bound(parsed: dict, certificate: dict) -> Fraction:
    """A directly verified Lagrangian bound, also valid for the MILP relaxation.

    For minimization, nonnegative multipliers multiply normalized Ax<=b rows.
    Equality multipliers are free. Minimize the resulting linear function over
    declared variable bounds. Unbounded residual coefficients must be exactly zero.
    """
    fields(certificate, {"kind", "multipliers"}, "certificate")
    if certificate["kind"] != "lagrangian_bound":
        raise ContractError("unsupported certificate; solver status/gap text is not independently verified")
    multipliers = fields(certificate["multipliers"], set(parsed["constraints"]), "certificate/multipliers")
    objective = parsed["objective"]
    sign = 1 if objective["sense"] == "min" else -1
    reduced = {key: sign * objective["coefficients"].get(key, Fraction(0)) for key in parsed["variables"]}
    bound = sign * objective["constant"]
    for key, row in parsed["constraints"].items():
        multiplier = number(multipliers[key], f"certificate/multipliers/{key}")
        if row["sense"] != "eq" and multiplier < 0:
            raise ContractError(f"{key}: inequality multiplier must be nonnegative")
        row_sign = -1 if row["sense"] == "ge" else 1
        bound -= multiplier * row_sign * row["rhs"]
        for var_id, coef in row["coefficients"].items():
            reduced[var_id] += multiplier * row_sign * coef
    for key, coef in reduced.items():
        if not coef:
            continue
        edge = parsed["variables"][key]["lower" if coef > 0 else "upper"]
        if edge is None:
            raise ContractError(f"{key}: certificate has an unbounded reduced-cost term")
        bound += coef * edge
    return bound


def check_solution(spec: dict, result: dict, *, spec_sha256: str | None = None) -> dict:
    report = {"schema_version": SCHEMA_VERSION, "profile": PROFILE, "status": "INVALID",
              "feasibility": "NOT_CHECKED", "optimality": "NOT_CHECKED", "errors": [],
              "checked_scope": "declared LP/MILP arithmetic, bounds, integrality and constraints; problem interpretation is not certified"}

    def issue(code, location, message):
        report["errors"].append({"code": code, "location": location, "message": message})

    try:
        parsed = validate_spec(spec)
        fields(result, {"schema_version", "spec_sha256", "run_id", "values", "reported_objective", "claim", "certificate"}, "result")
        if result["schema_version"] != SCHEMA_VERSION:
            raise ContractError("unsupported result schema")
        hash_value(result["spec_sha256"], "result/spec_sha256")
        if spec_sha256 is not None and result["spec_sha256"] != spec_sha256:
            raise ContractError("result refers to a different specification hash")
        identifier(result["run_id"], "result/run_id")
        values = {key: number(value, f"values/{key}") for key, value in fields(result["values"], set(parsed["variables"]), "result/values").items()}
        claimed_objective = number(result["reported_objective"], "reported_objective")
        if result["claim"] not in ("feasible", "heuristic", "optimal"):
            raise ContractError("claim must be feasible, heuristic or optimal")
        if result["certificate"] is not None and type(result["certificate"]) is not dict:
            raise ContractError("certificate must be null or an object")
        feasibility_tol = number(TOLERANCES["feasibility_absolute"], "tol")
        integer_tol = number(TOLERANCES["integrality_absolute"], "tol")
        bounds, integers, constraints = [], [], []
        for key, var in parsed["variables"].items():
            value = values[key]
            violation = max(Fraction(0), (var["lower"]-value) if var["lower"] is not None else Fraction(0),
                            (value-var["upper"]) if var["upper"] is not None else Fraction(0))
            bounds.append(violation)
            if violation > feasibility_tol:
                issue("BOUND_VIOLATION", f"variables/{key}", f"bound violation: {display(violation)}")
            if var["domain"] != "continuous":
                floor = value.numerator // value.denominator
                residual = min(value-floor, floor+1-value)
                integers.append(residual)
                if residual > integer_tol:
                    issue("INTEGRALITY_VIOLATION", f"variables/{key}", f"distance to integer: {display(residual)}")
        row_results = []
        for key, row in parsed["constraints"].items():
            lhs = dot(row["coefficients"], values)
            residual = lhs-row["rhs"]
            violation = abs(residual) if row["sense"] == "eq" else max(Fraction(0), residual if row["sense"] == "le" else -residual)
            constraints.append(violation)
            row_results.append({"id": key, "lhs": display(lhs), "rhs": display(row["rhs"]),
                                "signed_residual": display(residual), "violation": display(violation)})
            if violation > feasibility_tol:
                issue("CONSTRAINT_VIOLATION", f"constraints/{key}", f"constraint violation: {display(violation)}")
        report["feasibility"] = "FAIL" if report["errors"] else "PASS"
        objective = parsed["objective"]["constant"] + dot(parsed["objective"]["coefficients"], values)
        if abs(objective-claimed_objective) > objective_tolerance(objective, claimed_objective):
            issue("OBJECTIVE_MISMATCH", "reported_objective", f"independent objective is {display(objective)}")
        report.update({"objective": display(objective), "constraint_checks": row_results,
                       "max_bound_violation": display(max(bounds, default=Fraction(0))),
                       "max_integrality_violation": display(max(integers, default=Fraction(0))),
                       "max_constraint_violation": display(max(constraints, default=Fraction(0))),
                       "optimality": "NOT_CLAIMED", "status": "FAIL" if report["errors"] else "PASS"})
        if result["certificate"] is not None:
            try:
                bound = dual_bound(parsed, result["certificate"])
                signed_objective = objective if parsed["objective"]["sense"] == "min" else -objective
                gap = signed_objective-bound
                report["verified_objective_bound"] = display(bound if parsed["objective"]["sense"] == "min" else -bound)
                report["verified_absolute_gap"] = display(gap)
                if report["feasibility"] == "PASS" and 0 <= gap <= objective_tolerance(signed_objective, bound):
                    report["optimality"] = "CERTIFIED_WITHIN_TOLERANCE"
                else:
                    report["optimality"] = "NOT_ESTABLISHED"
            except ContractError as exc:
                report["optimality"] = "UNSUPPORTED"
                issue("UNSUPPORTED_CERTIFICATE", "certificate", str(exc))
                if report["status"] == "PASS":
                    report["status"] = "UNKNOWN"
        if result["claim"] == "optimal" and report["optimality"] != "CERTIFIED_WITHIN_TOLERANCE":
            report["optimality"] = "UNSUPPORTED" if result["certificate"] is None else report["optimality"]
            issue("UNSUPPORTED_OPTIMALITY", "claim", "optimality needs an independently verified bound within the fixed tolerance")
            if report["status"] == "PASS":
                report["status"] = "UNKNOWN"
    except (ContractError, TypeError, ValueError, OverflowError) as exc:
        report["status"] = "INVALID"
        issue("INVALID_CONTRACT", "spec/result", str(exc))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = check_solution(load_json(args.spec), load_json(args.result), spec_sha256=sha256(args.spec))
        report["input_hashes"] = {str(args.spec): sha256(args.spec), str(args.result): sha256(args.result)}
    except (OSError, ValueError) as exc:
        report = {"schema_version": SCHEMA_VERSION, "status": "INVALID", "errors": [{"code": "INVALID_INPUT", "message": str(exc)}]}
    encoded = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
