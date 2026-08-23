from __future__ import annotations

import tkinter as tk
import threading
from typing import Callable

from saltvoice_local.state import Hub, Phase

BG = "#061018"
PANEL = "#102132"
GREEN = "#b4ff8c"
DIM = "#8fb3c4"
ERR = "#ff6b6b"
GOLD = "#f4c15d"
WHITE = "#f4fbff"

PHASE_COLOR = {
    Phase.SLEEPING: DIM,
    Phase.LISTENING: GREEN,
    Phase.HEARING: GOLD,
    Phase.SPEAKING: GREEN,
    Phase.WORKING: GOLD,
    Phase.ERROR: ERR,
}


class Overlay:
    def __init__(self, hub: Hub, click_through: bool = False) -> None:
        self.hub = hub
        self.click_through = click_through
        self._hidden = False
        self.root = tk.Tk()
        self.root.title("Saltvoice Local")
        self.root.configure(bg=BG)
        self.root.attributes("-topmost", True)
        self.root.resizable(True, True)
        try:
            self.root.attributes("-alpha", 0.98)
        except tk.TclError:
            pass

        width, height = 640, 210
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        x = max(12, (screen_w - width) // 2)
        y = 16
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(480, 160)

        header = tk.Frame(self.root, bg=PANEL)
        header.pack(fill="x")
        self.phase_label = tk.Label(
            header,
            text="SALTVOICE LOCAL  ·  STANDBY",
            fg=GREEN,
            bg=PANEL,
            font=("Segoe UI", 12, "bold"),
            anchor="w",
        )
        self.phase_label.pack(fill="x", padx=14, pady=(10, 0))
        self.hint = tk.Label(
            header,
            text='Wake: “Salt wake up”  ·  Standby: “Salt go on standby”  ·  never pasted into Grok Bot',
            fg=DIM,
            bg=PANEL,
            font=("Segoe UI", 8),
            anchor="w",
        )
        self.hint.pack(fill="x", padx=14, pady=(2, 8))

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        self.you = tk.Label(
            body,
            text="You: (waiting)",
            fg=WHITE,
            bg=BG,
            font=("Segoe UI", 11),
            wraplength=600,
            justify="left",
            anchor="nw",
        )
        self.you.pack(fill="x", pady=(0, 6))
        self.bot = tk.Label(
            body,
            text="Grok Bot: (waiting)",
            fg=GREEN,
            bg=BG,
            font=("Segoe UI", 11),
            wraplength=600,
            justify="left",
            anchor="nw",
        )
        self.bot.pack(fill="x")

        self.root.protocol("WM_DELETE_WINDOW", self.hide)
        self.hub.subscribe(self._on_hub)
        self.root.after(100, self._raise)
        print(f"SALTVOICE LOCAL overlay at +{x}+{y} size {width}x{height}", flush=True)

    def _raise(self) -> None:
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.attributes("-topmost", True)
            self.root.update()
        except tk.TclError:
            pass

    def _on_hub(self, _event: str, snapshot: dict) -> None:
        def apply() -> None:
            phase: Phase = snapshot["phase"]
            color = PHASE_COLOR.get(phase, GREEN)
            label = "LISTENING" if snapshot.get("armed") else "STANDBY"
            self.phase_label.configure(
                text=f"SALTVOICE LOCAL  ·  {label}",
                fg=color,
            )
            user = snapshot.get("user_text") or ""
            status = snapshot.get("status_line") or ""
            if not snapshot.get("armed") and phase is Phase.SLEEPING:
                self.you.configure(text=status[:400] or "Standby. Say Salt wake up to listen.")
                self.bot.configure(text="Not sending to any app until you say Salt wake up.")
                return
            if user:
                self.you.configure(text=f"You: {user[:400]}")
            elif status:
                self.you.configure(text=status[:400])
            if status and (snapshot.get("armed") or user):
                self.bot.configure(text=status[:400])

        try:
            self.root.after(0, apply)
        except tk.TclError:
            pass

    def set_topmost(self, value: bool) -> None:
        done = threading.Event()

        def apply() -> None:
            try:
                if value:
                    self.root.attributes("-topmost", True)
                    self.root.lift()
                else:
                    self.root.attributes("-topmost", False)
                    self.root.lower()
            except tk.TclError:
                pass
            finally:
                done.set()

        try:
            self.root.after(0, apply)
            done.wait(timeout=1.0)
        except tk.TclError:
            pass

    def toggle_visible(self) -> None:
        if self._hidden:
            self.show()
        else:
            self.hide()

    def hide(self) -> None:
        self._hidden = True
        self.root.withdraw()
        print("Overlay hidden. Tray → Show overlay, or Ctrl+Alt+H.", flush=True)

    def show(self) -> None:
        self._hidden = False
        self._raise()

    def on_quit(self, fn: Callable[[], None]) -> None:
        self.root.protocol("WM_DELETE_WINDOW", lambda: fn())

    def loop(self) -> None:
        self.root.mainloop()

    def shutdown(self) -> None:
        try:
            self.root.quit()
            self.root.destroy()
        except tk.TclError:
            pass
