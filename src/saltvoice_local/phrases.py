from __future__ import annotations

import re

# Spoken to Saltvoice only. These must never be pasted into Grok Bot or other apps.
WAKE_PHRASES = (
    "salt wake up",
    "salt wakeup",
    "salt wake",
    "hey salt",
    "ok salt",
    "okay salt",
    "salt listen",
    "salt open voice over",
    "salt start voice over",
    "salt open voice",
    "salt start voice",
    "salt voice over",
    "open voice over",
    "start voice over",
)

STANDBY_PHRASES = (
    "salt go on standby",
    "salt go on stand by",
    "salt on standby",
    "salt on stand by",
    "salt standby",
    "salt stand by",
    "salt pause",
    "salt quiet",
    "salt stop voice over",
    "stop salt voice over",
    "stop voice over",
    "salt voice over stop",
    "salt close voice over",
    "salt turn voice over off",
    "turn voice over off",
    "voice over off",
    "salt sleep",
    "salt close voice",
    "salt stop listening",
    "salt go to sleep",
    "that's all salt",
    "thats all salt",
    "salt turn off",
    "salt stop",
    "stop salt",
)

TARGET_GROK_PHRASES = (
    "salt send to grok bot",
    "salt send to grok",
    "salt use grok bot",
    "salt use grok",
)

TARGET_HERE_PHRASES = (
    "salt send here",
    "salt send to this window",
    "salt send to this app",
    "salt use this window",
    "salt send to the front",
)

_VOICEOVER = re.compile(r"voice[\s\-]*over", re.I)
_SALT_ALIAS = re.compile(r"\b(sol|saul|assault|salts)\b")
_STANDBY_ALIAS = re.compile(r"\bstand\s+by\b")


def normalize(text: str) -> str:
    lowered = text.lower().replace("'", "")
    lowered = _VOICEOVER.sub("voice over", lowered)
    lowered = _STANDBY_ALIAS.sub("standby", lowered)
    lowered = re.sub(r"[^a-z0-9\s]+", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return _SALT_ALIAS.sub("salt", lowered)


def _has_any(n: str, phrases: tuple[str, ...]) -> bool:
    return any(p in n for p in phrases)


def is_standby_phrase(text: str) -> bool:
    n = normalize(text)
    if not n:
        return False
    if _has_any(n, STANDBY_PHRASES):
        return True
    words = n.split()
    tokens = set(words)
    if "salt" not in tokens:
        return False
    if "standby" in tokens or tokens & {"pause", "quiet", "sleep"}:
        return True
    # Any order: "stop salt voice over", "salt, stop, voiceover"
    if tokens & {"stop", "close"} and ("voice" in tokens or "voiceover" in tokens):
        return True
    # Short "stop salt" / "salt stop" — never paste the word stop into Grok Bot
    if tokens & {"stop", "close"} and len(words) <= 5:
        return True
    return False


def is_sleep_phrase(text: str) -> bool:
    return is_standby_phrase(text)


def is_target_grok_phrase(text: str) -> bool:
    return _has_any(normalize(text), TARGET_GROK_PHRASES)


def is_target_here_phrase(text: str) -> bool:
    return _has_any(normalize(text), TARGET_HERE_PHRASES)


def is_wake_phrase(text: str) -> bool:
    if is_standby_phrase(text) or is_target_grok_phrase(text) or is_target_here_phrase(text):
        return False
    n = normalize(text)
    if not n:
        return False
    if _has_any(n, WAKE_PHRASES):
        return True
    words = n.split()
    if "salt" in words and "wake" in words:
        return True
    if "salt" in words and "voice" in words:
        return True
    return "salt" in words and "listen" in words


def classify_utterance(text: str) -> str:
    """wake | standby | target_grok | target_here | task"""
    if is_standby_phrase(text):
        return "standby"
    if is_target_grok_phrase(text):
        return "target_grok"
    if is_target_here_phrase(text):
        return "target_here"
    if is_wake_phrase(text):
        return "wake"
    return "task"


def is_control_phrase(text: str) -> bool:
    return classify_utterance(text) != "task"
