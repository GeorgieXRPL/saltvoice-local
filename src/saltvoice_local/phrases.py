from __future__ import annotations

import re

# Spoken to Saltvoice only. These must never be pasted into Grok Bot or other apps.
WAKE_PHRASES = (
    "salt wake up",
    "salt wakeup",
    "salt wake",
    "wake up salt",
    "wake salt",
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
    "salt go to sleep",
    "salt cut sleep",
    "salt close voice",
    "salt stop listening",
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

FILLERS = frozenset(
    {
        "so",
        "oh",
        "ok",
        "okay",
        "alright",
        "all right",
        "right",
        "um",
        "uh",
        "hmm",
        "yeah",
        "yep",
        "yup",
        "yes",
        "no",
        "ah",
        "huh",
        "mm",
        "mhm",
        "thanks",
        "thank you",
        "hi",
        "hello",
    }
)

_VOICEOVER = re.compile(r"voice[\s\-]*over", re.I)
_SALT_ALIAS = re.compile(r"\b(sol|saul|assault|salts)\b")
_STANDBY_ALIAS = re.compile(r"\bstand\s+by\b")
_WAKE_GLUE = frozenset(
    {
        "salt",
        "voice",
        "over",
        "hey",
        "ok",
        "okay",
        "open",
        "start",
        "listen",
        "wake",
        "up",
        "wakeup",
        "please",
        "the",
        "a",
        "me",
    }
)


def normalize(text: str) -> str:
    lowered = text.lower().replace("'", "")
    lowered = _VOICEOVER.sub("voice over", lowered)
    lowered = _STANDBY_ALIAS.sub("standby", lowered)
    lowered = re.sub(r"\basleep\b", "sleep", lowered)
    lowered = re.sub(r"[^a-z0-9\s]+", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    lowered = _SALT_ALIAS.sub("salt", lowered)
    # tiny.en: "soap" ≈ salt, "step" ≈ stop, only in command-like lines
    if any(k in lowered for k in ("voice", "wake", "standby", "sleep", "stop", "salt")):
        lowered = re.sub(r"\bsoap\b", "salt", lowered)
        lowered = re.sub(r"\bstep\b", "stop", lowered)
    return lowered


def _has_any(n: str, phrases: tuple[str, ...]) -> bool:
    return any(p in n for p in phrases)


def _starts_with_any(n: str, phrases: tuple[str, ...]) -> bool:
    return any(n.startswith(p) for p in phrases)


def _extra_words(n: str, phrases: tuple[str, ...], glue: frozenset[str]) -> list[str]:
    rest = f" {n} "
    for phrase in sorted(phrases, key=len, reverse=True):
        rest = rest.replace(f" {phrase} ", " ")
    return [w for w in rest.split() if w not in glue]


def is_filler_utterance(text: str) -> bool:
    n = normalize(text)
    if not n or n in FILLERS:
        return True
    if len(n) < 4:
        return True
    return False


def is_standby_phrase(text: str) -> bool:
    n = normalize(text)
    if not n:
        return False
    if _has_any(n, STANDBY_PHRASES):
        return True
    words = n.split()
    tokens = set(words)
    # Whisper often drops "Salt". Bare "on standby" / "go on standby" is still a command.
    if "standby" in tokens:
        extra = [w for w in words if w not in {"salt", "go", "on", "standby", "please", "the", "now"}]
        if not extra:
            return True
    if "salt" not in tokens:
        return bool(tokens & {"stop", "close"} and ("voice" in tokens or "voiceover" in tokens) and len(words) <= 6)
    if tokens & {"pause", "quiet", "sleep"}:
        return True
    if tokens & {"stop", "close"} and ("voice" in tokens or "voiceover" in tokens):
        return True
    if tokens & {"stop", "close"} and len(words) <= 5:
        return True
    return False


def is_sleep_phrase(text: str) -> bool:
    return is_standby_phrase(text)


def is_target_grok_phrase(text: str) -> bool:
    return _has_any(normalize(text), TARGET_GROK_PHRASES)


def is_target_here_phrase(text: str) -> bool:
    return _has_any(normalize(text), TARGET_HERE_PHRASES)


def _looks_like_wake(n: str) -> bool:
    if _has_any(n, WAKE_PHRASES):
        return True
    tokens = set(n.split())
    if "salt" in tokens and tokens & {"wake", "listen", "voice"}:
        return True
    return "wake" in tokens and "salt" in tokens


def is_wake_phrase(text: str) -> bool:
    if is_standby_phrase(text) or is_target_grok_phrase(text) or is_target_here_phrase(text):
        return False
    n = normalize(text)
    if not n or not _looks_like_wake(n):
        return False
    extra = _extra_words(n, WAKE_PHRASES, _WAKE_GLUE)
    # A long sentence that merely mentions Saltvoice is a task, not a wake command.
    if extra and len(extra) >= 3 and not _starts_with_any(n, WAKE_PHRASES + ("wake up salt", "wake salt")):
        return False
    return True


def remainder_after_wake(text: str) -> str:
    """If they said a wake command plus a task, return the task only."""
    n = normalize(text)
    prefixes = WAKE_PHRASES + ("wake up salt", "wake salt", "wakeup salt")
    rest = n
    matched = False
    for prefix in sorted(prefixes, key=len, reverse=True):
        if rest.startswith(prefix):
            rest = rest[len(prefix) :].strip()
            matched = True
            break
    if not matched or not rest or is_filler_utterance(rest):
        return ""
    if classify_utterance(rest) != "task":
        return ""
    return rest


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
