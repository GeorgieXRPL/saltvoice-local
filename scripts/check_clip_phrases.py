#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from saltvoice_local.phrases import classify_utterance, is_clip_phrase, is_wake_phrase


def expect(text: str, kind: str) -> None:
    got = classify_utterance(text)
    assert got == kind, f"{text!r} -> {got!r} (expected {kind!r})"


def main() -> None:
    clip_lines = (
        "Salt clip that",
        "salt clip this",
        "salt clip it",
        "salt save clip",
        "salt grab that",
        "salt clip",
        "clip that",
        "clip this",
        "Salt click that",
        "so clip that",
    )
    for line in clip_lines:
        expect(line, "clip")
        assert is_clip_phrase(line), f"{line!r} should be a clip phrase"
        assert not is_wake_phrase(line), f"{line!r} must not be stolen as wake"

    expect("click that", "task")
    assert not is_clip_phrase("click that")
    expect("Salt go on standby", "standby")
    expect("Salt wake up", "wake")
    expect("open chrome", "task")
    print("ok")


if __name__ == "__main__":
    main()
