from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger("saltvoice_local")

DEFAULT_BRAIN = """# Saltvoice memory — your accent, nicknames, and saved phrases.
# The overlay Teach box writes into corrections. No restart needed.

corrections:
  # What Whisper heard: what you meant
  # soat: salt
  # soak: salt

shortcuts:
  # What you say: the full task to paste into Grok Bot
  # the usual: Open the Windows Downloads folder.

commands:
  # Extra wake/standby phrases in your own words
  # thats enough: standby
  # back to work: wake

settings:
  finish_wait_seconds: 2.2
"""


class Brain:
    """Persistent phrase book. Not an LLM — it remembers your words."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.corrections: dict[str, str] = {}
        self.shortcuts: dict[str, str] = {}
        self.commands: dict[str, str] = {}
        self.finish_wait = 2.2
        self.load()

    def load(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(DEFAULT_BRAIN, encoding="utf-8")
        try:
            data = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            log.warning("brain.yaml unreadable (%s); using empty memory", exc)
            data = {}
        if not isinstance(data, dict):
            data = {}
        self.corrections = _str_map(data.get("corrections"))
        self.shortcuts = _str_map(data.get("shortcuts"))
        self.commands = _str_map(data.get("commands"))
        settings = data.get("settings") if isinstance(data.get("settings"), dict) else {}
        try:
            self.finish_wait = float(settings.get("finish_wait_seconds") or 2.2)
        except (TypeError, ValueError):
            self.finish_wait = 2.2
        self.finish_wait = max(0.8, min(4.0, self.finish_wait))
        self._push_into_phrases()
        log.info(
            "brain: %s correction(s), %s shortcut(s), %s command(s) from %s",
            len(self.corrections),
            len(self.shortcuts),
            len(self.commands),
            self.path,
        )

    def save(self) -> None:
        payload = {
            "corrections": self.corrections,
            "shortcuts": self.shortcuts,
            "commands": self.commands,
            "settings": {"finish_wait_seconds": self.finish_wait},
        }
        self.path.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        self._push_into_phrases()

    def add_correction(self, heard: str, meant: str) -> str:
        heard_key = _plain(heard)
        meant_val = (meant or "").strip()
        if not heard_key or not meant_val:
            return "Type what it heard and what you meant, then Save."
        self.corrections[heard_key] = meant_val
        self.save()
        log.info("brain correction: %r → %r", heard_key, meant_val)
        return f"Saved: “{heard_key}” means “{meant_val}”."

    def add_shortcut(self, spoken: str, task: str) -> str:
        key = _plain(spoken)
        task = (task or "").strip()
        if not key or not task:
            return "Type a short name and the full task."
        self.shortcuts[key] = task
        self.save()
        return f"Saved shortcut: “{key}”."

    def add_command(self, phrase: str, kind: str) -> str:
        key = _plain(phrase)
        kind = (kind or "").strip().lower().replace(" ", "_")
        if kind in {"sleep", "stop", "pause"}:
            kind = "standby"
        if kind in {"listen", "start"}:
            kind = "wake"
        if not key:
            return "Type a phrase, then choose wake or standby."
        if kind not in {"wake", "standby", "target_grok", "target_here"}:
            return "Choose wake or standby."
        self.commands[key] = kind
        self.save()
        return f"Saved phrase: “{key}” means {kind}."

    def set_finish_wait(self, seconds: float) -> str:
        try:
            value = float(seconds)
        except (TypeError, ValueError):
            return "Wait time must be a number of seconds."
        self.finish_wait = max(0.8, min(4.0, value))
        self.save()
        return f"Wait {self.finish_wait:.1f}s after you stop talking before sending."

    def snapshot(self) -> dict[str, Any]:
        return {
            "corrections": dict(self.corrections),
            "shortcuts": dict(self.shortcuts),
            "commands": dict(self.commands),
            "finish_wait": self.finish_wait,
            "path": str(self.path),
        }

    def expand_shortcut(self, text: str) -> str | None:
        key = _plain(text)
        if not key:
            return None
        for spoken, task in self.shortcuts.items():
            if _plain(spoken) == key:
                return task
        return None

    def _push_into_phrases(self) -> None:
        from saltvoice_local.phrases import set_command_aliases, set_user_corrections

        set_user_corrections(self.corrections)
        set_command_aliases(self.commands)


def _plain(text: str) -> str:
    import re

    lowered = (text or "").lower().replace("'", "")
    lowered = re.sub(r"[^a-z0-9\s]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def _str_map(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for key, value in raw.items():
        k = str(key or "").strip()
        v = str(value or "").strip()
        if k and v:
            out[k] = v
    return out


def brain_path() -> Path:
    from saltvoice_local.config import app_data_dir

    return app_data_dir() / "brain.yaml"
