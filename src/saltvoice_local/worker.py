from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

from saltvoice_local.grok_bot import GrokBotConfig, send_instruction
from saltvoice_local.phrases import classify_utterance, is_filler_utterance, normalize

log = logging.getLogger("saltvoice_local")


class ComputerWorker:
    def __init__(self, window_titles: list[str], prefer: str, cli: str, workspace: Path, target: str = "grok") -> None:
        self.window_titles = window_titles
        self.prefer = prefer
        self.cli = cli
        self.workspace = workspace
        self.target = target
        self._last_sent = ""
        self._last_sent_at = 0.0

    async def run_computer_task(self, instruction: str) -> dict[str, Any]:
        cleaned = (instruction or "").strip()
        if classify_utterance(cleaned) != "task":
            log.info("blocked control phrase from handoff: %s", cleaned)
            return {"status": "ok", "method": "control-skipped"}
        if is_filler_utterance(cleaned):
            log.info("blocked filler from handoff: %s", cleaned)
            return {"status": "ok", "method": "filler-skipped"}
        key = normalize(cleaned)
        now = time.monotonic()
        if key and key == self._last_sent and now - self._last_sent_at < 8:
            return {"status": "ok", "method": "deduped"}
        cfg = GrokBotConfig(
            window_titles=self.window_titles,
            prefer=self.prefer,
            cli=self.cli,
            target=self.target,
        )
        try:
            result = await asyncio.to_thread(send_instruction, cleaned, self.workspace, cfg)
        except Exception as exc:
            log.exception("handoff crashed")
            return {"status": "error", "error": str(exc)}
        result.pop("process", None)
        if result.get("status") in {"ok", "started"}:
            self._last_sent = key
            self._last_sent_at = now
        return result
