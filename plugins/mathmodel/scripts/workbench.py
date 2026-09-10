"""Shared project state. Queries never create files or write QA reports."""
from __future__ import annotations
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import threading
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

try:
    from runtime.safety import MAX_ARTIFACT_BYTES, MAX_LOG_BYTES, MAX_LOG_PAGE, atomic_json, contained_file, file_hash, is_link, safe_files
    from runtime.locks import FileLock
except ModuleNotFoundError:
    from .runtime.safety import MAX_ARTIFACT_BYTES, MAX_LOG_BYTES, MAX_LOG_PAGE, atomic_json, contained_file, file_hash, is_link, safe_files
    from .runtime.locks import FileLock

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
STAGES = [f"S{i}" for i in range(9)]
PRO_STAGES = [f"P{i}" for i in range(10)]
JOB_TYPES = {"preflight", "model_run", "evidence_check", "format_check", "final_check"}
ACTIVE_STATUSES = ("queued", "running", "cancelling")
SAFE_ARTIFACT_ROOTS = ("problem_files", "paper_output", "paper_output_pro")
PROJECT_TREE_ROOTS = SAFE_ARTIFACT_ROOTS
MAX_PROJECT_FILE_BYTES = MAX_ARTIFACT_BYTES


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def project_id(root: Path):
    return hashlib.sha256(os.path.normcase(str(root.resolve())).encode()).hexdigest()[:16]


def core_layout(root):
    root = Path(root).resolve()
    skills = PLUGIN_ROOT / "skills"
    pro = skills / "pro-workflow-orchestrator/scripts"
    standard = skills / "paper-workflow-orchestrator/scripts"
    legacy = (root / "paper_output").is_dir() and not (root / "paper_output_pro").is_dir()
    use_pro = (pro / "pro_status.py").is_file() and not (legacy and standard.is_dir())
    return {"edition": "pro" if use_pro else "standard", "skills": skills, "scripts": pro if use_pro else standard,
            "output": root / ("paper_output_pro" if use_pro else "paper_output"), "stages": PRO_STAGES if use_pro else STAGES}


def evaluate_guard(root):
    """Pure subprocess query; no shared cwd mutation, bytecode or QA writes."""
    root = Path(root).expanduser().resolve()
    layout = core_layout(root)
    if layout["edition"] == "pro":
        script = layout["scripts"] / "pro_status.py"
        command = [sys.executable, "-B", str(script), "--project-root", str(root), "--format", "json"]
    else:
        script = layout["scripts"] / "workflow_guard.py"
        code = "import json,runpy,sys; m=runpy.run_path(sys.argv[1]); print(json.dumps(m['evaluate_status'](),ensure_ascii=False))"
        command = [sys.executable, "-B", "-c", code, str(script)]
    fallback = {"status": "UNKNOWN", "edition": layout["edition"], "steps": [], "current_step": "", "next_step": layout["stages"][0],
                "recommended_skill": "pro-workflow-orchestrator" if layout["edition"] == "pro" else "paper-workflow-orchestrator"}
    try:
        if not script.is_file():
            raise FileNotFoundError("活动插件缺少 Guard 脚本")
        result = subprocess.run(command, cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=40,
                                env={**os.environ, "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"})
        data = json.loads(result.stdout)
        if not isinstance(data, dict):
            raise ValueError("Guard response must be an object")
        data.setdefault("edition", layout["edition"])
        return data
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return {**fallback, "next_action": f"无法读取 Guard 状态：{exc}", "failures": [str(exc)]}


def _stable(value):
    if isinstance(value, dict):
        return {k: _stable(v) for k, v in value.items() if k not in {"generated_at", "updated_at", "revision"}}
    return [_stable(v) for v in value] if isinstance(value, list) else value


class WorkbenchState:
    def __init__(self, root):
        self.root = Path(root).expanduser().resolve()
        if not self.root.is_dir():
            raise ValueError("比赛项目目录不存在")
        self.state_dir = self.root / ".mathmodel"
        self.db_path = self.state_dir / "workbench.sqlite3"
        self._lock = threading.RLock()

    @contextmanager
    def _db(self, *, readonly=False):
        if is_link(self.state_dir) or is_link(self.db_path):
            raise PermissionError("linked runtime state is not allowed")
        conn = sqlite3.connect(self.db_path.as_uri() + "?mode=ro", uri=True, timeout=15) if readonly else sqlite3.connect(self.db_path, timeout=15)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA busy_timeout=15000")
            if not readonly:
                conn.execute("BEGIN IMMEDIATE")
            yield conn
            if not readonly:
                conn.commit()
        except Exception:
            if not readonly:
                conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self):
        if is_link(self.state_dir) or is_link(self.db_path):
            raise PermissionError("linked runtime state is not allowed")
        self.state_dir.mkdir(parents=True, exist_ok=True)
        with FileLock(self.state_dir / "schema.lock", 30), self._db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            INSERT OR IGNORE INTO meta(key,value) VALUES('revision','0');
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,revision INTEGER NOT NULL,
              stage TEXT NOT NULL,status TEXT NOT NULL,message TEXT,current_task TEXT,artifacts TEXT,created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,type TEXT NOT NULL,stage TEXT NOT NULL,status TEXT NOT NULL,
              command TEXT NOT NULL,started_at TEXT,finished_at TEXT,exit_code INTEGER,log TEXT,error TEXT,created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS artifacts(id TEXT PRIMARY KEY,path TEXT NOT NULL,kind TEXT NOT NULL,
              sha256 TEXT NOT NULL,size INTEGER NOT NULL,updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS job_requests(request_key TEXT PRIMARY KEY,job_id TEXT NOT NULL,fingerprint TEXT NOT NULL,retry_of TEXT);
            """)
            additions = {"options": "TEXT DEFAULT '{}'", "request_key": "TEXT", "fingerprint": "TEXT", "fingerprint_details": "TEXT", "retry_of": "TEXT", "owner": "TEXT",
                         "pid": "INTEGER", "process_identity": "TEXT", "child_pid": "INTEGER", "child_identity": "TEXT",
                         "log_size": "INTEGER DEFAULT 0", "log_truncated": "INTEGER DEFAULT 0", "cancel_requested": "INTEGER DEFAULT 0"}
            for table, columns in (("jobs", additions), ("artifacts", {"mtime_ns": "INTEGER", "ctime_ns": "INTEGER", "inode": "INTEGER"})):
                existing = {r[1] for r in db.execute(f"PRAGMA table_info({table})")}
                for key, declaration in columns.items():
                    if key not in existing:
                        db.execute(f"ALTER TABLE {table} ADD COLUMN {key} {declaration}")
            db.execute("CREATE UNIQUE INDEX IF NOT EXISTS unique_request_key ON jobs(request_key) WHERE request_key IS NOT NULL")
            db.execute("INSERT OR IGNORE INTO job_requests(request_key,job_id,fingerprint,retry_of) SELECT request_key,id,fingerprint,retry_of FROM jobs WHERE request_key IS NOT NULL AND fingerprint IS NOT NULL")

    @staticmethod
    def _bump(db):
        db.execute("UPDATE meta SET value=CAST(value AS INTEGER)+1 WHERE key='revision'")
        return int(db.execute("SELECT value FROM meta WHERE key='revision'").fetchone()[0])

    def _event(self, db, stage, status, message, task=""):
        revision = self._bump(db)
        db.execute("INSERT INTO events(revision,stage,status,message,current_task,artifacts,created_at) VALUES(?,?,?,?,?,?,?)",
                   (revision, stage, status, message[:8192], task, "[]", utcnow()))

    def close(self):
        pass

    def _rows(self, sql, args=()):
        if not self.db_path.is_file():
            return []
        try:
            with self._db(readonly=True) as db:
                return [dict(row) for row in db.execute(sql, args)]
        except sqlite3.OperationalError:
            return []

    def record_event(self, stage, status, message="", current_task="", artifacts=None):
        if stage not in STAGES + PRO_STAGES or status not in {"pending", "running", "awaiting_validation", "passed", "failed", "stale", "cancelled", "interrupted"}:
            raise ValueError("invalid stage or activity status")
        if len(message) > 8192 or len(current_task) > 256 or len(artifacts or []) > 100:
            raise ValueError("activity exceeds limits")
        self.initialize()
        with self._db() as db:
            revision = self._bump(db)
            event = {"revision": revision, "stage": stage, "status": status, "message": message,
                     "current_task": current_task, "artifacts": artifacts or [], "timestamp": utcnow()}
            db.execute("INSERT INTO events(revision,stage,status,message,current_task,artifacts,created_at) VALUES(?,?,?,?,?,?,?)",
                       (revision, stage, status, message, current_task, json.dumps(artifacts or [], ensure_ascii=False), event["timestamp"]))
        self.refresh()
        return event

    def _guard_status(self):
        return evaluate_guard(self.root)

    def artifacts(self, kind=None):
        cached = {item["path"]: item for item in self._rows("SELECT * FROM artifacts")}
        found = []
        for name in SAFE_ARTIFACT_ROOTS:
            for path in safe_files(self.root / name):
                try:
                    rel = path.relative_to(self.root).as_posix(); info = path.stat(); old = cached.get(rel, {})
                    signature = (info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_ino)
                    previous = (old.get("size"), old.get("mtime_ns"), old.get("ctime_ns"), old.get("inode"))
                    digest = old["sha256"] if signature == previous else file_hash(path)
                    item = {"id": hashlib.sha256(rel.encode()).hexdigest()[:20], "path": rel,
                            "kind": path.suffix.lower().lstrip(".") or "file", "sha256": digest, "size": info.st_size,
                            "mtime_ns": info.st_mtime_ns, "ctime_ns": info.st_ctime_ns, "inode": info.st_ino}
                    if kind is None or item["kind"] == kind:
                        found.append(item)
                except OSError:
                    continue
        return sorted(found, key=lambda item: item["path"])

    register_artifacts = artifacts

    def read_artifact(self, artifact_id):
        if not isinstance(artifact_id, str) or len(artifact_id) != 20 or any(c not in "0123456789abcdef" for c in artifact_id):
            raise FileNotFoundError("unknown artifact")
        item = next((row for row in self.artifacts() if row["id"] == artifact_id), None)
        if item is None:
            raise FileNotFoundError("unknown artifact")
        return contained_file(self.root, item["path"]), item

    def events(self, cursor=0, limit=100):
        limit = max(1, min(int(limit), 200))
        rows = self._rows("SELECT * FROM events WHERE id>? ORDER BY id LIMIT ?", (max(0, int(cursor)), limit + 1))
        page = rows[:limit]
        for row in page:
            row["artifacts"] = json.loads(row.get("artifacts") or "[]"); row["timestamp"] = row.pop("created_at")
        return {"items": page, "next_cursor": page[-1]["id"] if len(rows) > limit else None}

    def status(self):
        layout = core_layout(self.root); guard = self._guard_status()
        saved = self._rows("SELECT value FROM meta WHERE key='snapshot'")
        previous = json.loads(saved[0]["value"]) if saved else {}
        steps = [x for x in guard.get("steps", []) if isinstance(x, dict)]
        step_map = {str(x.get("step")): x for x in steps}
        codes = PRO_STAGES if guard.get("edition") == "pro" else layout["stages"]
        next_step = str(guard.get("next_step") or guard.get("current_step") or codes[0])
        history = self._rows("SELECT * FROM events ORDER BY id DESC LIMIT 100"); history.reverse()
        for item in history:
            item["artifacts"] = json.loads(item.get("artifacts") or "[]"); item["timestamp"] = item.pop("created_at")
        current = history[-1] if history else {}
        jobs = self._rows("SELECT id,type,stage,status,options,retry_of,started_at,finished_at,exit_code,error,log_size,log_truncated FROM jobs ORDER BY rowid DESC LIMIT 30")
        for job in jobs:
            job["options"] = json.loads(job.get("options") or "{}")
        active = next((j for j in jobs if j["status"] in {"running", "cancelling"}), None)
        if active is None:
            active = next((j for j in reversed(jobs) if j["status"] == "queued"), None)
        prior = {x["code"]: x["status"] for x in previous.get("stages", [])}; stages = []
        for code in codes:
            item = step_map.get(code, {}); raw = str(item.get("status", "PENDING")).upper()
            mapped = {"PASS": "passed", "FAIL": "failed", "INVALID": "stale", "UNKNOWN": "unknown"}.get(raw, "pending")
            if raw != "PASS" and prior.get(code) in {"passed", "stale"}:
                mapped = "stale"
            if active and active["stage"] == code and active["status"] != "queued":
                mapped = "running"
            failures = item.get("failures") or []
            stages.append({"code": code, "name": item.get("name", code), "status": mapped, "validation_status": raw,
                           "message": str(failures[0]) if failures else "", "failures": failures})
        authoritative = "passed" if guard.get("status") == "COMPLETE" else next((s["status"] for s in stages if s["code"] == next_step), "pending")
        activity = active["status"] if active else current.get("status", "pending")
        if activity == "passed":
            activity = "awaiting_validation"
        revisions = self._rows("SELECT value FROM meta WHERE key='revision'")
        return {"schema_version": "3.0", "project": self.root.name, "project_id": project_id(self.root), "project_root": str(self.root),
                "core_edition": layout["edition"], "output_root": str(layout["output"]), "stage": next_step, "stage_count": len(codes),
                "status": authoritative, "activity_status": activity, "message": str((guard.get("failures") or [current.get("message", "")])[0]),
                "current_task": active["id"] if active else current.get("current_task", ""), "next_action": guard.get("next_action", ""),
                "recommended_skill": guard.get("recommended_skill", ""), "verified_count": sum(str(x.get("status")).upper() == "PASS" for x in steps),
                "stages": stages, "artifacts": self.artifacts(), "jobs": jobs, "logs": self.job(jobs[0]["id"], limit=8192)["log"] if jobs else "",
                "history": history, "guard": guard, "updated_at": utcnow(), "revision": int(revisions[0]["value"]) if revisions else 0}

    def refresh(self):
        self.initialize()
        with self._lock, FileLock(self.state_dir / "snapshot.lock", 60):
            snapshot = self.status()
            signature = hashlib.sha256(json.dumps(_stable(snapshot), ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            with self._db() as db:
                old = db.execute("SELECT value FROM meta WHERE key='snapshot_hash'").fetchone()
                if old is None or old[0] != signature:
                    snapshot["revision"] = self._bump(db)
                db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('snapshot_hash',?)", (signature,))
                db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('snapshot',?)", (json.dumps(snapshot, ensure_ascii=False),))
                db.execute("DELETE FROM artifacts")
                for a in snapshot["artifacts"]:
                    db.execute("INSERT INTO artifacts(id,path,kind,sha256,size,updated_at,mtime_ns,ctime_ns,inode) VALUES(?,?,?,?,?,?,?,?,?)",
                               (a["id"], a["path"], a["kind"], a["sha256"], a["size"], utcnow(), a["mtime_ns"], a["ctime_ns"], a["inode"]))
            atomic_json(self.state_dir / "status.json", snapshot)
            self._export_events()
            return snapshot

    _write_snapshot = refresh

    def _export_events(self):
        """Full compatibility export. The HTTP endpoint itself remains paginated."""
        rows = self._rows("SELECT MAX(id) AS last_id FROM events")
        last_id = int(rows[0]["last_id"] or 0) if rows else 0
        previous = self._rows("SELECT value FROM meta WHERE key='events_export_id'")
        if previous and int(previous[0]["value"]) == last_id and (self.state_dir / "events.jsonl").is_file():
            return
        descriptor, name = tempfile.mkstemp(prefix="events.", suffix=".tmp", dir=self.state_dir)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                with self._db(readonly=True) as db:
                    for row in db.execute("SELECT * FROM events WHERE id<=? ORDER BY id", (last_id,)):
                        item = dict(row); item["artifacts"] = json.loads(item["artifacts"] or "[]"); item["timestamp"] = item.pop("created_at")
                        handle.write(json.dumps(item, ensure_ascii=False) + "\n")
            os.replace(name, self.state_dir / "events.jsonl")
            with self._db() as db:
                db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('events_export_id',?)", (str(last_id),))
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def job(self, job_id, cursor=0, limit=MAX_LOG_PAGE):
        rows = self._rows("SELECT * FROM jobs WHERE id=?", (job_id,))
        if not rows:
            raise KeyError(job_id)
        row = rows[0]; row["job_id"] = row["id"]; row["options"] = json.loads(row.get("options") or "{}")
        row["execution_fingerprint"] = row.get("fingerprint")
        row["execution_inputs"] = json.loads(row.pop("fingerprint_details", None) or "{}")
        offset = max(0, int(cursor)); amount = max(1, min(int(limit), MAX_LOG_PAGE))
        log = self.state_dir / "logs" / f"{job_id}.log"
        if log.is_file():
            target = contained_file(self.state_dir, f"logs/{job_id}.log", limit=MAX_LOG_BYTES)
            with target.open("rb") as handle:
                handle.seek(offset); data = handle.read(amount)
            total = target.stat().st_size
        else:
            old = (row.get("log") or "").encode("utf-8"); data = old[offset:offset + amount]; total = len(old)
        row.update(log=data.decode("utf-8", errors="replace"), cursor=offset, next_cursor=offset + len(data),
                   has_more=offset + len(data) < total, log_bytes=total, log_truncated=bool(row.get("log_truncated")))
        for key in ("command", "pid", "process_identity", "child_pid", "child_identity", "owner", "request_key", "fingerprint"):
            row.pop(key, None)
        return row


# Imported last: jobs only needs WorkbenchState at execution time.
try:
    from runtime.jobs import JobRunner
except ModuleNotFoundError:
    from .runtime.jobs import JobRunner
