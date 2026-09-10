"""Own a complete child process group, including descendants after parent exit."""
from __future__ import annotations
import ctypes
import os
import signal
import subprocess


class ProcessTree:
    def __init__(self, proc):
        self.proc, self.handle = proc, None
        self.closed = False
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
        settings = Extended(); settings.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.handle or not self.kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(settings), ctypes.sizeof(settings)):
            self.close()
            raise OSError("cannot establish Windows process job")
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
    """Resume the primary thread after assigning the suspended process to a job."""
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
        entry = ThreadEntry(); entry.size = ctypes.sizeof(entry)
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


def popen_tree(command, **kwargs):
    if os.name == "nt":
        kwargs["creationflags"] = kwargs.get("creationflags", 0) | 4  # CREATE_SUSPENDED
    proc = subprocess.Popen(command, **kwargs)
    tree = None
    try:
        tree = ProcessTree(proc)
        if os.name == "nt":
            _resume_process(proc)
        return proc, tree
    except Exception:
        if tree:
            tree.close()
        proc.kill(); proc.wait(timeout=10)
        raise
