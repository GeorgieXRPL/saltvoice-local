from __future__ import annotations

import asyncio
import threading
from typing import Callable

import sounddevice as sd

from saltvoice_local.pcm import BLOCK_FRAMES, CHANNELS, DTYPE, SAMPLE_RATE, resample_pcm16


class Microphone:
    def __init__(self, on_pcm: Callable[[bytes], None], sample_rate: int = SAMPLE_RATE) -> None:
        self.on_pcm = on_pcm
        self.sample_rate = sample_rate
        self._stream: sd.RawInputStream | None = None
        self._armed = threading.Event()
        self._device_rate = sample_rate

    def arm(self, value: bool) -> None:
        if value:
            self._armed.set()
        else:
            self._armed.clear()

    def start(self) -> None:
        if self._stream is not None:
            return
        try:
            self._stream = sd.RawInputStream(
                samplerate=self.sample_rate,
                channels=CHANNELS,
                dtype=DTYPE,
                blocksize=BLOCK_FRAMES,
                callback=self._callback,
            )
            self._device_rate = self.sample_rate
        except Exception:
            device = sd.query_devices(kind="input")
            rate = int(device.get("default_samplerate") or 48000)
            self._stream = sd.RawInputStream(
                samplerate=rate,
                channels=CHANNELS,
                dtype=DTYPE,
                blocksize=0,
                callback=self._callback,
            )
            self._device_rate = rate
        self._stream.start()

    def _callback(self, indata, _frames, _time, _status) -> None:  # noqa: ANN001
        if not self._armed.is_set():
            return
        pcm = bytes(indata)
        if self._device_rate != self.sample_rate:
            pcm = resample_pcm16(pcm, self._device_rate, self.sample_rate)
        self.on_pcm(pcm)

    def close(self) -> None:
        self.arm(False)
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None


class AudioBridge:
    """Microphone only — no speakers, so Grok Bot is not echoed back into the mic."""

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop
        self.outgoing: asyncio.Queue[bytes] = asyncio.Queue(maxsize=80)
        self.mic = Microphone(on_pcm=self._from_portaudio)

    def start(self) -> None:
        self.mic.start()

    def _from_portaudio(self, pcm: bytes) -> None:
        def _put() -> None:
            try:
                self.outgoing.put_nowait(pcm)
            except asyncio.QueueFull:
                try:
                    self.outgoing.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    self.outgoing.put_nowait(pcm)
                except asyncio.QueueFull:
                    pass

        self.loop.call_soon_threadsafe(_put)

    def close(self) -> None:
        self.mic.close()
