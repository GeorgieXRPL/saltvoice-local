from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
import threading
from pathlib import Path

from saltvoice_local.config import app_data_dir, describe_setup, load_settings
from saltvoice_local.process import acquire_single_instance, configure_stdio, safe_print
from saltvoice_local.state import Hub, Phase

log = logging.getLogger("saltvoice_local")


class _DropWhisperSpam(logging.Filter):
    _DROP = ("Processing audio with duration", "VAD filter removed")

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        return not any(s in msg for s in self._DROP)


def _setup_logging() -> None:
    folder = app_data_dir()
    folder.mkdir(parents=True, exist_ok=True)
    logfile = folder / "saltvoice-local.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(logfile, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    quiet = _DropWhisperSpam()
    logging.getLogger().addFilter(quiet)
    for name in (
        "faster_whisper",
        "faster_whisper.transcribe",
        "ctranslate2",
        "huggingface_hub",
        "huggingface_hub.utils",
        "httpx",
        "httpcore",
        "urllib3",
        "filelock",
    ):
        noisy = logging.getLogger(name)
        noisy.setLevel(logging.WARNING)
        noisy.addFilter(quiet)
    log.info("log file: %s", logfile)
    print(f"LOG FILE: {logfile}", flush=True)


def _windows_dpi() -> None:
    if os.name != "nt":
        return
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            import ctypes

            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _open_path(path: Path) -> None:
    if os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
        return
    if sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
        return
    subprocess.Popen(["xdg-open", str(path)])


def _banner() -> None:
    print("", flush=True)
    print("======== SALTVOICE LOCAL ========", flush=True)
    print("Offline. No API key. Whisper runs on this PC.", flush=True)
    print("Look for a window titled  Saltvoice Local  at the TOP of the screen.", flush=True)
    print("Start:  press Wake or Ctrl+Alt+G  (mic stays off until then)", flush=True)
    print("Pause:  Salt go to sleep / Salt go on standby / bye   (mic OFF, kitchen is not heard)", flush=True)
    print("Also:   Salt send to grok    or    Salt send here", flush=True)
    print("Or press Ctrl+Alt+G.  Ctrl+Alt+H shows the overlay.  Ctrl+Alt+X quits.", flush=True)
    print("Default: spoken tasks are pasted into Grok Bot.", flush=True)
    print("This black window is only logs. Do not close it.", flush=True)
    print("=================================", flush=True)
    print("", flush=True)


def _console_mirror(_event: str, snapshot: dict) -> None:
    if _event == "arm" and snapshot.get("armed"):
        safe_print("LISTENING. Speak a task. Sleep: Salt go to sleep", flush=True)
    if _event == "arm" and not snapshot.get("armed"):
        safe_print("SLEEP. Mic off. Press Wake or Ctrl+Alt+G.", flush=True)
    if _event == "target":
        safe_print(f"TARGET: {snapshot.get('status_line')}", flush=True)
    if _event == "wake-stt" and snapshot.get("user_text") and snapshot.get("armed"):
        safe_print(f"HEARD: {snapshot['user_text']}", flush=True)
    if _event in {"handoff"}:
        safe_print(f"TASK: {snapshot.get('status_line')}", flush=True)


def run(*, check: bool = False) -> int:
    configure_stdio()
    _setup_logging()
    if not check and not acquire_single_instance():
        safe_print("Saltvoice Local is already running. Close the other window first.")
        return 3
    settings = load_settings()
    for line in describe_setup(settings):
        print(line, flush=True)

    from saltvoice_local.stt import load_model

    print("Loading local Whisper model (first run downloads it, then it stays on disk)…", flush=True)
    try:
        load_model(
            settings.whisper_model,
            settings.device,
            settings.compute_type,
            download_root=settings.model_dir,
        )
    except Exception as exc:
        log.exception("whisper load failed")
        print(f"WHISPER FAILED: {exc}", flush=True)
        print("Install Visual C++ runtime on Windows if ctranslate2 cannot load.", flush=True)
        return 2
    if check:
        print("Whisper model loaded. Offline STT is ready.", flush=True)
        return 0

    from saltvoice_local.audio import AudioBridge
    from saltvoice_local.brain import Brain, brain_path
    from saltvoice_local.hotkeys import HotkeyListener
    from saltvoice_local.overlay import Overlay
    from saltvoice_local.session import VoiceSession
    from saltvoice_local.tray import start_tray
    from saltvoice_local.worker import ComputerWorker

    _windows_dpi()
    _banner()
    hub = Hub()
    hub.subscribe(_console_mirror)
    brain = Brain(brain_path())
    print(f"MEMORY FILE: {brain.path}", flush=True)

    overlay = None
    try:
        overlay = Overlay(
            hub,
            on_teach=lambda heard, meant: brain.add_correction(heard, meant),
            on_shortcut=brain.add_shortcut,
            on_command=brain.add_command,
            on_snapshot=brain.snapshot,
            on_open_brain=lambda: _open_path(brain.path),
        )
        from saltvoice_local.grok_bot import set_topmost_hook

        set_topmost_hook(overlay.set_topmost)
        print("OVERLAY ON: look for a window titled  Saltvoice Local  at the top of the screen.", flush=True)
        print("If you do not see it, press Ctrl+Alt+H or check the taskbar.", flush=True)
        if not settings.overlay.show_on_start:
            overlay.hide()
    except Exception as exc:
        log.exception("overlay failed")
        print(f"OVERLAY FAILED: {exc}", flush=True)

    loop_ready = threading.Event()
    loop_holder: dict[str, asyncio.AbstractEventLoop] = {}

    def loop_thread() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop_holder["loop"] = loop
        loop_ready.set()
        loop.run_forever()

    threading.Thread(target=loop_thread, name="asyncio", daemon=True).start()
    loop_ready.wait()
    loop = loop_holder["loop"]

    audio = AudioBridge(loop)
    try:
        audio.start()
        audio.mic.arm(False)
        print("Sleeping. Microphone is off until you press Wake or Ctrl+Alt+G.", flush=True)
    except Exception as exc:
        hub.emit("error", phase=Phase.ERROR, status_line=f"Microphone failed: {exc}")
        log.exception("audio start failed")
        print(f"MICROPHONE FAILED: {exc}", flush=True)

    session_holder: dict[str, VoiceSession] = {}
    ready = threading.Event()
    worker = ComputerWorker(
        window_titles=settings.grok_window_titles,
        prefer=settings.grok_prefer,
        cli=settings.grok_cli,
        workspace=settings.workspace_path,
        target=settings.handoff_target,
    )

    def _make_session() -> None:
        session_holder["s"] = VoiceSession(settings, hub, audio, worker, brain=brain)
        ready.set()

    loop.call_soon_threadsafe(_make_session)
    if not ready.wait(timeout=5):
        raise RuntimeError("Timed out starting the session loop")
    session = session_holder["s"]
    asyncio.run_coroutine_threadsafe(session.start_idle(), loop)

    def call(coro) -> None:
        asyncio.run_coroutine_threadsafe(coro, loop)

    if overlay is not None:
        overlay.on_wake = lambda: call(session.arm(True))
        overlay.on_standby = lambda: call(session.arm(False))
        overlay.on_teach = lambda heard, meant: brain.add_correction(heard, meant)
        overlay.on_shortcut = brain.add_shortcut
        overlay.on_command = brain.add_command
        overlay.on_snapshot = brain.snapshot
        overlay.on_open_brain = lambda: _open_path(brain.path)

        def _set_wait(seconds: float) -> str:
            message = brain.set_finish_wait(seconds)
            session.set_finish_wait(brain.finish_wait)
            return message

        def _set_floor(value: float) -> str:
            message = brain.set_voice_floor(value)
            session.set_voice_floor(brain.voice_floor)
            return message

        overlay.on_finish_wait = _set_wait
        overlay.on_voice_floor = _set_floor

    def toggle() -> None:
        call(session.toggle())

    def cancel() -> None:
        call(session.cancel())

    def toggle_overlay() -> None:
        if overlay is not None:
            overlay.root.after(0, overlay.toggle_visible)

    def show_settings() -> None:
        if overlay is not None:
            overlay.root.after(0, overlay.show_settings)

    async def shutdown() -> None:
        await session.close()

    def quit_app() -> None:
        try:
            future = asyncio.run_coroutine_threadsafe(shutdown(), loop)
            future.result(timeout=8)
        except Exception:
            log.exception("shutdown")
        try:
            loop.call_soon_threadsafe(loop.stop)
        except Exception:
            pass
        audio.close()
        if overlay is not None:
            overlay.shutdown()
        else:
            os._exit(0)

    start_tray(
        on_toggle=toggle,
        on_cancel=cancel,
        on_overlay=toggle_overlay,
        on_quit=quit_app,
        on_open_config=lambda: _open_path(settings.config_path),
        on_open_brain=lambda: _open_path(brain.path),
        on_overlay_settings=show_settings,
    )
    listener = HotkeyListener(
        settings.hotkeys,
        on_toggle=toggle,
        on_cancel=cancel,
        on_overlay=toggle_overlay,
        on_hold_start=lambda: call(session.arm(True)),
        on_hold_end=lambda: call(session.arm(False)),
        listen_mode=settings.listen_mode if settings.listen_mode == "hold" else "toggle",
    )
    try:
        listener.start()
    except Exception as exc:
        log.exception("hotkeys failed")
        hub.emit("error", status_line=f"Hotkeys failed ({exc}). Use the tray or overlay Wake.")

    hub.emit(
        "ready",
        phase=Phase.SLEEPING,
        status_line="Sleeping. Mic is off. Press Wake or Ctrl+Alt+G.",
        target=settings.handoff_target,
    )
    if overlay is not None:
        try:
            overlay.loop()
        finally:
            listener.stop()
            audio.close()
        return 0

    print("No overlay. Press Ctrl+C to quit.", flush=True)
    try:
        while True:
            threading.Event().wait(3600)
    except KeyboardInterrupt:
        quit_app()
    return 0
