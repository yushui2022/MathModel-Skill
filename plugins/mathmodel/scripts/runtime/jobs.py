"""Atomic project job admission and durable worker supervision."""
from __future__ import annotations
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import uuid
import platform
from datetime import datetime, timezone
from pathlib import Path
from .safety import contained_file, process_identity, spawn_options, terminate_tree, reap_process, execution_environment, safe_files, file_hash, atomic_json, MAX_LOG_PAGE
from .locks import FileLock


def _core():
    try:
        import workbench
    except ModuleNotFoundError:
        from .. import workbench
    return workbench


def job_command(root: Path, job_type: str, options=None):
    core = _core()
    if job_type not in core.JOB_TYPES:
        raise ValueError("unsupported job type")
    options = {} if options is None else options
    if not isinstance(options, dict):
        raise ValueError("options must be an object")
    layout = core.core_layout(root)
    if layout["edition"] == "pro":
        allowed = {"preflight": {"model", "reasoning", "optimization_check_profile"}, "model_run": {"spec"}, "evidence_check": set(), "format_check": set(), "final_check": set()}[job_type]
        if set(options) - allowed:
            raise ValueError("unsupported job option")
        names = {"preflight": "pro_preflight.py", "model_run": "pro_run_experiment.py", "evidence_check": "pro_status.py", "format_check": "pro_format_check.py", "final_check": "pro_gate.py"}
        script = layout["scripts"] / names[job_type]
        command = [sys.executable, "-B", "-u", str(script), "--project-root", str(root)]
        if job_type == "preflight":
            if not all(isinstance(options.get(k), str) and 0 < len(options[k]) <= 100 for k in ("model", "reasoning")):
                raise ValueError("Pro 预检需要用户实际声明的 model 和 reasoning")
            command += ["--platform", "codex", "--model", options["model"], "--reasoning", options["reasoning"]]
            options = {**options, "optimization_check_profile": options.get("optimization_check_profile", "linear-v1")}
            if options["optimization_check_profile"] != "linear-v1":
                raise ValueError("unsupported optimization check profile")
            command += ["--optimization-check-profile", options["optimization_check_profile"]]
        elif job_type == "model_run":
            relative = str(options.get("spec", "")).removeprefix("paper_output_pro/")
            if not relative.startswith("code/") or not relative.endswith(".json"):
                raise ValueError("spec 必须是 paper_output_pro/code 下的 JSON 实验规格")
            contained_file(layout["output"], relative)
            command += ["--spec", relative]
        elif job_type == "evidence_check":
            # This verifies current checkpoints only. It never invents CP3 approval.
            command += ["--format", "json", "--fail-if-blocked", "--require-through", "P5"]
        stage = {"preflight": "P0", "model_run": "P3", "evidence_check": "P5", "format_check": "P9", "final_check": "P9"}[job_type]
    else:
        if job_type == "final_check":
            raise ValueError("final_check requires the Pro core")
        if options:
            raise ValueError("Standard jobs do not accept options")
        scripts = {"preflight": layout["scripts"] / "preflight_check.py", "model_run": root / "paper_output/code/modeling/run_modeling.py",
                   "evidence_check": layout["skills"] / "quality-assurance-auditor/scripts/evidence_gate.py",
                   "format_check": layout["skills"] / "paper-formal-writer/scripts/check_paper_format.py"}
        script = scripts[job_type]
        if job_type == "model_run":
            script = contained_file(root, "paper_output/code/modeling/run_modeling.py")
        command = [sys.executable, "-B", "-u", str(script)]
        if job_type == "evidence_check":
            command += ["--mode", "official"]
        if job_type == "format_check":
            command += ["--render", "required"]
        stage = {"preflight": "S0", "model_run": "S5", "evidence_check": "S6", "format_check": "S8"}[job_type]
    if not script.is_file():
        raise FileNotFoundError(f"活动核心缺少任务脚本：{script.name}")
    return command, stage, options


def fingerprint_payload(root, job_type, options, command):
    """Bind idempotency to effective inputs, installed core and the actual Python env."""
    from .service import runtime_fingerprint
    root = Path(root)
    layout = _core().core_layout(root)
    paths = set()
    for value in command:
        if isinstance(value, str) and value.endswith(".py") and Path(value).is_file():
            paths.add(Path(value).resolve())
    if job_type == "model_run" and options.get("spec"):
        relative = options["spec"].removeprefix("paper_output_pro/")
        spec_path = contained_file(layout["output"], relative)
        paths.add(spec_path)
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        if not isinstance(spec, dict):
            raise ValueError("run specification must be an object")
        dependencies = [spec.get("script"), *spec.get("dependencies", []), *spec.get("inputs", [])]
        if any(not isinstance(p, str) for p in dependencies):
            raise ValueError("declared experiment files must be relative paths")
        paths.update(contained_file(layout["output"], p) for p in dependencies)
    elif job_type != "model_run":
        paths.update(safe_files(root / "problem_files"))
    if job_type in {"evidence_check", "format_check", "final_check"}:
        # Gate-generated summaries are outputs, not new effective input evidence.
        paths.update(p for p in safe_files(layout["output"]) if p.name not in {"pro_gate_report.json", "pro_gate_report.md", "format_check_report.json", "format_check_report.md"})
    packages = sorted({f"{d.metadata['Name']}=={d.version}" for d in importlib.metadata.distributions() if d.metadata.get("Name")})
    # Windows marketing release names can differ for detached processes. Kernel
    # version and architecture are the stable execution-environment identity.
    os_version = str(sys.getwindowsversion()) if os.name == "nt" else platform.release()
    environment = {"executable": sys.executable, "python": sys.version, "platform": [sys.platform, platform.machine(), os_version], "packages": packages,
                   "variables_sha256": hashlib.sha256(json.dumps(execution_environment(), sort_keys=True).encode()).hexdigest()}
    payload = {"type": job_type, "options": options, "command": command, "runtime": runtime_fingerprint(), "environment": environment,
               "files": {str(path): file_hash(path) for path in sorted(paths)}}
    return payload


def job_fingerprint(root, job_type, options, command):
    return hashlib.sha256(json.dumps(fingerprint_payload(root, job_type, options, command), sort_keys=True).encode()).hexdigest()


class JobRunner:
    """Construction never changes another owner's running tasks."""
    def __init__(self, state, owner=None):
        self.state = state
        self.owner = owner or uuid.uuid4().hex
        state.initialize()

    def recover(self):
        core = _core()
        for row in self.state._rows("SELECT * FROM jobs WHERE status IN ('queued','running','cancelling')"):
            identity = process_identity(row.get("pid") or 0)
            if identity and identity == row.get("process_identity"):
                continue
            created = datetime.fromisoformat(row["created_at"])
            if row["status"] == "queued" and (datetime.now(timezone.utc) - created).total_seconds() < 10:
                continue
            terminate_tree(row.get("child_pid") or 0, row.get("child_identity"))
            status = "cancelled" if row.get("cancel_requested") else "interrupted"
            with self.state._db() as db:
                db.execute("UPDATE jobs SET status=?,finished_at=?,error=? WHERE id=? AND status IN ('queued','running','cancelling')",
                           (status, core.utcnow(), "实验进程已结束；保留日志，可重试任务。", row["id"]))
                self.state._event(db, row["stage"], status, "实验进程已结束；保留日志，可重试任务。", row["id"])

    def start(self, job_type, options=None, idempotency_key=None, *, retry_of=None):
        command, stage, options = job_command(self.state.root, job_type, options)
        if idempotency_key is not None and (not isinstance(idempotency_key, str) or not 1 <= len(idempotency_key) <= 128):
            raise ValueError("invalid idempotency key")
        details = fingerprint_payload(self.state.root, job_type, options, command)
        fingerprint = hashlib.sha256(json.dumps(details, sort_keys=True).encode()).hexdigest()
        jid = uuid.uuid4().hex
        with self.state._db() as db:
            if idempotency_key:
                row = db.execute("SELECT job_id,fingerprint,retry_of FROM job_requests WHERE request_key=?", (idempotency_key,)).fetchone()
                if row:
                    if row["fingerprint"] != fingerprint or row["retry_of"] != retry_of:
                        raise ValueError("idempotency key reused with different parameters")
                    return row["job_id"]
            active = db.execute("SELECT id,fingerprint FROM jobs WHERE status IN ('queued','running','cancelling') ORDER BY rowid").fetchall()
            for row in active:
                if row["fingerprint"] == fingerprint:
                    if idempotency_key:
                        db.execute("INSERT INTO job_requests(request_key,job_id,fingerprint,retry_of) VALUES(?,?,?,?)",
                                   (idempotency_key, row["id"], fingerprint, retry_of))
                    return row["id"]
            if len(active) >= 16:
                raise RuntimeError("项目实验队列已满（16 个）；请等待或取消排队任务。")
            db.execute("INSERT INTO jobs(id,type,stage,status,command,options,request_key,fingerprint,fingerprint_details,retry_of,owner,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                       (jid, job_type, stage, "queued", json.dumps(command, ensure_ascii=False), json.dumps(options, ensure_ascii=False),
                        idempotency_key, fingerprint, json.dumps(details, ensure_ascii=False), retry_of, self.owner, _core().utcnow()))
            if idempotency_key:
                db.execute("INSERT INTO job_requests(request_key,job_id,fingerprint,retry_of) VALUES(?,?,?,?)", (idempotency_key, jid, fingerprint, retry_of))
            self.state._bump(db)
        try:
            worker = Path(__file__).with_name("worker.py").resolve()
            proc = subprocess.Popen([sys.executable, "-B", "-u", str(worker), "--project-root", str(self.state.root), "--job-id", jid],
                                    cwd=self.state.root, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    env=execution_environment(), **spawn_options(detached=True))
            with self.state._db() as db:
                db.execute("UPDATE jobs SET pid=?,process_identity=? WHERE id=? AND pid IS NULL", (proc.pid, process_identity(proc.pid), jid))
            reap_process(proc)
        except OSError as exc:
            with self.state._db() as db:
                db.execute("UPDATE jobs SET status='failed',finished_at=?,error=? WHERE id=?", (_core().utcnow(), str(exc), jid))
                self.state._event(db, stage, "failed", str(exc), jid)
            raise RuntimeError(f"无法启动实验：{exc}") from exc
        return jid

    def get(self, job_id, cursor=0, limit=MAX_LOG_PAGE):
        return self.state.job(job_id, cursor, limit)

    def retry(self, job_id, idempotency_key=None):
        """Create a new attempt while keeping the previous run and spec immutable."""
        key = idempotency_key or ("retry:" + job_id)
        if not isinstance(key, str) or not 1 <= len(key) <= 128:
            raise ValueError("invalid retry idempotency key")
        with FileLock(self.state.state_dir / "retry.lock", 30):
            previous = self.state._rows("SELECT * FROM jobs WHERE id=?", (job_id,))
            if not previous:
                raise KeyError(job_id)
            source = previous[0]
            if source["status"] not in {"failed", "cancelled", "interrupted"}:
                raise ValueError("只能重试失败、取消或中断的任务")
            duplicate = self.state._rows("SELECT j.type,j.options,r.retry_of FROM job_requests r JOIN jobs j ON j.id=r.job_id WHERE r.request_key=?", (key,))
            if duplicate:
                if duplicate[0]["retry_of"] != job_id:
                    raise ValueError("retry idempotency key belongs to another source job")
                return self.start(duplicate[0]["type"], json.loads(duplicate[0]["options"]), key, retry_of=job_id)
            options = json.loads(source["options"] or "{}")
            layout = _core().core_layout(self.state.root)
            if source["type"] == "model_run" and layout["edition"] == "pro":
                relative = str(options.get("spec", "")).removeprefix("paper_output_pro/")
                if not relative.startswith("code/"):
                    raise ValueError("原任务缺少有效的实验规格")
                spec_path = contained_file(layout["output"], relative, limit=1024 * 1024)
                spec = json.loads(spec_path.read_text(encoding="utf-8"))
                if not isinstance(spec, dict) or not isinstance(spec.get("run_id"), str):
                    raise ValueError("原实验规格缺少 run_id")
                suffix = uuid.uuid4().hex[:12]
                spec["run_id"] = spec["run_id"][:64] + "-retry-" + suffix
                spec["retry_provenance"] = {"source_job_id": job_id, "source_spec": relative,
                                            "source_spec_sha256": file_hash(spec_path), "created_at": _core().utcnow()}
                attempt = spec_path.with_name(spec_path.stem[:80] + ".retry-" + suffix + ".json")
                atomic_json(attempt, spec)
                options["spec"] = attempt.relative_to(layout["output"]).as_posix()
            return self.start(source["type"], options, key, retry_of=job_id)

    def cancel(self, job_id):
        with self.state._db() as db:
            row = db.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row is None:
                raise KeyError(job_id)
            if row["status"] not in _core().ACTIVE_STATUSES:
                return row["status"] == "cancelled"
            db.execute("UPDATE jobs SET cancel_requested=1,status='cancelling' WHERE id=?", (job_id,))
            self.state._bump(db)
        return True
