from __future__ import annotations

from typing import Callable

from saltvoice_local.config import Hotkeys


def _key_names(key: object) -> set[str]:
    from pynput import keyboard

    names: set[str] = set()
    mapping = {
        keyboard.Key.ctrl: "ctrl",
        keyboard.Key.ctrl_l: "ctrl",
        keyboard.Key.ctrl_r: "ctrl",
        keyboard.Key.alt: "alt",
        keyboard.Key.alt_l: "alt",
        keyboard.Key.alt_r: "alt",
        keyboard.Key.cmd: "cmd",
        keyboard.Key.cmd_l: "cmd",
        keyboard.Key.cmd_r: "cmd",
        keyboard.Key.shift: "shift",
        keyboard.Key.shift_l: "shift",
        keyboard.Key.shift_r: "shift",
    }
    if key in mapping:
        names.add(mapping[key])
    return names


class HotkeyListener:
    def __init__(
        self,
        keys: Hotkeys,
        *,
        on_toggle: Callable[[], None],
        on_cancel: Callable[[], None],
        on_overlay: Callable[[], None],
        on_clip: Callable[[], None] | None = None,
        on_hold_start: Callable[[], None] | None = None,
        on_hold_end: Callable[[], None] | None = None,
        listen_mode: str = "toggle",
    ) -> None:
        self.keys = keys
        self.on_toggle = on_toggle
        self.on_cancel = on_cancel
        self.on_overlay = on_overlay
        self.on_clip = on_clip
        self.on_hold_start = on_hold_start
        self.on_hold_end = on_hold_end
        self.listen_mode = listen_mode
        self._listener = None
        self._hotkeys = None
        self._holding = False
        self._down: set[str] = set()

    def start(self) -> None:
        from pynput import keyboard

        mapping = {
            self.keys.toggle_listen: self.on_toggle,
            self.keys.cancel: self.on_cancel,
            self.keys.toggle_overlay: self.on_overlay,
        }
        clip_combo = getattr(self.keys, "save_clip", "") or ""
        if clip_combo and self.on_clip is not None:
            mapping[clip_combo] = self.on_clip
        self._hotkeys = keyboard.GlobalHotKeys(mapping)
        self._hotkeys.start()

        if self.listen_mode == "hold" and self.on_hold_start and self.on_hold_end:
            combo = self._parse_hold(self.keys.hold_talk)

            def on_press(key: object) -> None:
                self._down |= _key_names(key)
                if combo and combo <= self._down and not self._holding:
                    self._holding = True
                    self.on_hold_start()

            def on_release(key: object) -> None:
                self._down -= _key_names(key)
                if self._holding and not (combo <= self._down):
                    self._holding = False
                    self.on_hold_end()

            self._listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            self._listener.start()

    def stop(self) -> None:
        try:
            if self._hotkeys:
                self._hotkeys.stop()
        except Exception:
            pass
        try:
            if self._listener:
                self._listener.stop()
        except Exception:
            pass

    @staticmethod
    def _parse_hold(spec: str) -> set[str]:
        parts = {p.strip("<> ").lower() for p in spec.split("+") if p.strip()}
        aliases = {
            "cmd": "cmd",
            "win": "cmd",
            "windows": "cmd",
            "super": "cmd",
            "ctrl": "ctrl",
            "control": "ctrl",
            "alt": "alt",
            "shift": "shift",
        }
        return {aliases.get(p, p) for p in parts}
