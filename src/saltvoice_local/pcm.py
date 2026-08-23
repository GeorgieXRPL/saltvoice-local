from __future__ import annotations

import base64

import numpy as np

SAMPLE_RATE = 24_000
CHANNELS = 1
DTYPE = "int16"
BLOCK_FRAMES = 480
BYTES_PER_FRAME = 2


def rms_int16(pcm: bytes) -> float:
    if not pcm:
        return 0.0
    samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float32)
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(samples / 32768.0))))


def resample_pcm16(pcm: bytes, src_rate: int, dst_rate: int) -> bytes:
    if src_rate == dst_rate or not pcm:
        return pcm
    src = np.frombuffer(pcm, dtype=np.int16).astype(np.float32)
    if src.size == 0:
        return pcm
    duration = src.size / float(src_rate)
    dst_count = max(1, int(round(duration * dst_rate)))
    src_x = np.linspace(0.0, duration, num=src.size, endpoint=False)
    dst_x = np.linspace(0.0, duration, num=dst_count, endpoint=False)
    dst = np.interp(dst_x, src_x, src)
    return np.clip(dst, -32768, 32767).astype(np.int16).tobytes()


def pcm16_to_b64(pcm: bytes) -> str:
    return base64.b64encode(pcm).decode("ascii")


def b64_to_pcm16(data: str) -> bytes:
    return base64.b64decode(data)
