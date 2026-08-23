from __future__ import annotations

import asyncio
import logging
import time

from saltvoice_local.audio import AudioBridge
from saltvoice_local.config import Settings
from saltvoice_local.phrases import is_sleep_phrase, is_wake_phrase, normalize
from saltvoice_local.state import Hub, Phase
from saltvoice_local.wake import WakeWatcher
from saltvoice_local.worker import ComputerWorker

log = logging.getLogger("saltvoice_local")


class VoiceSession:
    """Local mic → Whisper → Grok Bot paste. No cloud APIs."""

    def __init__(
        self,
        settings: Settings,
        hub: Hub,
        audio: AudioBridge | None,
        worker: ComputerWorker,
    ) -> None:
        self.settings = settings
        self.hub = hub
        self.audio = audio
        self.worker = worker
        self._armed = False
        self._stop: asyncio.Event | None = None
        self._pump_task: asyncio.Task | None = None
        self._sleep_task: asyncio.Task | None = None
        self.wake: WakeWatcher | None = None
        self._last_user_norm = ""
        self._last_user_at = 0.0
        self._last_user_activity = time.monotonic()

    @property
    def armed(self) -> bool:
        return self._armed

    def _ensure(self) -> None:
        if self._stop is None:
            self._stop = asyncio.Event()

    async def arm(self, value: bool) -> None:
        self._armed = value
        if self.wake:
            if value:
                self.wake.enter_listen()
            else:
                self.wake.enter_sleep()
        if value:
            self._last_user_activity = time.monotonic()
            log.info("armed — local Whisper will paste into Grok Bot")
            self.hub.emit(
                "arm",
                phase=Phase.LISTENING,
                armed=True,
                status_line="Listening. Speak your request. Say Salt stop voice over to stop.",
            )
        else:
            log.info("sleeping — waiting for Salt open voice over")
            self.hub.emit(
                "arm",
                phase=Phase.SLEEPING,
                armed=False,
                user_text="",
                assistant_text="",
                status_line="Sleeping. Waiting for Salt open voice over.",
            )

    async def start_idle(self) -> None:
        self._ensure()
        if self.audio and self._pump_task is None:
            self._pump_task = asyncio.create_task(self._mic_pump(), name="mic-pump")
        if self.wake is None:
            self.wake = WakeWatcher(
                language=self.settings.language,
                on_wake=lambda: self.arm(True),
                on_sleep=lambda: self.arm(False),
                on_utterance=self._on_user_final,
                on_text=lambda text: self.hub.emit("wake-stt", user_text=text, status_line=f"Heard: {text}"),
            )
        if self._sleep_task is None:
            self._sleep_task = asyncio.create_task(self._auto_sleep(), name="auto-sleep")

    async def toggle(self) -> None:
        await self.arm(not self._armed)

    async def cancel(self) -> None:
        self.hub.emit("cancel", phase=Phase.LISTENING if self._armed else Phase.SLEEPING, status_line="Stopped.")

    async def _mic_pump(self) -> None:
        assert self.audio is not None
        assert self._stop is not None
        while not self._stop.is_set():
            try:
                pcm = await asyncio.wait_for(self.audio.outgoing.get(), timeout=0.25)
            except asyncio.TimeoutError:
                continue
            if self.wake:
                await self.wake.feed(pcm)

    async def _auto_sleep(self) -> None:
        limit = max(1.0, self.settings.auto_sleep_minutes) * 60
        assert self._stop is not None
        while not self._stop.is_set():
            await asyncio.sleep(5)
            if not self._armed:
                continue
            if time.monotonic() - self._last_user_activity >= limit:
                await self.arm(False)

    async def _on_user_final(self, text: str) -> None:
        now = time.monotonic()
        key = normalize(text)
        if key == self._last_user_norm and now - self._last_user_at < 5:
            return
        self._last_user_norm = key
        self._last_user_at = now
        self._last_user_activity = now
        print(f"YOU: {text}", flush=True)
        log.info("YOU: %s", text)
        if is_sleep_phrase(text) and self._armed:
            await self.arm(False)
            return
        if is_wake_phrase(text):
            if not self._armed:
                await self.arm(True)
            return
        self.hub.emit("user", phase=Phase.HEARING, user_text=text, status_line=f"You: {text}"[-180:])
        if not self._armed:
            return
        result = await self.worker.run_computer_task(text)
        method = result.get("method") or result.get("status")
        err = result.get("error")
        line = f"HANDOFF {method}: {text}"
        if err:
            line = f"HANDOFF FAILED: {err}"
        print(line, flush=True)
        log.info(line)
        self.hub.emit("handoff", phase=Phase.WORKING, status_line=line[:180])

    async def close(self) -> None:
        self._ensure()
        self._stop.set()
        self._armed = False
        if self.audio:
            self.audio.mic.arm(False)
        for task in (self._pump_task, self._sleep_task):
            if task:
                task.cancel()
