from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]


def app_data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "SaltvoiceLocal"
    return Path.home() / ".saltvoice-local"


@dataclass
class Hotkeys:
    toggle_listen: str = "<ctrl>+<alt>+g"
    hold_talk: str = "<ctrl>+<cmd>"
    cancel: str = "<ctrl>+<alt>+x"
    toggle_overlay: str = "<ctrl>+<alt>+h"


@dataclass
class OverlayConfig:
    show_on_start: bool = True


@dataclass
class Settings:
    whisper_model: str = "tiny.en"
    device: str = "cpu"
    compute_type: str = "int8"
    language: str = "en"
    listen_mode: str = "wake"
    hotkeys: Hotkeys = field(default_factory=Hotkeys)
    overlay: OverlayConfig = field(default_factory=OverlayConfig)
    auto_sleep_minutes: float = 8.0
    workspace: str = ""
    grok_window_titles: list[str] = field(
        default_factory=lambda: ["Grok Bot", "Grok", "Grok Build"]
    )
    grok_prefer: str = "window"
    grok_cli: str = "grok"
    handoff_target: str = "grok"
    config_path: Path = field(default_factory=lambda: ROOT / "config.yaml")

    @property
    def workspace_path(self) -> Path:
        raw = (self.workspace or "").strip()
        if raw:
            return Path(raw).expanduser()
        return Path.home() / "Documents"

    @property
    def model_dir(self) -> Path:
        return app_data_dir() / "models"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config at {path} must be a mapping")
    return data


def load_settings() -> Settings:
    example = ROOT / "config.example.yaml"
    local = ROOT / "config.yaml"
    if not local.exists() and example.exists():
        local.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")

    data = _load_yaml(local)
    hot = data.get("hotkeys") or {}
    overlay = data.get("overlay") or {}
    grok = data.get("grok_bot") or {}
    titles = grok.get("window_titles") or ["Grok Bot", "Grok", "Grok Build"]
    stt = data.get("stt") or {}

    return Settings(
        whisper_model=str(stt.get("model") or data.get("whisper_model") or "tiny.en"),
        device=str(stt.get("device") or "cpu"),
        compute_type=str(stt.get("compute_type") or "int8"),
        language=str(stt.get("language") or "en"),
        listen_mode=str(data.get("listen_mode") or "wake").lower(),
        hotkeys=Hotkeys(
            toggle_listen=str(hot.get("toggle_listen") or "<ctrl>+<alt>+g"),
            hold_talk=str(hot.get("hold_talk") or "<ctrl>+<cmd>"),
            cancel=str(hot.get("cancel") or "<ctrl>+<alt>+x"),
            toggle_overlay=str(hot.get("toggle_overlay") or "<ctrl>+<alt>+h"),
        ),
        overlay=OverlayConfig(show_on_start=bool(overlay.get("show_on_start", True))),
        auto_sleep_minutes=float(data.get("auto_sleep_minutes") or 8),
        workspace=str(data.get("workspace") or ""),
        grok_window_titles=[str(t) for t in titles],
        grok_prefer=str(grok.get("prefer") or "window"),
        grok_cli=str(grok.get("cli") or "grok"),
        handoff_target=str(grok.get("target") or data.get("handoff_target") or "grok").lower(),
        config_path=local,
    )


def describe_setup(settings: Settings) -> list[str]:
    return [
        "Mode: standalone local Whisper (no xAI / no API key)",
        f"Whisper model: {settings.whisper_model} on {settings.device}/{settings.compute_type}",
        "Speech path: microphone → local text → paste into Grok Bot (or the front window)",
        f"Grok Bot windows: {', '.join(settings.grok_window_titles)}",
        f"Default target: {settings.handoff_target}",
        f"Workspace: {settings.workspace_path}"
        + (" (exists)" if settings.workspace_path.exists() else " (folder missing)"),
        "Starts listening as soon as it opens",
        "Sleep: Salt go to sleep  (say Salt wake up to listen again)",
        f"Python: {sys.version.split()[0]}",
    ]
