from __future__ import annotations

import logging
import os
import threading
from pathlib import Path

import numpy as np

from saltvoice_local.pcm import resample_pcm16, rms_int16

log = logging.getLogger("saltvoice_local")

WHISPER_RATE = 16_000

_model = None
_model_lock = threading.Lock()
_model_name = ""


def load_model(name: str, device: str, compute_type: str, download_root: Path | None = None):
    """Load Whisper once. First run downloads the model into download_root."""
    global _model, _model_name
    with _model_lock:
        key = f"{name}:{device}:{compute_type}"
        if _model is not None and _model_name == key:
            return _model
        from faster_whisper import WhisperModel

        kwargs: dict = {"device": device, "compute_type": compute_type}
        if download_root is not None:
            download_root.mkdir(parents=True, exist_ok=True)
            kwargs["download_root"] = str(download_root)
        os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
        os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
        log.info("loading local Whisper %s (%s/%s)…", name, device, compute_type)
        _model = WhisperModel(name, **kwargs)
        _model_name = key
        log.info("Whisper ready")
        return _model


def transcribe_pcm(
    pcm: bytes,
    sample_rate: int = 24000,
    language: str = "en",
    min_rms: float = 0.008,
) -> str:
    if not pcm or _model is None:
        return ""
    if rms_int16(pcm) < min_rms:
        return ""
    if sample_rate != WHISPER_RATE:
        pcm = resample_pcm16(pcm, sample_rate, WHISPER_RATE)
    audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    if audio.size < WHISPER_RATE // 4:
        return ""
    try:
        kwargs = dict(
            language=language or "en",
            beam_size=3,
            vad_filter=False,
            without_timestamps=True,
            condition_on_previous_text=False,
            initial_prompt="Salt wake up. Salt go on standby. Salt send to grok.",
        )
        try:
            segments, _info = _model.transcribe(audio, **kwargs)
        except TypeError:
            kwargs.pop("condition_on_previous_text", None)
            kwargs.pop("initial_prompt", None)
            segments, _info = _model.transcribe(audio, **kwargs)
        text = " ".join(seg.text.strip() for seg in segments if getattr(seg, "text", None)).strip()
        return text
    except Exception as exc:
        log.warning("local STT failed: %s", exc)
        return ""
