from __future__ import annotations

import json
import logging
import shutil
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

log = logging.getLogger("saltvoice_local")

_LOCK = threading.Lock()
_REPLAY_PREFIX = "Replay"
_REPLAY_SUFFIXES = {".mp4", ".mkv"}
_DEFAULT_COMBO = "<ctrl>+<alt>+c"
_DEFAULT_OVERLAY = "http://127.0.0.1:8787/say"
_WAIT_SECONDS = 8.0


def save_clip(settings: Any = None) -> dict[str, str]:
    """Save Streamlabs Replay Buffer to Videos/stream-clips. Never pastes text."""
    with _LOCK:
        return _save_clip(settings)


def _clip_cfg(settings: Any) -> dict[str, str]:
    folder = ""
    replay_folder = ""
    combo = _DEFAULT_COMBO
    overlay_url = _DEFAULT_OVERLAY
    clip = settings
    if settings is not None and not isinstance(settings, dict):
        clip = getattr(settings, "clip", settings)
    if isinstance(clip, dict):
        folder = str(clip.get("folder") or "")
        replay_folder = str(clip.get("replay_folder") or "")
        combo = str(clip.get("hotkey") or combo)
        overlay_url = str(clip.get("overlay_url") or overlay_url)
    elif clip is not None:
        folder = str(getattr(clip, "folder", "") or "")
        replay_folder = str(getattr(clip, "replay_folder", "") or "")
        combo = str(getattr(clip, "hotkey", "") or combo)
        overlay_url = str(getattr(clip, "overlay_url", "") or overlay_url)
    return {
        "folder": folder.strip(),
        "replay_folder": replay_folder.strip(),
        "hotkey": combo.strip() or _DEFAULT_COMBO,
        "overlay_url": overlay_url.strip() or _DEFAULT_OVERLAY,
    }


def _save_clip(settings: Any) -> dict[str, str]:
    cfg = _clip_cfg(settings)
    dest_folder = Path(cfg["folder"]).expanduser() if cfg["folder"] else Path.home() / "Videos" / "stream-clips"
    src_folder = Path(cfg["replay_folder"]).expanduser() if cfg["replay_folder"] else Path.home() / "Videos"
    try:
        dest_folder.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return {"error": f"cannot create {dest_folder}: {exc}"}
    if not src_folder.is_dir():
        return {"error": f"replay folder missing: {src_folder}"}

    before = _replay_snapshot(src_folder)
    try:
        _send_combo(cfg["hotkey"])
    except Exception as exc:
        return {"error": f"hotkey failed: {exc}"}

    found = _wait_for_replay(src_folder, before, _WAIT_SECONDS)
    if found is None:
        return {"error": "no new Replay file in 8s"}

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = dest_folder / f"clip-{stamp}.mp4"
    n = 2
    while dest.exists():
        dest = dest_folder / f"clip-{stamp}-{n}.mp4"
        n += 1
    try:
        shutil.copy2(found, dest)
    except OSError as exc:
        return {"error": f"copy failed: {exc}"}

    _say_clipped(cfg["overlay_url"])
    log.info("clip saved: %s (from %s)", dest, found.name)
    return {"path": str(dest)}


def _replay_snapshot(folder: Path) -> dict[Path, tuple[float, int]]:
    out: dict[Path, tuple[float, int]] = {}
    try:
        entries = list(folder.iterdir())
    except OSError:
        return out
    for path in entries:
        if not path.is_file():
            continue
        if not path.name.startswith(_REPLAY_PREFIX):
            continue
        if path.suffix.lower() not in _REPLAY_SUFFIXES:
            continue
        try:
            st = path.stat()
        except OSError:
            continue
        out[path] = (st.st_mtime, st.st_size)
    return out


def _wait_for_replay(
    folder: Path,
    before: dict[Path, tuple[float, int]],
    timeout: float,
) -> Path | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        time.sleep(0.2)
        now = _replay_snapshot(folder)
        changed = [path for path, meta in now.items() if before.get(path) != meta]
        if not changed:
            continue
        best = max(changed, key=lambda p: now[p][0])
        if now[best][1] <= 0:
            continue
        time.sleep(0.3)
        try:
            size = best.stat().st_size
        except OSError:
            continue
        if size > 0:
            return best
    return None


def _say_clipped(url: str) -> None:
    if not url:
        return
    try:
        data = json.dumps({"text": "Clipped"}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=1.5).read()
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return


def _send_combo(spec: str) -> None:
    from pynput.keyboard import Controller, Key

    alias = {
        "ctrl": Key.ctrl,
        "control": Key.ctrl,
        "alt": Key.alt,
        "shift": Key.shift,
        "cmd": Key.cmd,
        "win": Key.cmd,
        "windows": Key.cmd,
        "super": Key.cmd,
    }
    parts = [x.strip("<> ").lower() for x in spec.split("+") if x.strip()]
    if not parts:
        parts = ["ctrl", "alt", "c"]
    mods = []
    tap_key = "c"
    for part in parts:
        if part in alias:
            mods.append(alias[part])
        elif len(part) == 1:
            tap_key = part
        else:
            tap_key = part
    kb = Controller()
    if mods:
        with kb.pressed(*mods):
            kb.tap(tap_key)
            time.sleep(0.05)
    else:
        kb.tap(tap_key)

