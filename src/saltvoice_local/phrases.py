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
        "soat",
        "sot",
        "huh",
    }
)

PROFANITY = frozenset(
    {
        "fuck",
        "fucking",
        "shit",
        "damn",
        "ass",
        "bitch",
        "crap",
        "hell",
    }
)

# tiny.en often hears "salt" as these. Map them before matching commands.
SALT_MISHEARS = frozenset(
    {
        "sol",
        "saul",
        "assault",
        "salts",
        "soat",
        "sult",
        "sault",
        "slt",
        "soed",
        "sawt",
        "soult",
        "psalt",
        "soalt",
        "sot",
        "sal",
        "zalt",
        "saults",
        "soka",
        "soaka",
        "sok",
    }
)

_COMMAND_STARTERS = frozenset(
    {
        "open",
        "close",
        "launch",
        "start",
        "search",
        "go",
        "show",
        "hide",
        "quit",
        "exit",
        "build",
        "make",
        "create",
        "write",
        "type",
        "click",
        "press",
        "find",
        "play",
        "pause",
        "navigate",
        "pull",
        "update",
        "turn",
        "put",
        "set",
        "delete",
        "remove",
        "install",
        "run",
        "send",
        "ask",
        "tell",
        "look",
        "bring",
        "switch",
        "move",
        "copy",
        "paste",
        "save",
        "load",
        "refresh",
        "scroll",
        "zoom",
        "mute",
        "volume",
        "not",
        "can",
        "please",
        "hey",
    }
)

_STANDBY_FILLER = frozenset(
    {
        "salt",
        "go",
        "on",
        "standby",
        "please",
        "the",
        "now",
        "so",
        "soat",
        "soak",
        "lets",
        "let",
        "us",
        "to",
        "and",
        "just",
        "you",
        "hey",
        "ok",
        "okay",
        "stop",
        "going",
        "gonna",
        "same",
        "boy",
        "boys",
        "stand",
        "by",
        "my",
        "me",
        "a",
        "oh",
        "out",
        "saw",
        "salts",
        "cut",
        "asleep",
        "sleep",
        "pause",
        "quiet",
        "voice",
        "over",
        "listening",
    }
)

_STANDBY_TASKISH = frozenset(
    {
        "open",
        "close",
        "put",
        "chrome",
        "firefox",
        "edge",
        "window",
        "app",
        "download",
        "folder",
        "file",
        "browser",
        "tab",
    }
)

_BYE_FILLER = frozenset(
    {
        "salt",
        "so",
        "soat",
        "soak",
        "say",
        "go",
        "and",
        "bye",
        "goodbye",
        "please",
        "the",
        "now",
        "just",
        "you",
        "hey",
        "ok",
        "okay",
        "lets",
        "let",
        "me",
        "my",
        "a",
        "oh",
        "out",
        "saw",
        "salts",
        "soka",
    }
)

_user_corrections: dict[str, str] = {}
_command_aliases: dict[str, str] = {}

_VOICEOVER = re.compile(r"voice[\s\-]*over", re.I)
_STANDBY_ALIAS = re.compile(r"\bstand\s+by\b")
_PHONETIC = (
    (re.compile(r"\bsame\s+boys?\b"), "standby"),
    (re.compile(r"\bstand\s+boys?\b"), "standby"),
    (re.compile(r"\bsand\s+by\b"), "standby"),
    (re.compile(r"\bsand\s+boys?\b"), "standby"),
    (re.compile(r"\bstan\s+by\b"), "standby"),
    (re.compile(r"\bgoing\s+same\b"), "go on"),
    (re.compile(r"\bgoin[g]?\s+same\b"), "go on"),
    (re.compile(r"\bwait(?:\s+the)?(?:\s+fuck)?\s+up\b"), "wake up"),
    (re.compile(r"\bcut\s+a?\s*sleep\b"), "cut sleep"),
)
_TASK_FIXES = (
    (re.compile(r"\bopen crime\b", re.I), "Open Chrome"),
    (re.compile(r"\bclose crime\b", re.I), "close Chrome"),
    (re.compile(r"\blaunch crime\b", re.I), "launch Chrome"),
    (re.compile(r"\bstart crime\b", re.I), "start Chrome"),
)
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
        "so",
        "soak",
        "soat",
        "you",
        "out",
        "oh",
        "saw",
        "soka",
        "just",
    }
)


def set_user_corrections(mapping: dict[str, str] | None) -> None:
    """Dialect / accent replacements from brain.yaml (heard → meant)."""
    global _user_corrections
    cleaned: dict[str, str] = {}
    for key, value in (mapping or {}).items():
        heard = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]+", " ", str(key).lower().replace("'", ""))).strip()
        meant = str(value or "").strip()
        if heard and meant:
            cleaned[heard] = meant.lower()
    _user_corrections = cleaned


def set_command_aliases(mapping: dict[str, str] | None) -> None:
    """User phrases that mean wake / standby / send here / send to grok."""
    global _command_aliases
    allowed = {"wake", "standby", "target_grok", "target_here"}
    cleaned: dict[str, str] = {}
    for key, value in (mapping or {}).items():
        phrase = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]+", " ", str(key).lower().replace("'", ""))).strip()
        kind = str(value or "").strip().lower().replace(" ", "_")
        if kind in {"sleep", "stop", "pause"}:
            kind = "standby"
        if kind in {"listen", "start"}:
            kind = "wake"
        if phrase and kind in allowed:
            cleaned[phrase] = kind
    _command_aliases = cleaned


def _apply_user_corrections(n: str) -> str:
    for heard, meant in sorted(_user_corrections.items(), key=lambda kv: len(kv[0]), reverse=True):
        if not heard:
            continue
        if " " in heard:
            n = n.replace(heard, meant)
        else:
            n = re.sub(rf"\b{re.escape(heard)}\b", meant, n)
    return n


def _map_salt_words(n: str) -> str:
    words = n.split()
    commandish = any(
        w in words
        for w in (
            "wake",
            "wakeup",
            "standby",
            "voice",
            "listen",
            "sleep",
            "stop",
            "up",
            "bye",
            "goodbye",
        )
    )
    saltish = {"so", "soak", "soaked", "oh", "out", "saw"}
    command_next = {
        "wake",
        "wakeup",
        "standby",
        "listen",
        "voice",
        "lets",
        "let",
        "go",
        "say",
        "bye",
        "sleep",
    }
    out: list[str] = []
    i = 0
    while i < len(words):
        nxt = words[i + 1] if i + 1 < len(words) else ""
        if words[i] == "you" and nxt == "salt":
            out.append("salt")
            i += 2
            continue
        if words[i] == "you" and nxt in {"wake", "wakeup"}:
            out.append("salt")
            i += 1
            continue
        if words[i] in saltish and nxt in {"lets", "let"}:
            out.append("salt")
            i += 2
            continue
        if words[i] in saltish and nxt in command_next:
            out.append("salt")
            i += 1
            continue
        if words[i] == "so" and nxt in {"at", "alt", "olt", "ought", "ot"}:
            out.append("salt")
            i += 2
            continue
        w = words[i]
        if w in SALT_MISHEARS:
            out.append("salt")
        elif w in {"soap", "sought", "soul", "sold"} and commandish:
            out.append("salt")
        else:
            out.append(w)
        i += 1
    return " ".join(out)


def normalize(text: str) -> str:
    lowered = text.lower().replace("'", "")
    lowered = _VOICEOVER.sub("voice over", lowered)
    lowered = _STANDBY_ALIAS.sub("standby", lowered)
    lowered = re.sub(r"\basleep\b", "sleep", lowered)
    for pattern, repl in _PHONETIC:
        lowered = pattern.sub(repl, lowered)
    lowered = re.sub(r"[^a-z0-9\s]+", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    lowered = _apply_user_corrections(lowered)
    lowered = _map_salt_words(lowered)
    if any(k in lowered for k in ("voice", "wake", "standby", "sleep", "stop", "salt", "bye")):
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


def polish_task(text: str) -> str:
    """Fix a few tiny.en app-name stumbles before pasting."""
    out = (text or "").strip()
    for pattern, repl in _TASK_FIXES:
        out = pattern.sub(repl, out)
    return out


def is_filler_utterance(text: str) -> bool:
    n = normalize(text)
    if not n or n in FILLERS:
        return True
    if len(n) < 4 and n not in {"bye", "stop", "wake"}:
        return True
    return False


def is_noise_utterance(text: str) -> bool:
    n = normalize(text)
    words = n.split()
    if not words:
        return True
    content = [w for w in words if w not in FILLERS and w not in PROFANITY]
    if not content:
        return True
    if len(content) == 1 and content[0] not in _COMMAND_STARTERS and content[0] not in {
        "salt",
        "wake",
        "standby",
        "chrome",
        "google",
    }:
        return True
    return False


def is_incomplete_utterance(text: str) -> bool:
    """A chopped first syllable of a command, not a real task."""
    if classify_utterance(text) != "task":
        return False
    if is_filler_utterance(text):
        return True
    n = normalize(text)
    words = n.split()
    if not words:
        return True
    if len(words) == 1:
        return True
    if len(words) <= 3 and words[0] not in _COMMAND_STARTERS:
        return True
    if n in {"salt so", "so salt", "hey salt so"}:
        return True
    return False


def is_standby_phrase(text: str) -> bool:
    n = normalize(text)
    if not n:
        return False
    if n in {"bye", "goodbye", "good bye", "say bye"}:
        return True
    if _has_any(n, STANDBY_PHRASES):
        return True
    words = n.split()
    tokens = set(words)
    if "bye" in tokens or "goodbye" in tokens:
        extra = [w for w in words if w not in _BYE_FILLER]
        if not extra:
            return True
    if "standby" in tokens:
        extra = [w for w in words if w not in _STANDBY_FILLER]
        if not extra:
            return True
        taskish = any(w in _STANDBY_TASKISH for w in extra)
        if not taskish and len(extra) <= 2:
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
    words = n.split()
    tokens = set(words)
    if "salt" in tokens and tokens & {"wake", "listen", "voice"}:
        return True
    if "wake" in tokens and ("up" in tokens or "wakeup" in tokens):
        extra = [w for w in words if w not in _WAKE_GLUE]
        if not extra:
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
    n = normalize(text)
    if n in _command_aliases:
        return _command_aliases[n]
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
