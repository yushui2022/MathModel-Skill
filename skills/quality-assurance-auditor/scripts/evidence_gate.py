import argparse
import csv
import hashlib
import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path, PureWindowsPath
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_policy import POLICY_VERSION, accepted_status, project_artifact


BASE_DIR = Path.cwd()
OUTPUT_DIR = BASE_DIR / "paper_output"
QA_DIR = OUTPUT_DIR / "qa"
MODEL_ROUTE_FILE = OUTPUT_DIR / "plan" / "model_route.json"
FIGURE_INDEX_FILE = OUTPUT_DIR / "figure_index.json"
MODEL_RESULTS_FILE = OUTPUT_DIR / "results" / "model_results.json"
RUN_MANIFEST_FILE = OUTPUT_DIR / "results" / "run_manifest.json"
METRICS_FILE = OUTPUT_DIR / "results" / "metrics.json"
CONCLUSIONS_FILE = OUTPUT_DIR / "results" / "conclusions.json"
TABLE_INDEX_FILE = OUTPUT_DIR / "tables" / "table_index.json"
REPORT_JSON = QA_DIR / "evidence_gate_report.json"
REPORT_MD = QA_DIR / "evidence_gate_report.md"

def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"__error__": str(exc)}


def question_ids(model_route: Any) -> list[str]:
    questions = model_route.get("questions") if isinstance(model_route, dict) else []
    if not isinstance(questions, list):
        return []
    result = []
    for item in questions:
        if not isinstance(item, dict):
            continue
        qid = str(item.get("question_id") or item.get("id") or "").strip()
        if qid:
            result.append(qid)
    return sorted(set(result))


def grouped_items(data: Any, key: str) -> dict[str, list[dict[str, Any]]]:
    items = data.get(key) if isinstance(data, dict) else []
    grouped: dict[str, list[dict[str, Any]]] = {}
    if not isinstance(items, list):
        return grouped
    for item in items:
        if not isinstance(item, dict):
            continue
        qid = str(item.get("question_id") or "").strip()
        if qid:
            grouped.setdefault(qid, []).append(item)
    return grouped


def result_items(data: Any) -> dict[str, dict[str, Any]]:
    questions = data.get("questions") if isinstance(data, dict) else []
    grouped: dict[str, dict[str, Any]] = {}
    if not isinstance(questions, list):
        return grouped
    for item in questions:
        if not isinstance(item, dict):
            continue
        qid = str(item.get("question_id") or "").strip()
        if qid:
            grouped[qid] = item
    return grouped


def figure_items(data: Any) -> dict[str, list[dict[str, Any]]]:
    return grouped_items(data, "figures")


def table_items(data: Any) -> dict[str, list[dict[str, Any]]]:
    return grouped_items(data, "tables")


def status_of(item: dict[str, Any] | None) -> str:
    if not item:
        return "missing"
    return str(item.get("evidence_status") or item.get("status") or "").strip()


def resolve_artifact(path_text: object) -> Path:
    text = str(path_text or "").strip().strip("<>").replace("\\", "/")
    path = Path(text)
    if path.is_absolute():
        return path
    return BASE_DIR / path


def normalized_artifact(path_text: object) -> str:
    path = resolve_artifact(path_text)
    try:
        return path.resolve().relative_to(BASE_DIR.resolve()).as_posix()
    except Exception:
        return str(path).replace("\\", "/")


def sha256_file(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def recorded_file_failures(entry: dict[str, Any], label: str) -> list[str]:
    path_text = entry.get("path")
    if not str(path_text or "").strip():
        return [f"{label} 缺少 path"]
    path = resolve_artifact(path_text)
    failures: list[str] = []
    if not path.exists() or not path.is_file():
        return [f"{label} 文件不存在：{normalized_artifact(path_text)}"]
    if path.stat().st_size <= 0:
        failures.append(f"{label} 文件为空：{normalized_artifact(path_text)}")
    recorded_size = entry.get("bytes")
    if recorded_size not in (None, ""):
        try:
            if int(recorded_size) != path.stat().st_size:
                failures.append(
                    f"{label} 大小已变化：{normalized_artifact(path_text)} "
                    f"({recorded_size} -> {path.stat().st_size})"
                )
        except (TypeError, ValueError):
            failures.append(f"{label} bytes 字段无效：{recorded_size}")
    recorded_hash = str(entry.get("sha256") or "").strip().lower()
    if not recorded_hash:
        failures.append(f"{label} 缺少 sha256：{normalized_artifact(path_text)}")
    else:
        current_hash = sha256_file(path)
        if current_hash != recorded_hash:
            failures.append(f"{label} 内容哈希已变化：{normalized_artifact(path_text)}")
    return failures


def provenance_failures(item: dict[str, Any]) -> list[str]:
    provenance = item.get("execution_provenance")
    if not isinstance(provenance, dict):
        return ["缺少 execution_provenance，无法证明结果来自实际代码运行"]

    failures: list[str] = []
    source_code = resolve_artifact(provenance.get("source_code_path"))
    if not provenance.get("source_code_path"):
        failures.append("execution_provenance.source_code_path 为空")
    elif not source_code.exists():
        failures.append(f"source_code_path 不存在：{source_code}")
    elif provenance.get("source_code_sha256"):
        if sha256_file(source_code) != str(provenance.get("source_code_sha256") or "").lower():
            failures.append(f"source_code_path 内容已变化：{normalized_artifact(provenance.get('source_code_path'))}")

    if provenance.get("run_exit_code") not in (0, "0"):
        failures.append(f"run_exit_code 不是 0：{provenance.get('run_exit_code')}")

    if not str(provenance.get("run_command") or "").strip():
        failures.append("execution_provenance.run_command 为空")

    for artifact in provenance.get("output_artifacts", []) or []:
        artifact_path = resolve_artifact(artifact)
        if not artifact_path.exists():
            failures.append(f"输出产物不存在：{artifact}")
    return failures


def run_manifest_failures(item: dict[str, Any], run_manifest: Any) -> list[str]:
    if not isinstance(run_manifest, dict):
        return ["缺少或无法读取 run_manifest.json，无法核验建模代码运行记录"]
    runs = run_manifest.get("runs")
    if not isinstance(runs, list):
        return ["run_manifest.json 缺少 runs 列表"]
    if str(run_manifest.get("status") or "").upper() != "PASS":
        return [f"run_manifest.json status 不是 PASS：{run_manifest.get('status')}"]

    provenance = item.get("execution_provenance")
    if not isinstance(provenance, dict):
        return ["缺少 execution_provenance，无法匹配 run_manifest"]
    version = str(run_manifest.get("schema_version") or "1.0")
    if version not in ("1.0", "1.1"):
        return [f"Unsupported run_manifest schema_version: {version}"]
    if version != "1.1" and (provenance.get("execution_schema_version") == "1.1" or provenance.get("run_id")):
        return ["Current execution provenance requires run_manifest schema 1.1; rerun modeling"]
    if version == "1.1":
        current_failures = current_receipt_failures(item, run_manifest)
        if current_failures:
            return current_failures
    source_code = normalized_artifact(provenance.get("source_code_path"))
    qid = str(item.get("question_id") or "").strip()
    matches = [
        run for run in runs
        if isinstance(run, dict) and normalized_artifact(run.get("script")) == source_code
    ]
    if not matches:
        return [f"run_manifest.json 中没有 source_code_path 对应的运行记录：{source_code}"]

    run = matches[-1]
    failures: list[str] = []
    if run.get("returncode") not in (0, "0"):
        failures.append(f"run_manifest 记录 returncode 不是 0：{run.get('returncode')}")
    script_path = resolve_artifact(run.get("script"))
    if not script_path.exists():
        failures.append(f"run_manifest 记录的脚本不存在：{normalized_artifact(run.get('script'))}")
    else:
        script_hash = str(run.get("script_sha256") or "").strip().lower()
        if not script_hash:
            failures.append("run_manifest 运行记录缺少 script_sha256")
        elif sha256_file(script_path) != script_hash:
            failures.append(f"建模脚本在运行后已变化：{normalized_artifact(run.get('script'))}")
    run_qids = {str(value) for value in run.get("question_ids", []) or []}
    if qid and run_qids and qid not in run_qids:
        failures.append(f"run_manifest 运行记录未包含当前 question_id：{qid}")
    run_outputs = {
        normalized_artifact(item.get("path"))
        for item in run.get("output_artifacts", []) or []
        if isinstance(item, dict)
    }
    for artifact in provenance.get("output_artifacts", []) or []:
        normalized = normalized_artifact(artifact)
        if normalized not in run_outputs:
            failures.append(f"execution_provenance 输出未进入 run_manifest：{normalized}")
    missing_outputs = [
        str(item.get("path"))
        for item in run.get("output_artifacts", []) or []
        if isinstance(item, dict) and not item.get("exists")
    ]
    for artifact in missing_outputs:
        failures.append(f"run_manifest 记录输出产物不存在：{artifact}")
    for entry in run.get("input_files", []) or []:
        if isinstance(entry, dict):
            failures.extend(recorded_file_failures(entry, "运行输入"))
    for entry in run.get("output_artifacts", []) or []:
        if isinstance(entry, dict):
            failures.extend(recorded_file_failures(entry, "运行输出"))
    return failures


def current_receipt_failures(item: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    """Bind current-invocation results and shared contracts before inspecting files."""
    failures = []
    contracts = manifest.get("contract_files")
    required = {"paper_output/results/model_results.json", "paper_output/results/metrics.json",
                "paper_output/results/conclusions.json", "paper_output/tables/table_index.json"}
    if not isinstance(contracts, list) or len(contracts) != len(required):
        return ["run_manifest requires all four result contract snapshots"]
    if any(not isinstance(e, dict) for e in contracts):
        return ["Invalid run_manifest contract_files entry"]
    if {e.get('path') for e in contracts if isinstance(e.get('path'), str)} != required:
        return ["run_manifest contract_files does not match required result contracts"]
    provenance = item['execution_provenance']
    run_id = provenance.get('run_id')
    matches = [run for run in manifest['runs'] if isinstance(run, dict) and run.get('run_id') == run_id]
    if not isinstance(run_id, str) or not run_id or len(matches) != 1:
        return ["Result does not match exactly one current invocation run_id"]
    run = matches[0]
    if str(item.get('question_id')) not in (run.get('question_ids') or []):
        failures.append("Current invocation does not contain result question_id")
    if run.get('timed_out') is not False or run.get('status') != 'PASS':
        failures.append("Current invocation timed out or did not pass")
    entries = list(contracts)
    for name in ('input_files', 'output_artifacts'):
        value = run.get(name)
        if not isinstance(value, list) or not value or any(not isinstance(e, dict) for e in value):
            return [f"Current invocation requires nonempty {name}"]
        entries.extend(value)
    paths = [e.get('path') for e in entries] + [run.get('script'), provenance.get('source_code_path')]
    for value in paths:
        if not isinstance(value, str) or not value or '\x00' in value:
            return ["Invalid current-invocation evidence path"]
        text = value.replace('\\', '/')
        if Path(text).is_absolute() or PureWindowsPath(text).drive or ':' in text or '..' in text.split('/'):
            return [f"Current-invocation evidence path must be project-relative: {value}"]
        path = (BASE_DIR / text).resolve()
        if path == BASE_DIR.resolve() or not path.is_relative_to(BASE_DIR.resolve()):
            return [f"Current-invocation evidence path escapes project: {value}"]
    if normalized_artifact(run.get('script')) != normalized_artifact(provenance.get('source_code_path')):
        failures.append("Current invocation script differs from result provenance")
    for entry in contracts:
        failures.extend(recorded_file_failures(entry, "运行结果契约"))
    return failures


def has_bad_status(items: list[dict[str, Any]]) -> bool:
    return any(not accepted_status(item) for item in items)


def conclusion_text_exists(items: list[dict[str, Any]]) -> bool:
    return any(str(item.get("conclusion_text") or "").strip() for item in items)


def metric_value_failures(items: list[dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    for item in items:
        name = str(item.get("metric_name") or item.get("metric_role") or "<unnamed>")
        value = item.get("value")
        if value is None or value == "":
            failures.append(f"指标 {name} 缺少有效 value")
        elif type(value) not in (int, float) or (isinstance(value, float) and not math.isfinite(value)):
            failures.append(f"指标 {name} 不是有限数值（不接受文本或布尔值）：{value}")
    return failures


def indexed_artifact_failures(item: dict[str, Any], kind: str) -> list[str]:
    artifact_id = str(item.get("figure_id") or item.get("table_id") or "<unknown>")
    status = status_of(item)
    failures: list[str] = []
    if not accepted_status(item):
        failures.append(f"{kind} {artifact_id} 状态不可作为正式证据：{status}")
    if item.get('evidence_role') == 'exploratory':
        failures.append(f"{kind} {artifact_id} 仍为探索草图，不是正式实验")
    if item.get("placeholder") is True:
        failures.append(f"{kind} {artifact_id} 是占位产物")
    if item.get("ok") is False:
        failures.append(f"{kind} {artifact_id} 生成状态为失败")
    if item.get("exists") is False:
        failures.append(f"{kind} {artifact_id} 索引明确标记 exists=false")
    message = str(item.get("message") or "").strip().lower()
    if any(token in message for token in ("placeholder", "占位", "missing", "not readable", "无法", "缺少")):
        failures.append(f"{kind} {artifact_id} 包含失败/占位信息：{item.get('message')}")
    path_text = item.get("path") or item.get("expected_path")
    if not str(path_text or "").strip():
        failures.append(f"{kind} {artifact_id} 缺少 path")
    else:
        try:
            path = project_artifact(BASE_DIR, path_text)
        except ValueError as exc:
            return failures + [str(exc)]
        if not path.exists() or not path.is_file():
            failures.append(f"{kind} {artifact_id} 文件不存在：{normalized_artifact(path_text)}")
        elif path.stat().st_size <= 0:
            failures.append(f"{kind} {artifact_id} 文件为空：{normalized_artifact(path_text)}")
        else:
            try:
                if item.get('figure_id'):
                    from PIL import Image
                    with Image.open(path) as picture:
                        picture.verify()
                    with Image.open(path) as picture:
                        picture.load()
                elif path.suffix.lower() in ('.csv', '.tsv'):
                    with path.open(encoding='utf-8-sig', newline='') as handle:
                        rows = csv.reader(handle, delimiter='\t' if path.suffix.lower() == '.tsv' else ',', strict=True)
                        header = next(rows, [])
                        count = 0
                        if not header or any(not name.strip() for name in header) or len(set(header)) != len(header):
                            raise ValueError('Invalid or duplicate table headers')
                        for row in rows:
                            if len(row) != len(header):
                                raise ValueError('Malformed table row')
                            count += 1
                        if not count:
                            raise ValueError('Table has no data rows')
                elif path.suffix.lower() == '.xlsx':
                    from openpyxl import load_workbook
                    workbook = load_workbook(path, read_only=True, data_only=True)
                    try:
                        if not any(sum(any(v is not None for v in row) for row in sheet.values) >= 2 for sheet in workbook):
                            raise ValueError('Workbook has no header and data rows')
                    finally:
                        workbook.close()
                else:
                    raise ValueError('Formal tables require CSV, TSV or XLSX')
            except Exception as exc:
                failures.append(f"{kind} {artifact_id} 无法读取：{type(exc).__name__}: {exc}")
    return failures


def artifact_run_failures(item: dict[str, Any], manifest: Any) -> list[str]:
    """Every indexed artifact must be an output of a successful recorded run."""
    try:
        path = project_artifact(BASE_DIR, item.get('path') or item.get('expected_path'))
    except ValueError as exc:
        return [str(exc)]
    qid = item.get('question_id')
    runs = manifest.get('runs', []) if isinstance(manifest, dict) else []
    if not isinstance(runs, list):
        return ['Invalid run_manifest runs list']
    for run in runs:
        if not isinstance(run, dict) or run.get('returncode') != 0 or run.get('status', 'PASS') != 'PASS':
            continue
        if qid != 'ALL' and qid not in (run.get('question_ids') or []):
            continue
        for entry in run.get('output_artifacts', []) or []:
            if not isinstance(entry, dict):
                continue
            try:
                matches = project_artifact(BASE_DIR, entry.get('path')) == path
            except ValueError:
                continue
            if matches:
                return recorded_file_failures(entry, '图表运行产物')
    return [f"图表未绑定当前问题的实际运行产物：{item.get('path')}"]


def task_items(data: Any) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    if not isinstance(data, list):
        return grouped
    for item in data:
        if not isinstance(item, dict):
            continue
        qid = str(item.get("question_id") or "").strip()
        if qid:
            grouped.setdefault(qid, []).append(item)
    return grouped


def evaluate() -> dict[str, Any]:
    model_route = load_json(MODEL_ROUTE_FILE)
    figure_index = load_json(FIGURE_INDEX_FILE)
    model_results = load_json(MODEL_RESULTS_FILE)
    run_manifest = load_json(RUN_MANIFEST_FILE)
    metrics = load_json(METRICS_FILE)
    conclusions = load_json(CONCLUSIONS_FILE)
    table_index = load_json(TABLE_INDEX_FILE)

    failures: list[str] = []
    warnings: list[str] = []
    if isinstance(run_manifest, dict) and str(run_manifest.get('schema_version') or '1.0') == '1.0':
        warnings.append("Legacy run_manifest 1.0: no current-invocation ID or result-contract snapshot; regenerate the runner and rerun for 1.1 checks.")
    cleaning_paths = []
    analysis_path = OUTPUT_DIR / 'step1/problem_analysis.json'
    if analysis_path.exists():
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'problem-doc-model-selector/scripts'))
        from review_problem import review_errors
        analysis = load_json(analysis_path)
        failures.extend(review_errors(BASE_DIR, analysis))
        cleaning_paths.append(analysis_path)
        if isinstance(analysis, dict):
            for doc in analysis.get('documents', []):
                try:
                    cleaning_paths.append(project_artifact(BASE_DIR, doc.get('path')))
                except (ValueError, AttributeError) as exc:
                    failures.append(f'Invalid problem source: {exc}')
    cleaning_path = OUTPUT_DIR / "data_cleaned/cleaning_report.json"
    if cleaning_path.exists():
        cleaning_paths.append(cleaning_path)
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "data-cleaning-and-visualization/scripts"))
            from data_inputs import current_cleaning_report, project_path
            cleaning = current_cleaning_report(BASE_DIR.resolve())
            cleaning_paths.extend(project_path(BASE_DIR, name) for name in cleaning["input_hashes"])
            cleaning_paths.extend(project_path(BASE_DIR, item["cleaned_output"]) for item in cleaning["datasets"])
        except (ValueError, OSError, KeyError, TypeError) as exc:
            failures.append(f"Data import is stale or failed: {exc}")

    for path, data in (
        (MODEL_ROUTE_FILE, model_route),
        (FIGURE_INDEX_FILE, figure_index),
        (MODEL_RESULTS_FILE, model_results),
        (RUN_MANIFEST_FILE, run_manifest),
        (METRICS_FILE, metrics),
        (CONCLUSIONS_FILE, conclusions),
        (TABLE_INDEX_FILE, table_index),
    ):
        if data is None:
            failures.append(f"缺少证据门禁输入文件：{path.relative_to(BASE_DIR) if path.is_relative_to(BASE_DIR) else path}")
        elif isinstance(data, dict) and data.get("__error__"):
            failures.append(f"无法读取证据门禁输入文件：{path} ({data['__error__']})")

    qids = question_ids(model_route)
    if not qids:
        failures.append("model_route.json 中没有可追溯的 question_id，无法执行正式证据门禁。")

    for label, data, key, allow_all in (
        ('results', model_results, 'questions', False),
        ('metrics', metrics, 'items', False),
        ('conclusions', conclusions, 'items', False),
        ('figures', figure_index, 'figures', True),
        ('tables', table_index, 'tables', True),
    ):
        items = data.get(key) if isinstance(data, dict) else None
        if not isinstance(items, list):
            failures.append(f'{label}: expected {key} list')
            continue
        for item in items:
            if not isinstance(item, dict) or item.get('question_id') not in [*qids, *(['ALL'] if allow_all else [])]:
                failures.append(f'{label}: missing or unknown question_id')

    result_map = result_items(model_results)
    metric_map = grouped_items(metrics, "items")
    conclusion_map = grouped_items(conclusions, "items")
    figure_map = figure_items(figure_index)
    table_map = table_items(table_index)

    question_reports = []
    for qid in qids:
        q_failures: list[str] = []
        q_warnings: list[str] = []
        result = result_map.get(qid)
        q_metrics = metric_map.get(qid, [])
        q_conclusions = conclusion_map.get(qid, [])
        q_figures = figure_map.get(qid, []) + figure_map.get("ALL", [])
        q_tables = table_map.get(qid, []) + table_map.get("ALL", [])

        if not result:
            q_failures.append("缺少 model_results.json 中的模型结果")
        elif not accepted_status(result):
            q_failures.append(f"模型结果状态仍不可作为正式证据：{status_of(result)}")
        else:
            if not str(result.get("result_summary") or "").strip():
                q_failures.append("模型结果缺少 result_summary")
            for failure in provenance_failures(result):
                q_failures.append(f"模型结果缺少真实运行来源：{failure}")
            for failure in run_manifest_failures(result, run_manifest):
                q_failures.append(f"模型结果运行账本不完整：{failure}")

        if not q_metrics:
            q_failures.append("缺少 metrics.json 中的评价指标")
        elif has_bad_status(q_metrics):
            q_failures.append("评价指标仍包含草稿、模板或待补状态")
        else:
            q_failures.extend(metric_value_failures(q_metrics))

        if not q_conclusions or not conclusion_text_exists(q_conclusions):
            q_failures.append("缺少 conclusions.json 中可回扣原题的结论文本")
        elif has_bad_status(q_conclusions):
            q_failures.append("结论证据仍包含草稿、模板或待补状态")

        if not q_figures and not q_tables:
            q_failures.append("缺少图表或表格证据")
        for figure in q_figures:
            q_failures.extend(indexed_artifact_failures(figure, "图片"))
            q_failures.extend(artifact_run_failures(figure, run_manifest))
        if q_tables and has_bad_status(q_tables):
            q_failures.append("表格证据仍包含草稿、模板或待补状态")
        for table in q_tables:
            q_failures.extend(indexed_artifact_failures(table, "表格"))
            q_failures.extend(artifact_run_failures(table, run_manifest))

        for message in q_failures:
            failures.append(f"{qid}: {message}")
        for message in q_warnings:
            warnings.append(f"{qid}: {message}")

        question_reports.append(
            {
                "question_id": qid,
                "status": "FAIL" if q_failures else "PASS",
                "failures": q_failures,
                "warnings": q_warnings,
                "has_result": bool(result),
                "metric_count": len(q_metrics),
                "conclusion_count": len(q_conclusions),
                "figure_count": len(q_figures),
                "table_count": len(q_tables),
            }
        )

    # Preserve freshness of the actual computation, not just the JSON receipt.
    if isinstance(run_manifest, dict) and isinstance(run_manifest.get('runs'), list):
        for run in run_manifest['runs']:
            if not isinstance(run, dict):
                continue
            entries = [{'path': run.get('script')}]
            for key in ('input_files', 'output_artifacts'):
                values = run.get(key)
                if not isinstance(values, list):
                    failures.append(f'Invalid run_manifest {key} list')
                else:
                    entries.extend(values)
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                try:
                    cleaning_paths.append(project_artifact(BASE_DIR, entry.get('path')))
                except ValueError as exc:
                    failures.append(str(exc))

    return {
        "schema_version": "1.0",
        "policy_version": POLICY_VERSION,
        "generated_by": "quality-assurance-auditor/scripts/evidence_gate.py",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "warnings": warnings,
        "questions": question_reports,
        "input_hashes": {
            normalized_artifact(path): sha256_file(path)
            for path in (
                MODEL_ROUTE_FILE,
                FIGURE_INDEX_FILE,
                MODEL_RESULTS_FILE,
                RUN_MANIFEST_FILE,
                METRICS_FILE,
                CONCLUSIONS_FILE,
                TABLE_INDEX_FILE,
                *cleaning_paths,
                *[project_artifact(BASE_DIR, item.get('path') or item.get('expected_path'))
                  for group in (figure_map, table_map) for items in group.values() for item in items
                  if artifact_path_is_safe(item)],
            )
            if path.exists()
        },
    }


def artifact_path_is_safe(item):
    try:
        return project_artifact(BASE_DIR, item.get('path') or item.get('expected_path')).is_file()
    except (ValueError, OSError):
        return False


def write_reports(report: dict[str, Any], mode: str) -> None:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Evidence Gate Report",
        "",
        f"- Mode: `{mode}`",
        f"- Status: `{report['status']}`",
        f"- Generated at: `{report['generated_at']}`",
        "",
    ]
    if report["failures"]:
        lines.append("## Failures")
        lines.extend(f"- {item}" for item in report["failures"])
        lines.append("")
    if report["warnings"]:
        lines.append("## Warnings")
        lines.extend(f"- {item}" for item in report["warnings"])
        lines.append("")
    lines.append("## Questions")
    for item in report["questions"]:
        lines.append(
            f"- {item['question_id']}: {item['status']} "
            f"(results={item['has_result']}, metrics={item['metric_count']}, "
            f"conclusions={item['conclusion_count']}, figures={item['figure_count']}, tables={item['table_count']})"
        )
    REPORT_MD.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def main() -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Check whether MathModel Skill evidence is ready for formal writing.")
    parser.add_argument(
        "--mode",
        choices=("official", "quickstart"),
        default=os.environ.get("MATHMODEL_EVIDENCE_GATE_MODE", "official"),
        help="official returns non-zero on missing evidence; quickstart only warns.",
    )
    args = parser.parse_args()

    report = evaluate()
    write_reports(report, args.mode)

    print(f"证据门禁报告：{REPORT_MD}")
    if report["status"] == "PASS":
        print("✅ 证据门禁通过，可以进入正式全局写作与最终 QA。")
        return 0

    print("⚠️ 证据门禁未通过。正式论文不得把当前 Word 称为最终稿。")
    for failure in report["failures"][:12]:
        print(f" - {failure}")
    if len(report["failures"]) > 12:
        print(f" - 其余 {len(report['failures']) - 12} 项见报告。")
    return 0 if args.mode == "quickstart" else 1


if __name__ == "__main__":
    raise SystemExit(main())
