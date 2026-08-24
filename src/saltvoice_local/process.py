from __future__ import annotations

import ctypes
import logging
import os
import subprocess
import time
from ctypes import wintypes

log = logging.getLogger("saltvoice_local")

ERROR_ALREADY_EXISTS = 183


def configure_stdio() -> None:
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def safe_print(*args: object, **kwargs: object) -> None:
    text = " ".join(str(a) for a in args)
    try:
        print(text, **kwargs)  # type: ignore[arg-type]
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        sys.stdout.buffer.write((text + "\n").encode(encoding, errors="replace"))
        sys.stdout.buffer.flush()


_mutex_handle = None


def _kill_leftover(*, cmdline_needle: str, window_title: str) -> list[int]:
    """Stop an old Saltvoice that is still holding the mic / STT."""
    if os.name != "nt":
        return []
    killed: list[int] = []
    me = os.getpid()
    try:
        subprocess.run(
            ["taskkill", "/F", "/FI", f"WINDOWTITLE eq {window_title}*"],
            capture_output=True,
            timeout=8,
            check=False,
        )
    except Exception:
        pass
    script = (
        "$me = %d;"
        "Get-CimInstance Win32_Process |"
        " Where-Object {"
        "  $_.ProcessId -ne $me -and $_.CommandLine -and"
        "  ($_.CommandLine -match '%s')"
        " } |"
        " ForEach-Object { $_.ProcessId }"
    ) % (me, cmdline_needle.replace("'", ""))
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", script],
            text=True,
            timeout=12,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        out = ""
    for token in out.split():
        try:
            pid = int(token.strip())
        except ValueError:
            continue
        if pid == me:
            continue
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                capture_output=True,
                timeout=8,
                check=False,
            )
            killed.append(pid)
        except Exception:
            pass
    return killed


def acquire_single_instance(
    name: str = "Local\\SaltvoiceLocalSingleton",
    *,
    cmdline_needle: str = "saltvoice_local",
    window_title: str = "Saltvoice Local",
) -> bool:
    """Return True if this process owns the instance.

    If an old Saltvoice is still running (common after git pull), close it
    so standby/sleep is not the leftover Whisper listener.
    """
    global _mutex_handle
    if os.name != "nt":
        return True
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.GetLastError.restype = wintypes.DWORD
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]

    def _try() -> bool:
        global _mutex_handle
        _mutex_handle = kernel32.CreateMutexW(None, False, name)
        return kernel32.GetLastError() != ERROR_ALREADY_EXISTS

    if _try():
        return True
    log.warning("another Saltvoice Local is running — closing it so STT can stop")
    if _mutex_handle:
        try:
            kernel32.CloseHandle(_mutex_handle)
        except Exception:
            pass
        _mutex_handle = None
    killed = _kill_leftover(cmdline_needle=cmdline_needle, window_title=window_title)
    if killed:
        log.warning("closed leftover pid(s): %s", killed)
    time.sleep(1.0)
    if _try():
        return True
    log.error("another Saltvoice Local process is already running")
    return False
