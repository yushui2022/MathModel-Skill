"""Filesystem and process boundaries shared by the local runtime."""
from __future__ import annotations

import ctypes
import hashlib
import json
import mimetypes
import os
import signal
import stat
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

MAX_ARTIFACT_BYTES = 25 * 1024 * 1024
MAX_LOG_BYTES = 2 * 1024 * 1024
MAX_LOG_PAGE = 64 * 1024


def artifact_mime(path):
    """Stable scientific/text MIME types, independent of Windows registry entries."""
    suffix = Path(path).suffix.lower()
    types = {".md": "text/markdown", ".markdown": "text/markdown", ".txt": "text/plain", ".log": "text/plain",
             ".py": "text/x-python", ".r": "text/plain", ".jl": "text/plain", ".m": "text/plain", ".tex": "text/plain",
             ".csv": "text/csv", ".tsv": "text/tab-separated-values", ".json": "application/json", ".ipynb": "application/json",
             ".yaml": "text/plain", ".yml": "text/plain", ".toml": "text/plain", ".sql": "text/plain",
             ".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
             ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
             ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
    mime = types.get(suffix) or mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    return mime + "; charset=utf-8" if mime.startswith("text/") or mime == "application/json" else mime


def is_link(path: Path) -> bool:
    try:
        info = path.lstat()
        return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)
    except FileNotFoundError:
        return False


def contained_file(base: Path, relative: str | Path, *, limit: int = MAX_ARTIFACT_BYTES) -> Path:
    """Reject traversal and links in every path component before any file read."""
    value = str(relative)
    if "\\" in value or ":" in value or "\x00" in value:
        raise PermissionError("invalid path")
    rel = Path(value)
    if rel.is_absolute() or not rel.parts or any(part in {".", ".."} for part in rel.parts):
        raise PermissionError("invalid relative path")
    base = base.absolute()
    if is_link(base):
        raise PermissionError("linked root is not allowed")
    target = base
    for part in rel.parts:
        target = target / part
        if is_link(target):
            raise PermissionError("linked path is not allowed")
    resolved = target.resolve()
    if not resolved.is_relative_to(base.resolve()):
        raise PermissionError("path outside registered root")
    if not resolved.is_file():
        raise FileNotFoundError(value)
    if resolved.stat().st_size > limit:
        raise PermissionError("file exceeds size limit")
    return resolved


def safe_files(base: Path):
    if not base.is_dir() or is_link(base):
        return
    for directory, dirs, files in os.walk(base, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not is_link(Path(directory) / d))
        for name in sorted(files):
            candidate = Path(directory) / name
            try:
                yield contained_file(base, candidate.relative_to(base).as_posix())
            except (OSError, ValueError):
                continue


def file_hash(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def atomic_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def process_identity(pid: int) -> str | None:
    """Return OS creation identity, so stale PIDs are never treated as owners."""
    if pid <= 0:
        return None
    if os.name == "nt":
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
        kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return None
        try:
            code = wintypes.DWORD()
            if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value != 259:
                return None
            times = [wintypes.FILETIME() for _ in range(4)]
            if not kernel.GetProcessTimes(handle, *(ctypes.byref(t) for t in times)):
                return None
            return str((times[0].dwHighDateTime << 32) | times[0].dwLowDateTime)
        finally:
            kernel.CloseHandle(handle)
    try:
        # Linux /proc field 22 is a creation tick count, field 3 distinguishes zombies.
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return None if fields[0] == "Z" else fields[19]
    except (OSError, IndexError):
        if sys.platform == "darwin":
            result = subprocess.run(["ps", "-p", str(pid), "-o", "lstart="], capture_output=True, text=True)
            return result.stdout.strip() or None
        return None


def spawn_options(*, detached: bool = False) -> dict:
    if os.name == "nt":
        flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
        if detached:
            flags |= subprocess.DETACHED_PROCESS
        return {"creationflags": flags}
    return {"start_new_session": True}


def reap_process(process):
    """Retain/reap a detached child without binding its lifetime to the client."""
    threading.Thread(target=process.wait, daemon=True).start()


def execution_environment():
    return {**os.environ, "PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}


def terminate_tree(pid: int, identity: str | None) -> bool:
    if not identity or process_identity(pid) != identity:
        return False
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW, timeout=15)
    else:
        try:
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    return True
