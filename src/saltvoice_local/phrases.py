from __future__ import annotations

import re

WAKE_PHRASES = (
    "salt open voice over",
    "salt start voice over",
    "salt open voice",
    "salt start voice",
    "salt voice over",
    "open voice over",
    "start voice over",
    "hey salt",
    "ok salt",
    "okay salt",
    "salt listen",
    "salt wake",
)

SLEEP_PHRASES = (
    "salt stop voice over",
    "stop voice over",
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
)

# Whisper often writes VoiceOver as one word, and hears Salt as Sol/Saul.
_VOICEOVER = re.compile(r"voice[\s\-]*over", re.I)
_SALT_ALIAS = re.compile(r"\b(sol|saul|assault|salts)\b")


def normalize(text: str) -> str:
    lowered = text.lower().replace("'", "")
    lowered = _VOICEOVER.sub("voice over", lowered)
    lowered = re.sub(r"[^a-z0-9\s]+", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return _SALT_ALIAS.sub("salt", lowered)


def is_sleep_phrase(text: str) -> bool:
    n = normalize(text)
    if not n:
        return False
    if any(p in n for p in SLEEP_PHRASES):
        return True
    words = n.split()
    if "off" in words and ("voice" in words or "salt" in words):
        return True
    return "salt" in words and any(w in words for w in ("sleep", "close", "stop"))


def is_wake_phrase(text: str) -> bool:
    if is_sleep_phrase(text):
        return False
    n = normalize(text)
    if not n:
        return False
    if any(p in n for p in WAKE_PHRASES):
        return True
    words = n.split()
    if "salt" in words and "voice" in words:
        return True
    return "salt" in words and any(w in words for w in ("listen", "wake"))
