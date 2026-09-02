from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
from pathlib import Path

from pro_contracts import contract, hash_paths, output_root, read_json, sha256_file, write_json


RECOMMENDED_MODELS = ("claude fable 5", "fable 5", "gpt-5.6-sol", "gpt 5.6 sol")
EXPECTED_EDITION = "pro"
SKILL_ROOTS = ("skills", ".agents/skills", ".codex/skills", ".claude/skills", ".trae/skills")
LEGACY_ENTRY_EDITIONS = {
    "paper-workflow-orchestrator": "standard",
    "mathmodel-lite": "lite",
    "pro-workflow-orchestrator": "pro",
}


def classify(path: Path) -> str:
    name = path.name.casefold()
    suffix = path.suffix.casefold()
    if any(token in name for token in ("result", "结果", "提交", "答题纸", "template", "模板")):
        return "result_template"
    if suffix in {".csv", ".xls", ".xlsx", ".xlsm", ".parquet", ".json", ".txt"}:
        return "raw_data"
    if suffix in {".pdf", ".doc", ".docx", ".md"}:
        if any(token in name for token in ("附件", "reference", "参考", "说明")):
            return "reference_material"
        return "problem_statement"
    return "unclassified_attachment"


def find_libreoffice() -> str | None:
    candidates = [
        os.environ.get("LIBREOFFICE_PATH"),
        shutil.which("libreoffice"),
        shutil.which("soffice"),
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate).resolve())
    return None


def mathmodel_installations(project_root: Path) -> list[dict[str, str | None]]:
    found: list[dict[str, str | None]] = []
    for root_text in SKILL_ROOTS:
        skill_root = project_root / Path(root_text)
        if not skill_root.is_dir():
            continue
        for child in sorted(path for path in skill_root.iterdir() if path.is_dir()):
            marker_path = child / "MATHMODEL_EDITION.json"
            marker: dict[str, object] = {}
            marker_error: str | None = None
            if marker_path.is_file():
                try:
                    value = json.loads(marker_path.read_text(encoding="utf-8"))
                    marker = value if isinstance(value, dict) else {}
                    if marker.get("product") not in (None, "", "MathModel-Skill"):
                        continue
                except Exception as exc:
                    marker_error = f"{type(exc).__name__}: {exc}"
            legacy_edition = LEGACY_ENTRY_EDITIONS.get(child.name)
            edition = str(marker.get("edition") or legacy_edition or "").strip().lower()
            if edition not in {"standard", "lite", "pro"}:
                continue
            found.append({
                "edition": edition,
                "version": str(marker.get("version") or "legacy-unmarked"),
                "entry_skill": str(marker.get("entry_skill") or child.name),
                "skill_root": root_text,
                "path": child.relative_to(project_root).as_posix(),
                "marker": marker_path.relative_to(project_root).as_posix() if marker_path.is_file() else None,
                "marker_error": marker_error,
            })
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize the MathModel Skill Pro P0 contracts.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--platform", choices=("codex", "claude-code"), required=True)
    parser.add_argument("--model", required=True, help="User-declared model name.")
    parser.add_argument("--reasoning", default="unspecified")
    parser.add_argument("--multi-agent", choices=("available", "unavailable", "unknown"), default="unknown")
    parser.add_argument("--network", choices=("available", "unavailable", "unknown"), default="unknown")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    out = output_root(project_root, args.output_root)
    problem_root = project_root / "problem_files"
    files = sorted((path for path in problem_root.rglob("*") if path.is_file()), key=lambda p: p.as_posix()) if problem_root.is_dir() else []
    installations = mathmodel_installations(project_root)
    editions = sorted({str(item["edition"]) for item in installations})
    installed_conflicts = [item for item in installations if item["edition"] != EXPECTED_EDITION]
    model_recommended = any(token in args.model.casefold() for token in RECOMMENDED_MODELS)
    warnings = [] if model_recommended else [
        "The declared model is outside the recommended Fable 5 / GPT-5.6 Sol Ultra profile; Pro will continue without reducing its gates."
    ]
    versions = sorted({str(item["version"]) for item in installations if item["edition"] == EXPECTED_EDITION})
    if len(versions) > 1:
        warnings.append("Multiple Pro versions are installed: " + ", ".join(versions))
    errors: list[str] = []
    if not files:
        errors.append("problem_files/ has no readable task or attachment files")
    if installed_conflicts:
        errors.append("mixed MathModel editions detected: " + ", ".join(str(item["path"]) for item in installed_conflicts))
    for item in installations:
        if item.get("marker_error"):
            errors.append(f"unreadable edition marker {item['marker']}: {item['marker_error']}")

    out.mkdir(parents=True, exist_ok=True)
    for relative in (
        "analysis/independent", "research", "experiments", "evidence", "reviews", "paper",
        "qa", "code", "context", "data_cleaned", "figures", "tables",
    ):
        (out / relative).mkdir(parents=True, exist_ok=True)

    manifest_files = [
        {
            "path": path.relative_to(project_root).as_posix(),
            "role": classify(path),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in files
    ]
    input_hashes = hash_paths(files, project_root)
    write_json(out / "input_manifest.json", contract(
        producer_role="p0-input-preflight",
        status="PASS" if not errors else "BLOCKED",
        input_hashes=input_hashes,
        files=manifest_files,
        classification_counts={role: sum(item["role"] == role for item in manifest_files) for role in sorted({item["role"] for item in manifest_files})},
        errors=errors,
    ))
    config = contract(
        producer_role="p0-capability-preflight",
        status="PASS" if not errors else "BLOCKED",
        input_hashes={"input_manifest.json": sha256_file(out / "input_manifest.json")},
        version="3.0.0-pro.2",
        platform=args.platform,
        declared_model=args.model,
        recommended_model=model_recommended,
        reasoning_effort=args.reasoning,
        checkpoint_mode="required",
        research_policy="public_sources_only_without_explicit_authorization",
        delivery_formats=["docx", "pdf"],
        output_root="paper_output_pro",
        capabilities={
            "python": platform.python_version(),
            "python_executable": sys.executable,
            "libreoffice": find_libreoffice(),
            "multi_agent": args.multi_agent,
            "network": args.network,
        },
        mathmodel_installation={
            "expected_edition": EXPECTED_EDITION,
            "detected_editions": editions,
            "installations": installations,
        },
        warnings=warnings,
        errors=errors,
    )
    write_json(out / "pro_config.json", config)
    ledger_path = out / "checkpoint_ledger.json"
    if not ledger_path.exists():
        write_json(ledger_path, contract(
            producer_role="pro-workflow-orchestrator",
            status="PENDING",
            input_hashes={"pro_config.json": sha256_file(out / "pro_config.json")},
            checkpoints={str(i): {"status": "PENDING", "decision": None, "decided_at_utc": None, "artifact_hashes": {}, "approval_hash": None} for i in range(1, 4)},
        ))
    print(f"[{'PASS' if not errors else 'BLOCKED'}] Pro preflight: {out}")
    for warning in warnings:
        print(f"[WARNING] {warning}")
    for error in errors:
        print(f"[ERROR] {error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
