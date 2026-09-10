from __future__ import annotations

import argparse
import ctypes
import importlib.metadata
import os
import platform
import signal
import subprocess
import sys
import time
from pathlib import Path

from pro_checkpoint import require_checkpoints
from pro_contracts import contract, hash_paths, output_root, read_json, safe_path, sha256_file, utc_now, write_json


LOG_LIMIT_BYTES = 2 * 1024 * 1024  # Per stream; discarded bytes are still drained and counted.
LOG_DRAIN_GRACE_SECONDS = 2.0
LOG_CHUNK_BYTES = 64 * 1024


class _ProcessTree:
    """Keep the standalone Pro runner independent of the optional plugin runtime."""

    def __init__(self, proc):
        self.proc, self.handle, self.closed = proc, None, False
        if os.name != "nt":
            return
        from ctypes import wintypes as w

        class Basic(ctypes.Structure):
            _fields_ = [("per_process", ctypes.c_int64), ("per_job", ctypes.c_int64), ("flags", w.DWORD),
                        ("min_ws", ctypes.c_size_t), ("max_ws", ctypes.c_size_t), ("active", w.DWORD),
                        ("affinity", ctypes.c_size_t), ("priority", w.DWORD), ("scheduling", w.DWORD)]

        class Counters(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint64) for name in ("read_ops", "write_ops", "other_ops", "read_bytes", "write_bytes", "other_bytes")]

        class Extended(ctypes.Structure):
            _fields_ = [("basic", Basic), ("io", Counters), ("process_memory", ctypes.c_size_t),
                        ("job_memory", ctypes.c_size_t), ("peak_process", ctypes.c_size_t), ("peak_job", ctypes.c_size_t)]

        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
        self.kernel.CreateJobObjectW.restype = w.HANDLE
        self.kernel.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
        self.kernel.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        self.kernel.CloseHandle.argtypes = [w.HANDLE]
        self.kernel.TerminateJobObject.argtypes = [w.HANDLE, w.UINT]
        self.handle = self.kernel.CreateJobObjectW(None, None)
        settings = Extended()
        settings.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE; no breakaway.
        if not self.handle or not self.kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(settings), ctypes.sizeof(settings)):
            self.close()
            raise OSError("cannot establish Windows experiment process job")
        if not self.kernel.AssignProcessToJobObject(self.handle, int(proc._handle)):
            self.close()
            raise OSError("cannot assign experiment to Windows process job")

    def kill(self):
        if self.closed:
            return
        if os.name == "nt":
            if self.handle:
                self.kernel.TerminateJobObject(self.handle, 1)
        else:
            try:
                os.killpg(self.proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    def close(self):
        if self.closed:
            return
        if os.name == "nt":
            if self.handle:
                self.kernel.CloseHandle(self.handle)
                self.handle = None
        else:
            self.kill()
        self.closed = True


def _resume_process(proc):
    """Assign a suspended Windows process to its job before it can spawn children."""
    from ctypes import wintypes as w

    class ThreadEntry(ctypes.Structure):
        _fields_ = [("size", w.DWORD), ("usage", w.DWORD), ("thread_id", w.DWORD), ("owner_pid", w.DWORD),
                    ("base_priority", w.LONG), ("delta_priority", w.LONG), ("flags", w.DWORD)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [w.DWORD, w.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = w.HANDLE
    kernel.Thread32First.argtypes = [w.HANDLE, ctypes.POINTER(ThreadEntry)]
    kernel.Thread32Next.argtypes = [w.HANDLE, ctypes.POINTER(ThreadEntry)]
    kernel.OpenThread.argtypes = [w.DWORD, w.BOOL, w.DWORD]
    kernel.OpenThread.restype = w.HANDLE
    kernel.ResumeThread.argtypes = [w.HANDLE]
    kernel.ResumeThread.restype = w.DWORD
    kernel.CloseHandle.argtypes = [w.HANDLE]
    snapshot = kernel.CreateToolhelp32Snapshot(4, 0)
    if snapshot == ctypes.c_void_p(-1).value:
        raise OSError("cannot inspect suspended experiment thread")
    resumed = False
    try:
        entry = ThreadEntry()
        entry.size = ctypes.sizeof(entry)
        available = kernel.Thread32First(snapshot, ctypes.byref(entry))
        while available:
            if entry.owner_pid == proc.pid:
                thread = kernel.OpenThread(2, False, entry.thread_id)
                if thread:
                    try:
                        resumed |= kernel.ResumeThread(thread) != 0xFFFFFFFF
                    finally:
                        kernel.CloseHandle(thread)
            available = kernel.Thread32Next(snapshot, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)
    if not resumed:
        raise OSError("cannot resume suspended experiment")


def _popen_tree(argv, **kwargs):
    if os.name == "nt":
        kwargs["creationflags"] = 4 | subprocess.CREATE_NO_WINDOW  # CREATE_SUSPENDED
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(argv, **kwargs)
    tree = None
    try:
        tree = _ProcessTree(proc)
        if os.name == "nt":
            _resume_process(proc)
        return proc, tree
    except Exception:
        if tree:
            tree.close()
        proc.kill()
        proc.wait(timeout=5)
        for pipe in (proc.stdout, proc.stderr):
            if pipe:
                pipe.close()
        raise


def _available_chunk(pipe):
    """Return bytes, None for temporarily empty, or b'' for EOF, without blocking."""
    if os.name == "nt":
        import msvcrt
        from ctypes import wintypes as w
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.PeekNamedPipe.argtypes = [w.HANDLE, ctypes.c_void_p, w.DWORD, ctypes.c_void_p, ctypes.POINTER(w.DWORD), ctypes.c_void_p]
        available = w.DWORD()
        if not kernel.PeekNamedPipe(msvcrt.get_osfhandle(pipe.fileno()), None, 0, None, ctypes.byref(available), None):
            error = ctypes.get_last_error()
            if error in (109, 232):  # ERROR_BROKEN_PIPE / ERROR_NO_DATA
                return b""
            raise ctypes.WinError(error)
        if not available.value:
            return None
        return os.read(pipe.fileno(), min(LOG_CHUNK_BYTES, available.value))
    try:
        return os.read(pipe.fileno(), LOG_CHUNK_BYTES)
    except BlockingIOError:
        return None


def _capture_process(argv, root, child_env, directory, timeout):
    """Drain both streams fairly with bounded files, memory and post-exit cleanup."""
    logs = {name: {"path": f"experiments/{directory.name}/{name}.log", "limit_bytes": LOG_LIMIT_BYTES,
                   "observed_bytes": 0, "retained_bytes": 0, "truncated": False, "complete": False}
            for name in ("stdout", "stderr")}
    failures, proc, tree, pipes = [], None, None, {}
    exit_code = -1
    with (directory / "stdout.log").open("wb") as stdout, (directory / "stderr.log").open("wb") as stderr:
        files = {"stdout": stdout, "stderr": stderr}
        try:
            proc, tree = _popen_tree(argv, cwd=root, env=child_env, stdin=subprocess.DEVNULL,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
            pipes = {"stdout": proc.stdout, "stderr": proc.stderr}
            if os.name != "nt":
                for pipe in pipes.values():
                    os.set_blocking(pipe.fileno(), False)
            deadline = time.monotonic() + timeout
            exited_at = killed_at = None
            while True:
                now = time.monotonic()
                returncode = proc.poll()
                if returncode is not None and exited_at is None:
                    exited_at = now
                if returncode is None and now >= deadline and killed_at is None:
                    failures.append(f"process watchdog exceeded {timeout} seconds")
                    tree.kill()
                    killed_at = now
                if pipes and exited_at is not None and now - exited_at >= LOG_DRAIN_GRACE_SECONDS and killed_at is None:
                    failures.append("log pipes remained open after process exit; terminated remaining experiment descendants")
                    tree.kill()
                    killed_at = now
                if killed_at is not None and now - killed_at >= LOG_DRAIN_GRACE_SECONDS:
                    if pipes:
                        failures.append("log drain deadline exceeded; observed byte counts are incomplete")
                    if returncode is None:
                        failures.append("experiment did not exit after process-tree termination")
                    break
                progressed = False
                for name, pipe in list(pipes.items()):
                    chunk = _available_chunk(pipe)
                    if chunk is None:
                        continue
                    if not chunk:
                        logs[name]["complete"] = True
                        pipe.close()
                        del pipes[name]
                        continue
                    progressed = True
                    info = logs[name]
                    info["observed_bytes"] += len(chunk)
                    retained = chunk[:max(0, LOG_LIMIT_BYTES - info["retained_bytes"])]
                    files[name].write(retained)
                    info["retained_bytes"] += len(retained)
                    info["truncated"] = info["observed_bytes"] > LOG_LIMIT_BYTES
                if not pipes and returncode is not None:
                    break
                if not progressed:
                    time.sleep(0.01)
        except OSError as exc:
            failures.append(f"process or log capture failed: {exc}")
        finally:
            if tree:
                tree.close()
            if proc:
                try:
                    exit_code = proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    failures.append("process could not be reaped within cleanup deadline")
                for pipe in pipes.values():
                    pipe.close()
    if exit_code:
        failures.append(f"process exited with code {exit_code}")
    truncated = [name for name, info in logs.items() if info["truncated"]]
    if truncated:
        failures.append(f"log limit exceeded ({', '.join(truncated)}; {LOG_LIMIT_BYTES} bytes per stream); reduce verbosity and rerun with a new run_id")
    return exit_code, "; ".join(failures), logs


def refresh_manifest(root: Path) -> None:
    runs = []
    for path in sorted((root / "experiments").glob("*/receipt.json")):
        receipt = read_json(path)
        runs.append({"run_id": receipt["run_id"], "receipt_path": path.relative_to(root).as_posix(), "receipt_sha256": sha256_file(path)})
    write_json(root / "experiment_manifest.json", contract(
        producer_role="pro-experiment-runner", status="PASS", runs=runs,
        input_hashes={r["receipt_path"]: r["receipt_sha256"] for r in runs},
    ))


def execute(project: Path, spec_path: Path) -> tuple[Path, bool]:
    root = output_root(project)
    errors = require_checkpoints(project, root, 2)
    if errors:
        raise ValueError("; ".join(errors))
    spec_path = spec_path.resolve()
    if not spec_path.is_relative_to((root / "code").resolve()):
        raise ValueError("run specification must be under code/")
    spec_hash = sha256_file(spec_path)
    spec = read_json(spec_path)
    run_id = spec.get("run_id", "")
    if not isinstance(run_id, str) or not run_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in run_id):
        raise ValueError("run_id must be a simple unique identifier")
    directory = safe_path(root, "experiments/" + run_id)
    if directory.exists():
        raise ValueError("run_id already exists; retain previous runs and use a new ID")
    script = safe_path(root, spec.get("script", ""))
    if not script.is_relative_to((root / "code").resolve()) or script.suffix != ".py":
        raise ValueError("experiment entrypoint must be a Python file under code/")
    if not spec.get("route_id") or not spec.get("implementation_id"):
        raise ValueError("route_id and implementation_id are required")
    routes = {r["route_id"] for p in read_json(root / "candidate_routes.json")["subproblems"] for r in p["routes"]}
    if spec["route_id"] not in routes:
        raise ValueError("run route is not in the approved tournament")
    seed = spec.get("seed")
    if spec.get("stochastic") is True and type(seed) is not int:
        raise ValueError("stochastic runs require a recorded integer seed")
    inputs = [safe_path(root, p) for p in spec.get("inputs", [])]
    scripts = [script, *[safe_path(root, p) for p in spec.get("dependencies", [])]]
    if not inputs or any(not p.is_file() for p in [*inputs, *scripts]):
        raise ValueError("all declared scripts and non-empty inputs must exist")
    argv_tail = spec.get("args", [])
    if not isinstance(argv_tail, list) or any(not isinstance(a, str) for a in argv_tail):
        raise ValueError("args must be strings; shell command strings are not accepted")
    timeout = spec.get("timeout_seconds", 1800)
    if type(timeout) is not int or timeout <= 0:
        raise ValueError("timeout_seconds must be a positive per-process watchdog")
    directory.mkdir(parents=True)
    metrics_path = directory / "metrics.json"
    argv = [sys.executable, str(script), *[a.replace("{run_dir}", str(directory)).replace("{seed}", str(seed)) for a in argv_tail]]
    before_scripts, before_inputs = hash_paths(scripts, root), hash_paths(inputs, root)
    started = utc_now()
    environment = {
        "python": sys.version, "executable": sys.executable, "platform": platform.platform(),
        "packages": sorted({f"{d.metadata['Name']}=={d.version}" for d in importlib.metadata.distributions() if d.metadata['Name']}),
    }
    child_env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}
    exit_code, failure, logs = _capture_process(argv, root, child_env, directory, timeout)
    try:
        if hash_paths(scripts, root) != before_scripts or hash_paths(inputs, root) != before_inputs or sha256_file(spec_path) != spec_hash:
            failure = "scripts, inputs or run specification changed during execution"
    except OSError:
        failure = "scripts, inputs or run specification removed during execution"
    if not failure:
        try:
            from pro_validation import finite
            metrics = read_json(metrics_path).get("metrics", {})
            if not metrics or any(not (finite(v) or isinstance(v, list) and v and all(finite(x) for x in v)) for v in metrics.values()):
                failure = "missing, empty or nonnumeric metrics"
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            failure = str(exc)
    paths = [p for p in directory.rglob("*") if p.is_file()]
    outputs = hash_paths(paths, root)
    receipt = contract(
        producer_role="pro-experiment-runner", status="FAILED" if failure else "PASS",
        input_hashes=before_inputs, script_hashes=before_scripts, output_hashes=outputs,
        run_id=run_id, route_id=spec["route_id"], implementation_id=spec["implementation_id"],
        argv=argv, cwd="paper_output_pro", environment=environment, seed=seed,
        stochastic=spec.get("stochastic") is True, exit_code=exit_code,
        started_at_utc=started, finished_at_utc=utc_now(), failure_reason=failure or None,
        log_capture=logs,
        metrics_file=metrics_path.relative_to(root).as_posix(),
        spec_path=spec_path.relative_to(root).as_posix(), spec_sha256=spec_hash,
    )
    receipt_path = directory / "receipt.json"
    write_json(receipt_path, receipt)
    return receipt_path, not failure


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute a Pro experiment and record actual outputs.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--spec", help="Run specification relative to paper_output_pro/")
    parser.add_argument("--refresh-manifest", action="store_true", help="Run after a parallel batch has fully completed")
    args = parser.parse_args()
    project = args.project_root.resolve()
    root = output_root(project)
    try:
        if args.refresh_manifest:
            refresh_manifest(root)
            print("[PASS] Collected all execution receipts")
            return 0
        if not args.spec:
            parser.error("--spec is required")
        path, passed = execute(project, safe_path(root, args.spec))
        print(f"[{'PASS' if passed else 'FAILED'}] {path}")
        return 0 if passed else 1
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(f"[BLOCKED] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
