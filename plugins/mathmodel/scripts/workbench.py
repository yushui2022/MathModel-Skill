#!/usr/bin/env python3
"""Local state and controlled job runner for the MathModel Codex plugin.

The module deliberately uses only the Python standard library.  It is safe to
import from both the dashboard and an optional MCP adapter and never accepts
arbitrary shell text.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STAGES = [f"S{i}" for i in range(9)]
JOB_TYPES = {"preflight", "model_run", "evidence_check", "format_check"}
SAFE_ARTIFACT_ROOTS = ("paper_output",)
_GUARD_LOCK = threading.Lock()


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def project_id(root: Path) -> str:
    return hashlib.sha256(str(root.resolve()).encode("utf-8")).hexdigest()[:16]


class WorkbenchState:
    """Per-project SQLite state with a JSON snapshot for old dashboard clients."""

    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        self.state_dir = self.root / ".mathmodel"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.state_dir / "workbench.sqlite3"
        self._lock = threading.RLock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15)
        conn.row_factory = sqlite3.Row
        # DELETE mode is portable to read-only plugin caches and Windows temp
        # directories; SQLite still provides transactional persistence.
        conn.execute("PRAGMA journal_mode=DELETE")
        return conn

    @contextmanager
    def _db(self):
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS events(
              id INTEGER PRIMARY KEY AUTOINCREMENT, revision INTEGER NOT NULL,
              stage TEXT NOT NULL, status TEXT NOT NULL, message TEXT,
              current_task TEXT, artifacts TEXT, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS jobs(
              id TEXT PRIMARY KEY, type TEXT NOT NULL, stage TEXT NOT NULL,
              status TEXT NOT NULL, command TEXT NOT NULL, started_at TEXT,
              finished_at TEXT, exit_code INTEGER, log TEXT, error TEXT,
              created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS artifacts(
              id TEXT PRIMARY KEY, path TEXT NOT NULL, kind TEXT NOT NULL,
              sha256 TEXT NOT NULL, size INTEGER NOT NULL, updated_at TEXT NOT NULL);
            """)

    def close(self) -> None:
        """Checkpoint the WAL before a project service is shut down."""
        try:
            with self._db() as db:
                db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except sqlite3.Error:
            pass

    def record_event(self, stage: str, status: str, message: str = "", current_task: str = "", artifacts: list[str] | None = None) -> dict[str, Any]:
        if stage not in STAGES or status not in {"pending", "running", "awaiting_validation", "passed", "failed", "stale"}:
            raise ValueError("invalid stage or status")
        artifacts = artifacts or []
        with self._lock, self._db() as db:
            revision = int(db.execute("SELECT COALESCE(MAX(revision),0)+1 FROM events").fetchone()[0])
            event = {"revision": revision, "stage": stage, "status": status, "message": message, "current_task": current_task, "artifacts": artifacts, "timestamp": utcnow()}
            db.execute("INSERT INTO events(revision,stage,status,message,current_task,artifacts,created_at) VALUES(?,?,?,?,?,?,?)", (revision, stage, status, message, current_task, json.dumps(artifacts, ensure_ascii=False), event["timestamp"]))
            db.commit()
        self._write_snapshot()
        return event

    def _guard_status(self) -> dict[str, Any]:
        script = self.root / ".agents" / "skills" / "paper-workflow-orchestrator" / "scripts" / "workflow_guard.py"
        if not script.exists():
            script = Path(__file__).resolve().parents[1] / "skills" / "paper-workflow-orchestrator" / "scripts" / "workflow_guard.py"
        if not script.exists():
            return {"status": "UNKNOWN", "steps": [], "next_action": "安装 MathModel Skills 后运行预检。"}
        try:
            # Import under an isolated cwd because the existing guard binds cwd at import time.
            import runpy
            with _GUARD_LOCK:
                old = Path.cwd()
                os.chdir(self.root)
                try:
                    module = runpy.run_path(str(script))
                    result = module["evaluate_status"]()
                finally:
                    os.chdir(old)
            return result
        except Exception as exc:
            try: os.chdir(old)
            except Exception: pass
            return {"status": "UNKNOWN", "steps": [], "next_action": f"无法读取 Guard 状态：{exc}"}

    def _write_snapshot(self) -> None:
        guard = self._guard_status()
        with self._db() as db:
            rows = db.execute("SELECT * FROM events ORDER BY id DESC LIMIT 100").fetchall()
            job_rows = db.execute("SELECT id,type,status,started_at,finished_at,exit_code,substr(COALESCE(log,''),1,200000) AS log FROM jobs ORDER BY created_at DESC LIMIT 30").fetchall()
        history = []
        for row in reversed(rows):
            item = dict(row); item["artifacts"] = json.loads(item.pop("artifacts") or "[]"); item["timestamp"] = item.pop("created_at")
            history.append(item)
        current = history[-1] if history else {"stage": "S0", "status": "pending", "message": "尚未记录工作流活动", "artifacts": []}
        # Guard is the source of truth for completion. Events describe activity
        # only and can never promote a stage to PASS.
        step_rows = guard.get("steps") if isinstance(guard, dict) else []
        step_status = {str(x.get("step")): str(x.get("status", "")).lower() for x in step_rows if isinstance(x, dict)}
        verified = sum(value == "pass" for value in step_status.values())
        next_step = str(guard.get("next_step") or guard.get("current_step") or "S0") if isinstance(guard, dict) else "S0"
        if isinstance(guard, dict) and guard.get("status") == "COMPLETE": next_step = "S8"
        raw_authoritative = "passed" if isinstance(guard, dict) and guard.get("status") == "COMPLETE" else step_status.get(next_step, "pending")
        authoritative = {"pass": "passed", "fail": "failed", "failed": "failed", "invalid": "stale"}.get(raw_authoritative, raw_authoritative)
        activity = current.get("status", "pending")
        if activity == "passed" and authoritative != "passed": activity = "awaiting_validation"
        stages = []
        for stage in STAGES:
            raw = step_status.get(stage, "")
            mapped = {"pass": "passed", "fail": "failed", "failed": "failed", "invalid": "stale"}.get(raw)
            if mapped is None:
                mapped = "validating" if stage == next_step and activity == "awaiting_validation" else "pending"
            failure = next((x.get("failures", [""])[0] for x in step_rows if x.get("step") == stage and x.get("failures")), "")
            stages.append({"code": stage, "status": mapped, "message": failure})
        payload = {
            "schema_version": "2.0", "project": self.root.name,
            "project_id": project_id(self.root), "project_root": str(self.root),
            "stage": next_step, "status": authoritative, "activity_status": activity,
            "message": (guard.get("failures") or [guard.get("next_action", "")])[0] if isinstance(guard, dict) and guard.get("failures") else current.get("message", ""),
            "current_task": current.get("current_task", ""),
            "next_action": guard.get("next_action", "") if isinstance(guard, dict) else "",
            "recommended_skill": guard.get("recommended_skill", "") if isinstance(guard, dict) else "",
            "verified_count": verified, "stages": stages, "artifacts": self.artifacts(),
            "jobs": [dict(row) for row in job_rows],
            "logs": (job_rows[0]["log"] if job_rows else ""), "updated_at": utcnow(),
            "history": history, "guard": guard,
            "revision": history[-1].get("revision", 0) if history else 0,
        }
        tmp = self.state_dir / "status.json.tmp"
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, self.state_dir / "status.json")
        with (self.state_dir / "events.jsonl").open("w", encoding="utf-8") as fh:
            for item in history: fh.write(json.dumps(item, ensure_ascii=False) + "\n")

    def status(self) -> dict[str, Any]:
        self._write_snapshot()
        return json.loads((self.state_dir / "status.json").read_text(encoding="utf-8"))

    def register_artifacts(self) -> list[dict[str, Any]]:
        found = []
        base = self.root / "paper_output"
        if not base.is_dir(): return found
        with self._lock, self._db() as db:
            for path in base.rglob("*"):
                if not path.is_file() or path.is_symlink(): continue
                rel = path.relative_to(self.root).as_posix()
                if path.stat().st_size > 25 * 1024 * 1024: continue
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                aid = hashlib.sha256(rel.encode()).hexdigest()[:20]
                kind = path.suffix.lower().lstrip(".") or "file"
                db.execute("INSERT OR REPLACE INTO artifacts(id,path,kind,sha256,size,updated_at) VALUES(?,?,?,?,?,?)", (aid, rel, kind, digest, path.stat().st_size, utcnow()))
                found.append({"id": aid, "path": rel, "kind": kind, "sha256": digest, "size": path.stat().st_size})
            db.commit()
        return found

    def artifacts(self, kind: str | None = None) -> list[dict[str, Any]]:
        self.register_artifacts()
        with self._db() as db:
            q = "SELECT id,path,kind,sha256,size,updated_at FROM artifacts"; args: tuple[Any, ...] = ()
            if kind: q += " WHERE kind=?"; args = (kind,)
            return [dict(r) for r in db.execute(q + " ORDER BY path", args)]

    def read_artifact(self, artifact_id: str) -> tuple[Path, dict[str, Any]]:
        self.register_artifacts()
        with self._db() as db:
            row = db.execute("SELECT * FROM artifacts WHERE id=?", (artifact_id,)).fetchone()
        if not row: raise FileNotFoundError("unknown artifact")
        target = (self.root / row["path"]).resolve()
        if self.root / "paper_output" not in target.parents or target.is_symlink() or not target.is_file(): raise PermissionError("artifact outside allowlist")
        return target, dict(row)


class JobRunner:
    def __init__(self, state: WorkbenchState):
        self.state, self.jobs, self.lock = state, {}, threading.Lock()
        # A process restart cannot resume an orphaned child safely; preserve it
        # as a recovered failure so the UI never shows a phantom running job.
        with self.state._db() as db:
            db.execute("UPDATE jobs SET status='failed', finished_at=?, error=? WHERE status='running'", (utcnow(), "服务重启，原任务未恢复"))
    def start(self, job_type: str) -> str:
        if job_type not in JOB_TYPES: raise ValueError("unsupported job type")
        scripts = {"preflight": self.state.root / ".agents/skills/paper-workflow-orchestrator/scripts/preflight_check.py", "model_run": self.state.root / "paper_output/code/modeling/run_modeling.py", "evidence_check": self.state.root / ".agents/skills/quality-assurance-auditor/scripts/evidence_gate.py", "format_check": self.state.root / "paper_output/code/paper-formal-writer/check_paper_format.py"}
        plugin_skills = Path(__file__).resolve().parents[1] / "skills"
        fallbacks = {"preflight": plugin_skills / "paper-workflow-orchestrator/scripts/preflight_check.py", "evidence_check": plugin_skills / "quality-assurance-auditor/scripts/evidence_gate.py"}
        for key, fallback in fallbacks.items():
            if not scripts[key].exists() and fallback.exists(): scripts[key] = fallback
        commands = {"preflight": [sys.executable, str(scripts["preflight"])], "model_run": [sys.executable, str(scripts["model_run"])], "evidence_check": [sys.executable, str(scripts["evidence_check"]), "--mode", "official"], "format_check": [sys.executable, str(scripts["format_check"])]}
        script = scripts[job_type]
        if not script.exists(): raise FileNotFoundError(str(script))
        job_id = uuid.uuid4().hex
        stage = {"preflight":"S0","model_run":"S5","evidence_check":"S6","format_check":"S8"}[job_type]
        with self.lock:
            with self.state._db() as db:
                persisted = db.execute("SELECT id,type FROM jobs WHERE status='running' ORDER BY created_at DESC LIMIT 1").fetchone()
            if persisted:
                if persisted["type"] == job_type:
                    return str(persisted["id"])
                raise RuntimeError(f"已有任务运行中：{persisted['type']}")
            for existing_id, existing in self.jobs.items():
                if existing.get("status") == "running":
                    if existing.get("type") == job_type:
                        return existing_id
                    raise RuntimeError(f"已有任务运行中：{existing.get('type')}")
            self.jobs[job_id] = {"id": job_id, "type": job_type, "status": "running", "log": "", "process": None}
        with self.state._db() as db:
            db.execute("INSERT INTO jobs(id,type,stage,status,command,started_at,created_at) VALUES(?,?,?,?,?,?,?)", (job_id, job_type, stage, "running", json.dumps(commands[job_type], ensure_ascii=False), utcnow(), utcnow()))
        self.state.record_event(stage, "running", f"开始执行 {job_type}", job_id)
        thread = threading.Thread(target=self._run, args=(job_id, commands[job_type], self.state.root), daemon=True); thread.start()
        return job_id
    def _run(self, job_id: str, command: list[str], cwd: Path) -> None:
        try:
            proc = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        except Exception as exc:
            message = f"无法启动任务：{exc}"
            self.jobs[job_id].update(status="failed", log=message, exit_code=-1)
            with self.state._db() as db: db.execute("UPDATE jobs SET status='failed',finished_at=?,exit_code=-1,log=?,error=? WHERE id=?", (utcnow(), message, message, job_id))
            stage = {"preflight":"S0","model_run":"S5","evidence_check":"S6","format_check":"S8"}[self.jobs[job_id]["type"]]
            self.state.record_event(stage, "failed", message, job_id)
            return
        self.jobs[job_id]["process"] = proc
        out, _ = proc.communicate(); ok = proc.returncode == 0
        status = "passed" if ok else "failed"
        self.jobs[job_id].update(status=status, log=out[-200000:], exit_code=proc.returncode)
        with self.state._db() as db:
            db.execute("UPDATE jobs SET status=?,finished_at=?,exit_code=?,log=? WHERE id=?", (status, utcnow(), proc.returncode, out[-200000:], job_id))
        stage = {"preflight":"S0","model_run":"S5","evidence_check":"S6","format_check":"S8"}[self.jobs[job_id]["type"]]
        self.state.record_event(stage, "passed" if ok else "failed", out[-2000:], job_id)
    def get(self, job_id: str) -> dict[str, Any]:
        if job_id in self.jobs: return {k:v for k,v in self.jobs[job_id].items() if k != "process"}
        with self.state._db() as db:
            row = db.execute("SELECT id,type,status,stage,started_at,finished_at,exit_code,log,error FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not row: raise KeyError(job_id)
        return dict(row)
    def cancel(self, job_id: str) -> bool:
        item = self.jobs.get(job_id); proc = item and item.get("process")
        if proc and proc.poll() is None:
            proc.terminate(); item["status"] = "cancelled"
            with self.state._db() as db: db.execute("UPDATE jobs SET status=?,finished_at=? WHERE id=?", ("cancelled", utcnow(), job_id))
            return True
        return False
