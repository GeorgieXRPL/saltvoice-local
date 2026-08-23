#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from saltvoice_local.pcm import resample_pcm16, rms_int16
from saltvoice_local.phrases import classify_utterance, is_sleep_phrase, is_wake_phrase
from saltvoice_local.state import Hub, Phase


def test_resample() -> None:
    silence = b"\x00\x00" * 240
    out = resample_pcm16(silence, 24000, 48000)
    assert len(out) == 480 * 2
    assert rms_int16(silence) == 0.0


def test_phrases() -> None:
    assert classify_utterance("Salt wake up") == "wake"
    assert classify_utterance("Salt, go on standby") == "standby"
    assert classify_utterance("Salt go on stand by") == "standby"
    assert classify_utterance("Salt send here") == "target_here"
    assert classify_utterance("Salt send to Grok Bot") == "target_grok"
    assert classify_utterance("Open the download folder") == "task"
    assert classify_utterance("Salt, open the download folder") == "task"
    assert is_wake_phrase("Salt, open voice over")
    assert is_wake_phrase("hey salt")
    assert is_sleep_phrase("Stop, stop voiceover.")
    assert is_sleep_phrase("salt stop")
    assert not is_wake_phrase("please pass the salt")
    assert classify_utterance("Salt stop voice over") == "standby"


def test_hub() -> None:
    hub = Hub()
    hub.emit("ready", phase=Phase.LISTENING, status_line="hi")
    assert hub.phase is Phase.LISTENING


if __name__ == "__main__":
    test_resample()
    test_phrases()
    test_hub()
    print("ok")
