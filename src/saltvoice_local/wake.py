from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable

from saltvoice_local.pcm import SAMPLE_RATE, rms_int16
from saltvoice_local.phrases import (
    classify_utterance,
    is_filler_utterance,
    is_incomplete_utterance,
    is_noise_utterance,
    normalize,
    polish_task,
    remainder_after_wake,
)
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
        on_target: Callable[[str], Awaitable[None]] | None = None,
        on_clip: Callable[[], Awaitable[None]] | None = None,
        finish_wait: float = 2.2,
        voice_floor: float = 0.018,
    ) -> None:
        self.language = language
        self.on_wake = on_wake
        self.on_sleep = on_sleep
        self.on_utterance = on_utterance
        self.on_text = on_text
        self.on_target = on_target
        self.on_clip = on_clip
        self.finish_wait = max(0.8, min(4.0, float(finish_wait or 2.2)))
        self.voice_floor = max(0.008, min(0.04, float(voice_floor or 0.018)))
        self.enabled = False
        self.listening = False
        self._chunks: list[bytes] = []
        self._speaking = False
        self._last_voice = 0.0
        self._busy = False
        self._mute_until = 0.0
        self._last_norm = ""
        self._last_norm_at = 0.0
        self._last_standby_note = 0.0
        self._pending = ""
        self._pending_at = 0.0
        self._draft = ""
        self._draft_started = 0.0
        self._flush_task: asyncio.Task | None = None

    def reset(self) -> None:
        self._chunks.clear()
        self._speaking = False

    def enter_sleep(self) -> None:
        self.listening = False
        self.enabled = True
        self.reset()
        self._pending = ""
        self._abandon_draft()
        self._mute_until = time.monotonic() + 1.2
        log.info("standby — wake word only; say Salt wake up")

    def enter_listen(self) -> None:
        self.listening = True
        self.enabled = True
        self.reset()
        self._pending = ""
        self._abandon_draft()
        self._mute_until = 0.0

    def _max_seconds(self) -> float:
        return 5.0 if not self.listening else 24.0

    def _voice_floor(self) -> float:
        return self.voice_floor

    def _hangover(self) -> float:
        return 0.7 if not self.listening else 1.55

    def _cancel_flush(self) -> None:
        task = self._flush_task
        self._flush_task = None
        if task and not task.done():
            task.cancel()

    def _abandon_draft(self) -> None:
        self._cancel_flush()
        self._draft = ""
        self._draft_started = 0.0

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
        if now - self._last_voice < self._hangover():
            self._chunks.append(pcm)
            return
        if self._busy:
            return
        blob = b"".join(self._chunks)
        self.reset()
        duration = len(blob) / (SAMPLE_RATE * 2)
        min_dur = 0.35
        if duration < min_dur or duration > cap + 0.4:
            return
        need = max(0.008, self.voice_floor * 0.85)
        if rms_int16(blob) < need:
            return
        self._busy = True
        asyncio.create_task(self._handle_blob(blob, duration, need), name="stt-utt")

    async def _handle_blob(self, blob: bytes, duration: float, min_rms: float) -> None:
        try:
            if not self.enabled:
                return
            text = await asyncio.to_thread(transcribe_pcm, blob, SAMPLE_RATE, self.language, min_rms)
            if not text:
                return
            if not self.enabled:
                return
            now = time.monotonic()
            if (not self.listening) and self._pending and now - self._pending_at < 3.2:
                text = f"{self._pending} {text}".strip()
                log.info("stt joined fragment → %r", text)
                self._pending = ""
            kind = classify_utterance(text)
            if kind == "clip":
                log.info("stt: %r clip — not sending to any app", text)
                self._abandon_draft()
                if self.on_clip:
                    await self.on_clip()
                return
            if not self.listening:
                if kind == "wake":
                    log.info("stt: %r wake — listening", text)
                    self._abandon_draft()
                    self.enter_listen()
                    await self.on_wake()
                    rest = remainder_after_wake(text)
                    if rest and self.on_utterance:
                        log.info("stt: %r wake+task", rest)
                        await self.on_utterance(rest)
                    return
                if is_incomplete_utterance(text):
                    self._pending = text
                    self._pending_at = now
                    log.info("stt: %r holding for Salt wake up", text)
                    return
                if now - self._last_standby_note >= 20:
                    log.info("standby — say Salt wake up (not sending %r)", text)
                    self._last_standby_note = now
                return
            if kind == "standby":
                log.info("stt: %r standby — not sending to any app", text)
                self._abandon_draft()
                self.enter_sleep()
                await self.on_sleep()
                return
            if kind == "wake":
                log.info("stt: %r wake — listening", text)
                self._abandon_draft()
                self.enter_listen()
                await self.on_wake()
                rest = remainder_after_wake(text)
                if rest and self.on_utterance:
                    log.info("stt: %r wake+task", rest)
                    await self.on_utterance(rest)
                return
            if kind == "target_grok":
                log.info("stt: %r → send to Grok Bot", text)
                self._abandon_draft()
                if self.on_target:
                    await self.on_target("grok")
                return
            if kind == "target_here":
                log.info("stt: %r → send to front window", text)
                self._abandon_draft()
                if self.on_target:
                    await self.on_target("here")
                return
            if is_filler_utterance(text) or is_noise_utterance(text) or is_incomplete_utterance(text):
                if self._draft:
                    log.info("stt: %r skipped junk; still waiting for you to finish", text)
                    await self._bump_flush()
                else:
                    log.info("stt: %r filler — not pasted", text)
                return
            key = normalize(text)
            if key and key == self._last_norm and now - self._last_norm_at < 4:
                return
            self._last_norm = key
            self._last_norm_at = now
            await self._queue_task(text)
        except Exception:
            log.exception("stt handler failed")
        finally:
            self._busy = False

    async def _queue_task(self, text: str) -> None:
        now = time.monotonic()
        wait = max(0.8, min(4.0, float(self.finish_wait or 2.2)))
        if self._draft and now - self._draft_started > 18:
            await self._flush_draft()
        if self._draft:
            self._draft = f"{self._draft} {text}".strip()
        else:
            self._draft = text
            self._draft_started = now
        if self.on_text:
            self.on_text(self._draft)
        log.info("stt: %r holding until you finish (draft=%r wait=%.1fs)", text, self._draft, wait)
        self._cancel_flush()

        async def wait_and_flush() -> None:
            try:
                await asyncio.sleep(wait)
                await self._flush_draft()
            except asyncio.CancelledError:
                return

        self._flush_task = asyncio.create_task(wait_and_flush(), name="stt-flush")

    async def _bump_flush(self) -> None:
        if not self._draft:
            return
        log.info("stt: still holding draft %r", self._draft)
        self._cancel_flush()
        wait = max(0.8, min(4.0, float(self.finish_wait or 2.2)))

        async def wait_and_flush() -> None:
            try:
                await asyncio.sleep(wait)
                await self._flush_draft()
            except asyncio.CancelledError:
                return

        self._flush_task = asyncio.create_task(wait_and_flush(), name="stt-flush")

    async def _flush_draft(self) -> None:
        text = self._draft.strip()
        self._draft = ""
        self._draft_started = 0.0
        self._flush_task = None
        if not text:
            return
        kind = classify_utterance(text)
        if kind == "clip":
            log.info("stt: %r clip from draft — not sending to any app", text)
            if self.on_clip:
                await self.on_clip()
            return
        if kind != "task":
            log.info("stt: %r dropped from draft (control)", text)
            return
        if is_filler_utterance(text) or is_noise_utterance(text) or is_incomplete_utterance(text):
            log.info("stt: %r dropped (too short / noise)", text)
            return
        text = polish_task(text)
        if self.on_text:
            self.on_text(text)
        log.info("stt: %r listening=True (finished speaking)", text)
        if self.on_utterance:
            await self.on_utterance(text)
