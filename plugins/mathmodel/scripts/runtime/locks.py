"""Cross-process advisory locks; each owner keeps the descriptor open."""
from __future__ import annotations
import os
import time
from pathlib import Path
from .safety import is_link


class FileLock:
    def __init__(self, path: Path, timeout: float = 10):
        self.path, self.timeout, self.handle = path, timeout, None

    def acquire(self):
        if is_link(self.path) or is_link(self.path.parent):
            raise PermissionError("linked runtime lock is not allowed")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+b")
        if self.handle.tell() == 0:
            self.handle.write(b"0")
            self.handle.flush()
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                self.handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError:
                if time.monotonic() >= deadline:
                    self.handle.close()
                    self.handle = None
                    raise TimeoutError(f"Project service lock is busy: {self.path.name}")
                time.sleep(0.05)

    def release(self):
        if self.handle is None:
            return
        try:
            self.handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        finally:
            self.handle.close()
            self.handle = None

    __enter__ = acquire

    def __exit__(self, *args):
        self.release()
