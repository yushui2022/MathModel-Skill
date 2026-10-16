"""Bind numerical prose to recorded metrics; this is not a semantic proof engine."""
from __future__ import annotations

import csv
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

from authoring_contracts import read_json, relative, safe_relative_path, sha256_file, write_json
from paper_scope import visible_prose

VERSION = 1
SPLITS = {
    "train": ("训练集", "training set", "train set"),
    "test": ("测试集", "test set", "held-out set"),
    "validation": ("验证集", "validation set"),
    "all": ("全样本", "full sample"),
    "not_applicable": (),
}
STRENGTHS = {"observed": 0, "feasible": 1, "optimal": 2}
NUMBER = r"[-+]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][-+]?\d+)?"


def number(value) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError("expected a finite numeric value")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("expected a finite numeric value") from exc
    if not result.is_finite() or (result and abs(result.adjusted()) > 100):
        raise ValueError("numeric value is nonfinite or outside supported magnitude")
    return result


def required_metric_items(sections):
    return [item for section in sections for item in section.get("requirements", {}).get("evidence", [])
            if item.get("type") == "metric" or isinstance(item.get("value"), (int, float))]


def artifact_hash(root, path_text, run):
    path = safe_relative_path(root, path_text)
    key = relative(path, root)
    records = [r for r in run.get("output_artifacts", []) if isinstance(r, dict)
               and str(r.get("path", "")).replace("\\", "/") == key]
    if len(records) != 1 or not path.is_file() or sha256_file(path) != records[0].get("sha256"):
        raise ValueError(f"output is missing, changed, or not bound to the selected run: {key}")
    return path, sha256_file(path)


def build_catalog(root, sections, gate):
    """Resolve requirements against computed metrics, never outline-supplied context."""
    requirements = required_metric_items(sections)
    if not requirements:
        return {}, {}
    metrics_path = root / "paper_output/results/metrics.json"
    manifest_path = root / "paper_output/results/run_manifest.json"
    hashes = {}
    for path in (metrics_path, manifest_path):
        key = relative(path, root)
        if not path.is_file() or (gate.get("input_hashes") or {}).get(key) != sha256_file(path):
            raise ValueError(f"S6 must bind the current {key}; rerun evidence gate")
        hashes[key] = sha256_file(path)
    metrics = read_json(metrics_path).get("items", [])
    manifest = read_json(manifest_path)
    if manifest.get("status") != "PASS" or not isinstance(metrics, list):
        raise ValueError("metric catalog requires computed metrics and a PASS run manifest")
    selected = {}
    for requirement in requirements:
        matches = [m for m in metrics if isinstance(m, dict)
                   and m.get("question_id") == requirement.get("question_id")
                   and (m.get("metric_id") == requirement["metric_id"] if requirement.get("metric_id")
                        else (m.get("metric_name") or m.get("metric_role")) == requirement.get("name"))]
        if len(matches) != 1:
            raise ValueError(f"metric requirement is missing or ambiguous: {requirement.get('evidence_id')}; use metric_id")
        metric = matches[0]
        mid = metric.get("metric_id")
        if not isinstance(mid, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]+", mid):
            raise ValueError("computed metric needs a stable ASCII metric_id")
        if sum(isinstance(m, dict) and m.get("metric_id") == mid for m in metrics) != 1:
            raise ValueError(f"duplicate metric_id: {mid}")
        if metric.get("status") != "computed":
            raise ValueError(f"{mid}: metric is not computed")
        if number(metric.get("value")) != number(requirement.get("value")):
            raise ValueError(f"{mid}: outline value differs from metrics.json; rebuild outline")
        requirement["metric_id"] = mid
        if mid in selected:
            continue
        for key in ("metric_name", "unit", "sample_scope"):
            if not isinstance(metric.get(key), str) or not metric[key].strip():
                raise ValueError(f"{mid}: missing {key}; do not infer metric context during writing")
        split = metric.get("split")
        strength = metric.get("claim_strength", "observed")
        if split not in SPLITS or strength not in STRENGTHS:
            raise ValueError(f"{mid}: invalid split or claim_strength")
        source = metric.get("source_table")
        if not isinstance(source, dict) or not isinstance(source.get("row"), dict) or not source["row"]:
            raise ValueError(f"{mid}: source_table needs path, unique row selector, and value_column")
        table = safe_relative_path(root, source.get("path"))
        table_key = relative(table, root)
        runs = [r for r in manifest.get("runs", []) if isinstance(r, dict)
                and r.get("status") == "PASS" and r.get("returncode") == 0
                and metric.get("question_id") in r.get("question_ids", [])
                and (not metric.get("run_id") or r.get("run_id") == metric["run_id"])
                and any(isinstance(a, dict) and str(a.get("path", "")).replace("\\", "/") == table_key
                        for a in r.get("output_artifacts", []))]
        if len(runs) != 1 or not runs[0].get("run_id"):
            raise ValueError(f"{mid}: source table does not resolve to exactly one successful experiment")
        run = runs[0]
        table, digest = artifact_hash(root, table_key, run)
        if table.suffix.lower() != ".csv":
            raise ValueError(f"{mid}: export an auditable CSV table for the numerical claim")
        with table.open(encoding="utf-8-sig", newline="") as stream:
            rows = [r for r in csv.DictReader(stream) if all(r.get(k) == str(v) for k, v in source["row"].items())]
        if len(rows) != 1 or number(rows[0].get(source.get("value_column"))) != number(metric["value"]):
            raise ValueError(f"{mid}: source table row is ambiguous or disagrees with the metric")
        if source.get("unit_column") and rows[0].get(source["unit_column"]) != metric["unit"]:
            raise ValueError(f"{mid}: source table unit disagrees with the metric")
        hashes[table_key] = digest
        if strength != "observed":
            proof, digest = artifact_hash(root, metric.get("verification_path"), run)
            report = read_json(proof)
            if (report.get("status") != "PASS" or report.get("metric_id") != mid
                    or report.get("feasibility_verified") is not True
                    or report.get("unit") != metric["unit"]
                    or number(report.get("objective_value")) != number(metric["value"])
                    or (strength == "optimal" and report.get("optimality_verified") is not True)):
                raise ValueError(f"{mid}: no matching {strength} verification report")
            hashes[relative(proof, root)] = digest
        transforms = metric.get("allowed_transforms", ["identity"])
        if (not isinstance(transforms, list) or not transforms
                or any(t not in ("identity", "ratio_to_percent") for t in transforms)
                or ("ratio_to_percent" in transforms and metric["unit"] != "1")):
            raise ValueError(f"{mid}: invalid allowed_transforms (percent conversion requires unit '1')")
        aliases = metric.get("aliases", [])
        if not isinstance(aliases, list) or any(not isinstance(a, str) or not a.strip() for a in aliases):
            raise ValueError(f"{mid}: aliases must be nonempty strings")
        selected[mid] = {**metric, "run_id": run["run_id"], "claim_strength": strength,
                         "allowed_transforms": transforms, "source_table": {**source, "path": table_key},
                         "aliases": list(dict.fromkeys([metric["metric_name"], *aliases]))}
    return selected, hashes


def claims_path(path):
    return path.with_suffix(".claims.json")


def enabled(plan):
    return (plan.get("delivery") or {}).get("mode") != "smoke-test"


def check_plan(plan):
    if enabled(plan) and (plan.get("claim_binding_version") != VERSION or not isinstance(plan.get("metric_catalog"), dict)):
        return ["missing metric binding contract; rerun prepare_authoring.py (old plans cannot prove claim semantics)"]
    if enabled(plan):
        required = required_metric_items(plan.get("sections", []))
        if any(not item.get("metric_id") or item["metric_id"] not in plan["metric_catalog"] for item in required):
            return ["writing plan has unbound metric requirements; rerun prepare_authoring.py"]
    return []


def names_in(text, aliases):
    return any(re.search(r"(?<![A-Za-z0-9_])" + re.escape(alias) + r"(?![A-Za-z0-9_])", text, re.I)
               for alias in aliases)


def spans(text):
    # Sentence boundaries, excluding decimal points; quotes bind whole sentences/CSV-style table rows.
    return list(re.finditer(r"[^\n]+?(?:[。！？!?;；]|\.(?=\s|$)|$)", text, re.M))


def claim_prose(text):
    # Formula definitions and inline code are not reported numerical results.
    text = visible_prose(text)
    return re.sub(r"\$\$.*?\$\$|(?<!\\)\$[^$\n]+\$|`[^`\n]+`", "", text, flags=re.S)


def strength_in(text):
    text = re.sub(r"(?:未|无法|不能|不|尚未)(?:能|证明|保证|确认|达到|获得|为|是)*\s*(?:全局)?最优(?:性|解)?|"
                  r"\b(?:not|no)\s+(?:proven\s+|guarantee\s+of\s+)?(?:global\s+)?optimal\w*", "", text, flags=re.I)
    if re.search(r"最优|\boptimal(?:ity)?\b", text, re.I):
        return "optimal"
    if re.search(r"可行解|满足全部约束|\bfeasible\b", text, re.I):
        return "feasible"
    return "observed"


def audit_claims(root, path, plan, section):
    """Return errors, resolved claims and hashes for state freshness checks."""
    if not enabled(plan):
        return [], [], {}
    errors = check_plan(plan)
    if errors:
        return errors, [], {}
    catalog = plan["metric_catalog"]
    if not catalog:
        return [], [], {}
    visible = claim_prose(path.read_text(encoding="utf-8"))
    sidecar = claims_path(path)
    try:
        data = read_json(sidecar)
    except ValueError as exc:
        return [str(exc) + "; write a .claims.json sidecar, including claims: [] when no metrics occur"], [], {}
    binding_hashes = {relative(sidecar, root): sha256_file(sidecar)}
    source_hash = sha256_file(path)
    if (data.get("schema_version") != "1" or data.get("source_sha256") != source_hash
            or not isinstance(data.get("claims"), list)):
        return ["claim sidecar schema/source_sha256 is stale or claims is not a list"], [], binding_hashes
    resolved, covered = [], set()
    sentences = spans(visible)
    for index, claim in enumerate(data["claims"], 1):
        prefix = f"claim {index}"
        if not isinstance(claim, dict) or not isinstance(claim.get("metric_id"), str) or claim["metric_id"] not in catalog:
            errors.append(f"{prefix}: unknown metric_id")
            continue
        mid = claim["metric_id"]
        metric = catalog[mid]
        quote = claim.get("quote")
        matches = [s for s in sentences if isinstance(quote, str) and s.group().strip() == quote.strip()]
        if not matches:
            errors.append(f"{prefix}/{mid}: quote must match a whole visible sentence or table row")
            continue
        try:
            transform = claim.get("transform", "identity")
            if transform not in metric["allowed_transforms"]:
                raise ValueError("undeclared conversion")
            expected_unit = "%" if transform == "ratio_to_percent" else metric["unit"]
            if claim.get("unit") != expected_unit:
                raise ValueError("unit does not match the approved conversion")
            expected = number(metric["value"]) * (100 if transform == "ratio_to_percent" else 1)
            places = claim.get("decimals")
            if places is not None:
                if type(places) is not int or not 0 <= places <= 8:
                    raise ValueError("decimals must be an integer in 0..8")
                expected = expected.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
            if number(claim.get("value")) != expected:
                raise ValueError("displayed value differs from the approved conversion/rounding")
            if not names_in(quote, metric["aliases"]):
                raise ValueError("quote lacks the metric name or an approved alias")
            if metric["sample_scope"] not in quote:
                raise ValueError("quote lacks the recorded sample_scope")
            split = metric["split"]
            observed_splits = {key for key, labels in SPLITS.items() if any(label.casefold() in quote.casefold() for label in labels)}
            if split != "not_applicable" and observed_splits != {split}:
                raise ValueError("quote split differs from evidence (train/test/validation/all)")
            if split == "not_applicable" and observed_splits:
                raise ValueError("quote invents a sample split")
            numeric_quote = quote.replace(metric["sample_scope"], "")
            for alias in metric["aliases"]:
                numeric_quote = numeric_quote.replace(alias, "")
            suffix = "" if expected_unit == "1" else r"\s*" + re.escape(expected_unit)
            tokens = re.findall(r"(?<![0-9A-Za-z_.+-])(" + NUMBER + r")" + suffix + r"(?![A-Za-z0-9_%/\u4e00-\u9fff]|\.\d)", numeric_quote)
            raw_numbers = re.findall(NUMBER, numeric_quote)
            if len(tokens) != 1 or len(raw_numbers) != 1 or number(tokens[0]) != expected:
                raise ValueError("quote does not contain the displayed number with its unit")
            for field in ("run_id", "split", "sample_scope", "source_table"):
                if field in claim and claim[field] != metric[field]:
                    raise ValueError(f"binding overrides recorded {field}")
            assertion = claim.get("assertion", "observed")
            if assertion not in STRENGTHS or STRENGTHS[assertion] > STRENGTHS[metric["claim_strength"]]:
                raise ValueError("claim exceeds the verified evidence strength")
            if STRENGTHS[strength_in(quote)] > STRENGTHS[assertion]:
                raise ValueError("prose claims feasibility/optimality not supported by its binding")
        except (ValueError, TypeError, InvalidOperation) as exc:
            errors.append(f"{prefix}/{mid}: {exc}")
            continue
        for match in matches:
            covered.add((mid, match.start()))
        resolved.append({**claim, "run_id": metric["run_id"], "split": metric["split"],
                         "sample_scope": metric["sample_scope"], "source_table": metric["source_table"]})
    for sentence in sentences:
        candidates = [mid for mid, metric in catalog.items() if names_in(sentence.group(), metric["aliases"])]
        if candidates and re.search(NUMBER, sentence.group()) and not any((mid, sentence.start()) in covered for mid in candidates):
            errors.append(f"{candidates}: numerical occurrence has no valid binding: {sentence.group().strip()[:120]}")
        explicit_optimum = re.search(r"(?:方案|结果|解|模型)(?:是|为|达到|取得).{0,8}最优|"
                                     r"(?:获得|取得|证明了|达到了)(?:全局)?最优解|"
                                     r"\b(?:solution|result|model)\s+is\s+(?:globally\s+)?optimal\b", sentence.group(), re.I)
        if explicit_optimum and strength_in(sentence.group()) == "optimal" and not any(
            (mid, sentence.start()) in covered and catalog[mid]["claim_strength"] == "optimal" for mid in catalog
        ):
            errors.append("unbound optimality assertion; state the objective metric and cite its verified claim")
    required = {r.get("metric_id") for r in required_metric_items([section]) if r.get("metric_id")}
    missing = required - {r["metric_id"] for r in resolved}
    if missing:
        errors.append(f"required metrics have no valid prose claims: {sorted(missing)}")
    return errors, resolved, binding_hashes


def record_errors(root, path, record, plan):
    if not enabled(plan) or not plan.get("metric_catalog"):
        return []
    sidecar = claims_path(path)
    if not sidecar.is_file() or record.get("claims_sha256") != sha256_file(sidecar):
        return [f"claim bindings missing or changed after validation: {relative(sidecar, root)}"]
    return []


def assemble_claims(root, paths, destination, plan):
    if not enabled(plan) or not plan.get("metric_catalog"):
        return
    claims = []
    for path in paths:
        claims.extend(read_json(claims_path(path))["claims"])
    # Identical sentences in multiple chapters need only one identical binding.
    import json
    claims = list({json.dumps(c, sort_keys=True, ensure_ascii=False): c for c in claims}.values())
    write_json(claims_path(destination), {"schema_version": "1", "source_sha256": sha256_file(destination), "claims": claims})
