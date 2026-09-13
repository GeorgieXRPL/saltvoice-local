"""Transcript clip marks (text window), NOT Streamlabs/OBS replay."""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("saltvoice_local")

_LOCK = threading.Lock()
_BUFFER: list[tuple[float, str]] = []
_DEFAULT_WINDOW_S = 30.0
_MAX_ENTRIES = 200


def default_clips_folder() -> Path:
    # Prefer repo clips/ next to saltvoice-local root (…/saltvoice-local/clips).
    here = Path(__file__).resolve()
    # …/src/saltvoice_local/clip_mark.py → parents[2] = saltvoice-local
    root = here.parents[2]
    return root / "clips"


def push_transcript(text: str, *, at: float | None = None) -> None:
    """Record a transcript line for later clip marks."""
    cleaned = (text or "").strip()
    if not cleaned:
        return
    import time

    stamp = float(at if at is not None else time.time())
    with _LOCK:
        _BUFFER.append((stamp, cleaned))
        if len(_BUFFER) > _MAX_ENTRIES:
            del _BUFFER[: len(_BUFFER) - _MAX_ENTRIES]


def recent_transcript(window_seconds: float = _DEFAULT_WINDOW_S) -> str:
    """Return joined transcript lines from the last window_seconds (or all if shorter)."""
    import time

    now = time.time()
    cutoff = now - max(0.5, float(window_seconds))
    with _LOCK:
        lines = [t for ts, t in _BUFFER if ts >= cutoff]
        if not lines and _BUFFER:
            # Fall back to whatever we have (short session).
            lines = [t for _, t in _BUFFER]
    # De-dupe consecutive identical lines
    out: list[str] = []
    for line in lines:
        if out and out[-1] == line:
            continue
        out.append(line)
    return "\n".join(out).strip()


def clips_folder_from_settings(settings: Any = None) -> Path:
    folder = ""
    if settings is not None:
        clip = getattr(settings, "clip", None)
        if isinstance(settings, dict):
            clip = settings.get("clip") or settings
        if isinstance(clip, dict):
            folder = str(clip.get("marks_folder") or clip.get("transcript_folder") or "")
        elif clip is not None:
            folder = str(
                getattr(clip, "marks_folder", "")
                or getattr(clip, "transcript_folder", "")
                or ""
            )
    if folder.strip():
        return Path(folder).expanduser()
    return default_clips_folder()


def save_clip_mark(
    text: str | None = None,
    *,
    source: str = "local",
    settings: Any = None,
    folder: Path | str | None = None,
    window_seconds: float = _DEFAULT_WINDOW_S,
) -> dict[str, str]:
    """
    Write a transcript clip mark file.

    If text is blank/None, use the recent transcript buffer.
    Returns {"path": ...} on success, {"status":"skipped","reason":"empty"} if nothing to save,
    or {"error": ...} on IO failure.
    """
    body = (text or "").strip()
    if not body:
        body = recent_transcript(window_seconds)
    if not body:
        return {"status": "skipped", "reason": "empty"}

    dest_dir = Path(folder).expanduser() if folder else clips_folder_from_settings(settings)
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return {"error": f"cannot create {dest_dir}: {exc}"}

    now = datetime.now().astimezone()
    stamp = now.strftime("%Y%m%d-%H%M%S")
    dest = dest_dir / f"clip-{stamp}.txt"
    n = 2
    while dest.exists():
        dest = dest_dir / f"clip-{stamp}-{n}.txt"
        n += 1

    iso = now.isoformat(timespec="seconds")
    src = (source or "local").strip() or "local"
    content = f"time: {iso}\nsource: {src}\n\n{body}\n"
    try:
        dest.write_text(content, encoding="utf-8")
    except OSError as exc:
        return {"error": f"write failed: {exc}"}

    log.info("clip mark saved: %s (%s, %s chars)", dest, src, len(body))
    return {"path": str(dest), "status": "ok"}
