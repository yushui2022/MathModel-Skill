"""Durable worker: a service restart does not abandon a running experiment."""
from __future__ import annotations
import argparse
import json
import hashlib
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workbench import WorkbenchState, utcnow
from runtime.safety import MAX_LOG_BYTES, is_link, process_identity, spawn_options, terminate_tree, execution_environment
from runtime.processes import popen_tree
from runtime.locks import FileLock
from runtime.jobs import fingerprint_payload


def claim_queue(state, job):
    """Wait in SQLite insertion order; all writers share one OS execution lock."""
    jid = job["id"]
    with state._db() as db:
        db.execute("UPDATE jobs SET pid=?,process_identity=? WHERE id=?", (os.getpid(), process_identity(os.getpid()), jid))
    while True:
        rows = state._rows("SELECT status,cancel_requested FROM jobs WHERE id=?", (jid,))
        if not rows or rows[0]["status"] not in {"queued", "cancelling"}:
            return None
        if rows[0]["cancel_requested"]:
            with state._db() as db:
                db.execute("UPDATE jobs SET status='cancelled',finished_at=? WHERE id=?", (utcnow(), jid))
                state._event(db, job["stage"], "cancelled", "排队实验已取消", jid)
            return None
        head = state._rows("SELECT id FROM jobs WHERE status IN ('queued','running','cancelling') ORDER BY rowid LIMIT 1")
        if head and head[0]["id"] == jid:
            lock = FileLock(state.state_dir / "execution.lock", timeout=0)
            try:
                lock.acquire()
                return lock
            except TimeoutError:
                pass
        time.sleep(0.1)


def execute(root, job_id):
    state = WorkbenchState(root)
    state.initialize()
    rows = state._rows("SELECT * FROM jobs WHERE id=?", (job_id,))
    if not rows:
        return 1
    job = rows[0]
    execution_lock = claim_queue(state, job)
    if execution_lock is None:
        return 0
    try:
        current_details = fingerprint_payload(state.root, job["type"], json.loads(job["options"] or "{}"), json.loads(job["command"]))
        fingerprint = hashlib.sha256(json.dumps(current_details, sort_keys=True).encode()).hexdigest()
        if fingerprint != job["fingerprint"]:
            previous = json.loads(job.get("fingerprint_details") or "{}")
            changed = [key for key in current_details if previous.get(key) != current_details[key]]
            if "environment" in changed:
                changed += ["environment." + key for key in current_details["environment"] if previous.get("environment", {}).get(key) != current_details["environment"][key]]
            raise ValueError("排队期间有效输入发生变化（" + ", ".join(changed) + "）；请重新提交实验。")
    except Exception as exc:
        with state._db() as db:
            db.execute("UPDATE jobs SET status='failed',finished_at=?,error=? WHERE id=?", (utcnow(), str(exc), job_id))
            state._event(db, job["stage"], "failed", str(exc), job_id)
        execution_lock.release()
        return 1
    with state._db() as db:
        current = db.execute("SELECT cancel_requested,status FROM jobs WHERE id=?", (job_id,)).fetchone()
        if current["status"] not in {"queued", "cancelling"}:
            execution_lock.release()
            return 1
        if current["cancel_requested"]:
            db.execute("UPDATE jobs SET status='cancelled',finished_at=? WHERE id=?", (utcnow(), job_id))
            state._event(db, job["stage"], "cancelled", "实验启动前已取消", job_id)
            execution_lock.release()
            return 0
        db.execute("UPDATE jobs SET status='running',started_at=?,pid=?,process_identity=? WHERE id=?",
                   (utcnow(), os.getpid(), process_identity(os.getpid()), job_id))
        state._event(db, job["stage"], "running", f"开始执行 {job['type']}", job_id)
    log_dir = state.state_dir / "logs"
    log_path = log_dir / f"{job_id}.log"
    proc = None
    tree = None
    try:
        if is_link(log_dir) or is_link(log_path):
            raise PermissionError("linked logs directory or job log")
        log_dir.mkdir(exist_ok=True)
        with log_path.open("xb", buffering=0) as output:
            proc, tree = popen_tree(json.loads(job["command"]), cwd=state.root, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    env=execution_environment(),
                                    **spawn_options())
            identity = process_identity(proc.pid)
            with state._db() as db:
                db.execute("UPDATE jobs SET child_pid=?,child_identity=? WHERE id=?", (proc.pid, identity, job_id))
            size = 0
            truncated = False
            pump_error = []

            def pump():
                nonlocal size, truncated
                try:
                    while True:
                        chunk = proc.stdout.read1(8192)
                        if not chunk:
                            break
                        allowed = max(0, MAX_LOG_BYTES - size)
                        kept = chunk[:allowed]
                        if kept:
                            output.write(kept); size += len(kept)
                        was_truncated = truncated
                        truncated = truncated or len(kept) < len(chunk)
                        if kept or was_truncated != truncated:
                            with state._db() as db:
                                db.execute("UPDATE jobs SET log_size=?,log_truncated=? WHERE id=?", (size, int(truncated), job_id))
                                state._bump(db)
                except Exception as exc:
                    pump_error.append(str(exc))

            thread = threading.Thread(target=pump, daemon=True)
            thread.start()
            cancelled = False
            while proc.poll() is None:
                rows = state._rows("SELECT cancel_requested FROM jobs WHERE id=?", (job_id,))
                if rows and rows[0]["cancel_requested"]:
                    cancelled = True
                    tree.kill()
                    break
                if pump_error:
                    tree.kill()
                    break
                time.sleep(0.1)
            proc.wait(timeout=20)
            # Parent completion must not leave a child holding the output pipe open.
            tree.close()
            thread.join(timeout=5)
            if thread.is_alive():
                # A descendant inherited stdout. Stop the tree before finalizing.
                tree.kill()
                proc.stdout.close()
                thread.join(timeout=2)
            rows = state._rows("SELECT cancel_requested FROM jobs WHERE id=?", (job_id,))
            cancelled = cancelled or bool(rows and rows[0]["cancel_requested"])
            status = "cancelled" if cancelled else ("succeeded" if proc.returncode == 0 and not pump_error else "failed")
            error = "; ".join(pump_error) or None
            with state._db() as db:
                db.execute("UPDATE jobs SET status=?,finished_at=?,exit_code=?,error=?,log_size=?,log_truncated=? WHERE id=?",
                           (status, utcnow(), proc.returncode, error, size, int(truncated), job_id))
                state._event(db, job["stage"], "awaiting_validation" if status == "succeeded" else status,
                             f"{job['type']} {status}; exit={proc.returncode}", job_id)
        return 0
    except Exception as exc:
        if proc is not None:
            terminate_tree(proc.pid, process_identity(proc.pid))
        with state._db() as db:
            db.execute("UPDATE jobs SET status=CASE WHEN cancel_requested=1 THEN 'cancelled' ELSE 'failed' END,finished_at=?,error=? WHERE id=?",
                       (utcnow(), str(exc), job_id))
            row = db.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()
            state._event(db, job["stage"], row["status"], str(exc), job_id)
        return 1
    finally:
        execution_lock.release()
        if tree is not None:
            tree.close()
        if proc is not None and proc.stdout is not None:
            proc.stdout.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--job-id", required=True)
    args = parser.parse_args()
    raise SystemExit(execute(args.project_root, args.job_id))
