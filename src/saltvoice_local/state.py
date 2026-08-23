from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class Phase(str, Enum):
    SLEEPING = "sleeping"
    LISTENING = "listening"
    HEARING = "hearing"
    SPEAKING = "speaking"
    WORKING = "working"
    ERROR = "error"


Listener = Callable[[str, dict[str, Any]], None]


@dataclass
class Hub:
    phase: Phase = Phase.SLEEPING
    armed: bool = False
    user_text: str = ""
    assistant_text: str = ""
    status_line: str = "Press Ctrl+Alt+G to talk"
    listeners: list[Listener] = field(default_factory=list)

    def subscribe(self, fn: Listener) -> None:
        self.listeners.append(fn)

    def emit(self, event: str, **payload: Any) -> None:
        if "phase" in payload and isinstance(payload["phase"], Phase):
            self.phase = payload["phase"]
        if "armed" in payload:
            self.armed = bool(payload["armed"])
        if "user_text" in payload:
            self.user_text = str(payload["user_text"])
        if "assistant_text" in payload:
            self.assistant_text = str(payload["assistant_text"])
        if "status_line" in payload:
            self.status_line = str(payload["status_line"])
        snapshot = {
            "phase": self.phase,
            "armed": self.armed,
            "user_text": self.user_text,
            "assistant_text": self.assistant_text,
            "status_line": self.status_line,
            **payload,
        }
        for fn in list(self.listeners):
            fn(event, snapshot)
