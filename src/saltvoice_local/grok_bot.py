from __future__ import annotations

import base64
import ctypes
import logging
import os
import shutil
import subprocess
import threading
import time
from ctypes import wintypes
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger("saltvoice_local")

USER32 = ctypes.WinDLL("user32", use_last_error=True) if os.name == "nt" else None
KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True) if os.name == "nt" else None
_CALLBACKS: list[object] = []
_topmost_hook: Callable[[bool], None] | None = None
_winapi_ready = False

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_ABSOLUTE = 0x8000
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
VK_CONTROL = 0x11
VK_RETURN = 0x0D
VK_V = 0x56
SW_RESTORE = 9
SW_SHOW = 5
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040
ASFW_ANY = -1
CREATE_NO_WINDOW = 0x08000000
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SM_CXSCREEN = 0
SM_CYSCREEN = 1
ULONG_PTR = ctypes.c_size_t


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", INPUTUNION)]


class GrokBotConfig:
    def __init__(
        self,
        window_titles: list[str] | None = None,
        prefer: str = "window",
        cli: str = "grok",
        target: str = "grok",
    ) -> None:
        self.window_titles = [t.lower() for t in (window_titles or ["Grok Bot", "Grok", "Grok Build"])]
        self.prefer = (prefer or "window").lower()
        self.cli = cli or "grok"
        self.target = (target or "grok").lower()


def _configure_winapi() -> None:
    """64-bit Windows truncates handles unless restype is a pointer."""
    global _winapi_ready
    if _winapi_ready or USER32 is None or KERNEL32 is None:
        return
    KERNEL32.GlobalAlloc.restype = ctypes.c_void_p
    KERNEL32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    KERNEL32.GlobalLock.restype = ctypes.c_void_p
    KERNEL32.GlobalLock.argtypes = [ctypes.c_void_p]
    KERNEL32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    KERNEL32.GlobalFree.argtypes = [ctypes.c_void_p]
    KERNEL32.GetLastError.restype = wintypes.DWORD
    KERNEL32.GetCurrentThreadId.restype = wintypes.DWORD
    USER32.OpenClipboard.argtypes = [wintypes.HWND]
    USER32.OpenClipboard.restype = wintypes.BOOL
    USER32.EmptyClipboard.restype = wintypes.BOOL
    USER32.CloseClipboard.restype = wintypes.BOOL
    USER32.SetClipboardData.argtypes = [wintypes.UINT, ctypes.c_void_p]
    USER32.SetClipboardData.restype = ctypes.c_void_p
    USER32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
    USER32.SendInput.restype = wintypes.UINT
    USER32.GetSystemMetrics.argtypes = [ctypes.c_int]
    USER32.GetSystemMetrics.restype = ctypes.c_int
    USER32.SetForegroundWindow.argtypes = [wintypes.HWND]
    USER32.SetForegroundWindow.restype = wintypes.BOOL
    _winapi_ready = True


def set_topmost_hook(fn: Callable[[bool], None] | None) -> None:
    global _topmost_hook
    _topmost_hook = fn


def _call_topmost(value: bool) -> None:
    if _topmost_hook is None:
        return
    try:
        _topmost_hook(value)
    except Exception as exc:
        log.warning("topmost hook failed: %s", exc)


def list_windows() -> list[tuple[int, str]]:
    if USER32 is None:
        return []
    _configure_winapi()
    found: list[tuple[int, str]] = []
    EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @EnumWindowsProc
    def callback(hwnd, _lparam):  # noqa: ANN001
        if not USER32.IsWindowVisible(hwnd):
            return True
        length = USER32.GetWindowTextLengthW(hwnd)
        if length < 1:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        USER32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value.strip()
        if title:
            found.append((int(hwnd), title))
        return True

    _CALLBACKS.append(callback)
    USER32.EnumWindows(callback, 0)
    return found


def find_grok_window(titles: list[str]) -> tuple[int, str] | None:
    skip = ("saltvoice", "grok handsfree")
    needles = [t.lower() for t in titles]
    ranked: list[tuple[int, int, str]] = []
    for hwnd, title in list_windows():
        lowered = title.lower()
        if any(s in lowered for s in skip):
            continue
        score = 0
        if "grok bot" in lowered:
            score = 3
        elif any(n in lowered for n in needles):
            score = 2
        elif lowered == "grok" or lowered.startswith("grok "):
            score = 1
        if score:
            ranked.append((score, hwnd, title))
    if not ranked:
        return None
    ranked.sort(reverse=True)
    _score, hwnd, title = ranked[0]
    return hwnd, title


def _last_error() -> int:
    if KERNEL32 is None:
        return 0
    return int(KERNEL32.GetLastError())


def _set_clipboard_win32(text: str) -> None:
    if USER32 is None or KERNEL32 is None:
        raise RuntimeError("Clipboard is only available on Windows")
    _configure_winapi()
    encoded = text.encode("utf-16-le") + b"\x00\x00"
    opened = False
    for attempt in range(10):
        if USER32.OpenClipboard(None):
            opened = True
            break
        time.sleep(0.04 * (attempt + 1))
    if not opened:
        raise RuntimeError(f"OpenClipboard failed error={_last_error()}")
    handle = None
    try:
        USER32.EmptyClipboard()
        handle = KERNEL32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
        if not handle:
            raise RuntimeError(f"GlobalAlloc failed error={_last_error()}")
        locked = KERNEL32.GlobalLock(handle)
        if not locked:
            err = _last_error()
            KERNEL32.GlobalFree(handle)
            handle = None
            raise RuntimeError(f"GlobalLock failed error={err}")
        ctypes.memmove(locked, encoded, len(encoded))
        KERNEL32.GlobalUnlock(handle)
        if not USER32.SetClipboardData(CF_UNICODETEXT, handle):
            raise RuntimeError(f"SetClipboardData failed error={_last_error()}")
        handle = None
    finally:
        USER32.CloseClipboard()
        if handle:
            KERNEL32.GlobalFree(handle)


def _set_clipboard_powershell(text: str) -> None:
    payload = base64.b64encode(text.encode("utf-16-le")).decode("ascii")
    script = (
        "$t = [Text.Encoding]::Unicode.GetString([Convert]::FromBase64String('"
        + payload
        + "')); Set-Clipboard -Value $t"
    )
    flags = CREATE_NO_WINDOW if os.name == "nt" else 0
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-STA", "-NonInteractive", "-Command", script],
        capture_output=True,
        timeout=12,
        creationflags=flags,
    )
    if proc.returncode != 0:
        err = (proc.stderr or b"").decode("utf-8", errors="replace")[:240]
        raise RuntimeError(f"Set-Clipboard failed: {err or proc.returncode}")


def _set_clipboard_text(text: str) -> str:
    errors: list[str] = []
    try:
        _set_clipboard_win32(text)
        return "win32"
    except Exception as exc:
        errors.append(f"win32:{exc}")
        log.warning("win32 clipboard failed: %s", exc)
    try:
        _set_clipboard_powershell(text)
        return "powershell"
    except Exception as exc:
        errors.append(f"powershell:{exc}")
        log.warning("powershell clipboard failed: %s", exc)
    raise RuntimeError("clipboard failed: " + " | ".join(errors))


def _send_input(events: list[INPUT]) -> None:
    if USER32 is None or not events:
        return
    _configure_winapi()
    array = (INPUT * len(events))(*events)
    sent = USER32.SendInput(len(events), array, ctypes.sizeof(INPUT))
    if sent != len(events):
        raise RuntimeError(f"SendInput sent {sent}/{len(events)} error={_last_error()}")


def _key_event(vk: int, up: bool = False) -> INPUT:
    flags = KEYEVENTF_KEYUP if up else 0
    return INPUT(type=INPUT_KEYBOARD, union=INPUTUNION(ki=KEYBDINPUT(vk, 0, flags, 0, 0)))


def _unicode_event(char: str, up: bool = False) -> INPUT:
    flags = KEYEVENTF_UNICODE | (KEYEVENTF_KEYUP if up else 0)
    return INPUT(
        type=INPUT_KEYBOARD,
        union=INPUTUNION(ki=KEYBDINPUT(0, ord(char), flags, 0, 0)),
    )


def _paste_and_enter() -> None:
    _send_input(
        [
            _key_event(VK_CONTROL),
            _key_event(VK_V),
            _key_event(VK_V, up=True),
            _key_event(VK_CONTROL, up=True),
        ]
    )
    time.sleep(0.12)
    _send_input([_key_event(VK_RETURN), _key_event(VK_RETURN, up=True)])


def _type_text(text: str) -> None:
    events: list[INPUT] = []
    for char in text:
        if char in "\r\n":
            if events:
                _send_input(events)
                events = []
            _send_input([_key_event(VK_RETURN), _key_event(VK_RETURN, up=True)])
            time.sleep(0.02)
            continue
        events.append(_unicode_event(char))
        events.append(_unicode_event(char, up=True))
        if len(events) >= 80:
            _send_input(events)
            events = []
    if events:
        _send_input(events)
    time.sleep(0.08)
    _send_input([_key_event(VK_RETURN), _key_event(VK_RETURN, up=True)])


def _click_at(x: int, y: int) -> None:
    if USER32 is None:
        return
    _configure_winapi()
    width = max(1, USER32.GetSystemMetrics(SM_CXSCREEN))
    height = max(1, USER32.GetSystemMetrics(SM_CYSCREEN))
    nx = int(x * 65535 / width)
    ny = int(y * 65535 / height)
    flags_move = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE
    _send_input(
        [
            INPUT(type=INPUT_MOUSE, union=INPUTUNION(mi=MOUSEINPUT(nx, ny, 0, flags_move, 0, 0))),
            INPUT(type=INPUT_MOUSE, union=INPUTUNION(mi=MOUSEINPUT(nx, ny, 0, MOUSEEVENTF_LEFTDOWN, 0, 0))),
            INPUT(type=INPUT_MOUSE, union=INPUTUNION(mi=MOUSEINPUT(nx, ny, 0, MOUSEEVENTF_LEFTUP, 0, 0))),
        ]
    )


def _click_input(hwnd: int) -> None:
    if USER32 is None:
        return
    rect = wintypes.RECT()
    if not USER32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return
    x = (rect.left + rect.right) // 2
    y = rect.bottom - 56
    if y <= rect.top:
        y = (rect.top + rect.bottom) // 2
    _click_at(x, y)


def _focus(hwnd: int) -> int | None:
    if USER32 is None or KERNEL32 is None:
        return None
    _configure_winapi()
    previous = USER32.GetForegroundWindow()
    try:
        USER32.AllowSetForegroundWindow(ASFW_ANY)
    except Exception:
        pass
    USER32.ShowWindow(hwnd, SW_RESTORE)
    USER32.ShowWindow(hwnd, SW_SHOW)
    USER32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    fg = USER32.GetForegroundWindow()
    our = KERNEL32.GetCurrentThreadId()
    pid = wintypes.DWORD()
    fg_tid = USER32.GetWindowThreadProcessId(fg, ctypes.byref(pid))
    if fg_tid:
        USER32.AttachThreadInput(fg_tid, our, True)
    USER32.BringWindowToTop(hwnd)
    USER32.SetForegroundWindow(hwnd)
    if fg_tid:
        USER32.AttachThreadInput(fg_tid, our, False)
    USER32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    return int(previous) if previous else None


def _window_title(hwnd: int) -> str:
    if USER32 is None or not hwnd:
        return ""
    length = USER32.GetWindowTextLengthW(hwnd)
    if length < 1:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    USER32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value.strip()


def _is_ours(title: str) -> bool:
    lowered = (title or "").lower()
    return "saltvoice" in lowered or "grok handsfree" in lowered


def _paste_into_hwnd(hwnd: int, title: str, instruction: str, *, restore_previous: bool = True) -> str:
    previous = _focus(hwnd)
    time.sleep(0.2)
    _click_input(hwnd)
    time.sleep(0.15)
    method = "type"
    try:
        clip = _set_clipboard_text(instruction)
        method = f"paste/{clip}"
        _paste_and_enter()
        log.info("handoff pasted via %s into %r chars=%s", clip, title, len(instruction))
    except Exception as exc:
        log.warning("paste failed (%s); typing into %r instead", exc, title)
        _focus(hwnd)
        time.sleep(0.12)
        _click_input(hwnd)
        time.sleep(0.1)
        _type_text(instruction)
        log.info("handoff typed into %r chars=%s", title, len(instruction))
        method = "type"
    time.sleep(0.35)
    _call_topmost(True)
    if restore_previous and previous and USER32 is not None:
        prev_title = _window_title(previous).lower()
        if not _is_ours(prev_title) and "grok" not in prev_title:
            USER32.SetForegroundWindow(previous)
    return method


def send_to_window(instruction: str, titles: list[str]) -> dict[str, Any]:
    _configure_winapi()
    visible = [(h, t) for h, t in list_windows()]
    match = find_grok_window(titles)
    if not match:
        titles_only = [t for _h, t in visible][:40]
        log.warning("no Grok Bot window. visible=%s", titles_only)
        return {
            "status": "error",
            "error": "Could not find a Grok Bot window. Open Grok Bot first.",
            "visible_windows": titles_only,
        }
    hwnd, title = match
    log.info("handoff targeting window %r hwnd=%s", title, hwnd)
    print(f"HANDOFF window: {title}", flush=True)
    _call_topmost(False)
    time.sleep(0.15)
    method = _paste_into_hwnd(hwnd, title, instruction)
    return {"status": "ok", "method": "window", "window": title, "input": method}


def send_to_active_window(instruction: str) -> dict[str, Any]:
    """Paste into the frontmost app (not Saltvoice). For dictation into other programs."""
    if USER32 is None:
        return {"status": "error", "error": "Foreground paste is only available on Windows"}
    _configure_winapi()
    _call_topmost(False)
    time.sleep(0.2)
    hwnd = int(USER32.GetForegroundWindow() or 0)
    title = _window_title(hwnd)
    if not hwnd or _is_ours(title):
        for other, other_title in list_windows():
            if other != hwnd and not _is_ours(other_title):
                hwnd, title = other, other_title
                break
    if not hwnd or _is_ours(title):
        return {"status": "error", "error": "No other window is focused. Click the app you want, then speak."}
    log.info("handoff targeting front window %r hwnd=%s", title, hwnd)
    print(f"HANDOFF window: {title}", flush=True)
    method = _paste_into_hwnd(hwnd, title, instruction, restore_previous=False)
    return {"status": "ok", "method": "foreground", "window": title, "input": method}


def send_to_cli(instruction: str, cwd: Path, cli: str = "grok") -> dict[str, Any]:
    exe = shutil.which(cli) or shutil.which("grok.exe")
    if not exe:
        return {
            "status": "error",
            "error": "grok CLI not on PATH. Install Grok Build or keep Grok Bot open.",
        }
    cwd.mkdir(parents=True, exist_ok=True)
    log.info("starting %s -p in %s", exe, cwd)
    flags = CREATE_NO_WINDOW if os.name == "nt" else 0
    proc = subprocess.Popen(
        [exe, "-p", instruction],
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        creationflags=flags,
    )
    return {"status": "started", "method": "cli", "pid": proc.pid, "cwd": str(cwd), "process": proc}


_send_lock = threading.Lock()


def send_instruction(instruction: str, cwd: Path, cfg: GrokBotConfig) -> dict[str, Any]:
    text = (instruction or "").strip()
    if not text:
        return {"status": "error", "error": "Empty instruction"}
    with _send_lock:
        if os.name != "nt" and cfg.prefer == "window":
            return send_to_cli(text, cwd, cfg.cli)

        if cfg.target in {"here", "foreground", "front", "active"} and os.name == "nt":
            try:
                result = send_to_active_window(text)
            except Exception as exc:
                log.exception("foreground handoff crashed")
                result = {"status": "error", "error": str(exc)}
            if result.get("status") in {"ok", "started"}:
                return result

        errors: list[str] = []
        order = ["window", "cli"] if cfg.prefer != "cli" else ["cli", "window"]
        result = {"status": "error", "error": "No send method worked"}
        for method in order:
            try:
                if method == "window" and os.name == "nt":
                    result = send_to_window(text, cfg.window_titles)
                else:
                    result = send_to_cli(text, cwd, cfg.cli)
            except Exception as exc:
                log.exception("%s handoff crashed", method)
                result = {"status": "error", "error": f"{method}: {exc}"}
            if result.get("status") in {"ok", "started"}:
                return result
            errors.append(str(result.get("error") or method))
        result["attempts"] = errors
        return result
