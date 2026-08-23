from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable, Awaitable

from saltvoice_local.pcm import SAMPLE_RATE, rms_int16
from saltvoice_local.phrases import is_sleep_phrase, is_wake_phrase, normalize
from saltvoice_local.stt import transcribe_pcm

log = logging.getLogger("saltvoice_local")


class WakeWatcher:
    def __init__(
        self,
        language: str,
        on_wake: Callable[[], Awaitable[None]],
        on_sleep: Callable[[], Awaitable[None]],
        on_utterance: Callable[[str], Awaitable[None]] | None = None,
        on_text: Callable[[str], None] | None = None,
    ) -> None:
        self.language = language
        self.on_wake = on_wake
        self.on_sleep = on_sleep
        self.on_utterance = on_utterance
        self.on_text = on_text
        self.enabled = True
        self.listening = False
        self._chunks: list[bytes] = []
        self._speaking = False
        self._last_voice = 0.0
        self._busy = False
        self._mute_until = 0.0
        self._last_norm = ""
        self._last_norm_at = 0.0

    def reset(self) -> None:
        self._chunks.clear()
        self._speaking = False

    def enter_sleep(self) -> None:
        self.listening = False
        self.reset()
        self._mute_until = time.monotonic() + 2.0

    def enter_listen(self) -> None:
        self.listening = True
        self.reset()
        self._mute_until = 0.0

    def _max_seconds(self) -> float:
        return 18.0 if self.listening else 3.8

    def _voice_floor(self) -> float:
        return 0.016 if self.listening else 0.032

    async def feed(self, pcm: bytes) -> None:
        if not self.enabled:
            return
        now = time.monotonic()
        if now < self._mute_until:
            self.reset()
            return
        level = rms_int16(pcm)
        cap = self._max_seconds()
        if level > self._voice_floor():
            self._speaking = True
            self._last_voice = now
            self._chunks.append(pcm)
            max_bytes = int(SAMPLE_RATE * 2 * cap)
            total = sum(len(c) for c in self._chunks)
            if total > max_bytes:
                self._chunks.pop(0)
            return
        if not self._speaking:
            return
        if now - self._last_voice < 0.45:
            self._chunks.append(pcm)
            return
        if self._busy:
            return
        blob = b"".join(self._chunks)
        self.reset()
        duration = len(blob) / (SAMPLE_RATE * 2)
        min_dur = 0.35 if self.listening else 0.7
        if duration < min_dur or duration > cap + 0.4:
            return
        self._busy = True
        asyncio.create_task(self._handle_blob(blob, duration), name="stt-utt")

    async def _handle_blob(self, blob: bytes, duration: float) -> None:
        try:
            text = await asyncio.to_thread(transcribe_pcm, blob, SAMPLE_RATE, self.language)
            if not text:
                return
            key = normalize(text)
            now = time.monotonic()
            if key and key == self._last_norm and now - self._last_norm_at < 4:
                return
            self._last_norm = key
            self._last_norm_at = now
            wake = is_wake_phrase(text)
            sleep = is_sleep_phrase(text)
            if sleep:
                log.info("stt: %r sleep=True — stopping", text)
                self.enter_sleep()
                if self.on_text:
                    self.on_text(text)
                await self.on_sleep()
                return
            if wake:
                log.info("stt: %r wake=True — starting", text)
                self.enter_listen()
                if self.on_text:
                    self.on_text(text)
                await self.on_wake()
                return
            if self.listening and self.on_utterance:
                if self.on_text:
                    self.on_text(text)
                log.info("stt: %r listening=True dur=%.1fs", text, duration)
                await self.on_utterance(text)
        except Exception:
            log.exception("stt handler failed")
        finally:
            self._busy = False
