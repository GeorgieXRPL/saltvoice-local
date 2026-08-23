from __future__ import annotations

import tkinter as tk
import threading
from typing import Callable

from saltvoice_local.state import Hub, Phase

BG = "#071018"
PANEL = "#122433"
CARD = "#0c1c28"
GREEN = "#b4ff8c"
DIM = "#8fb3c4"
ERR = "#ff6b6b"
GOLD = "#f4c15d"
WHITE = "#f4fbff"
BTN = "#1b3a4e"
BTN_ON = "#1f5c3a"

PHASE_COLOR = {
    Phase.SLEEPING: DIM,
    Phase.LISTENING: GREEN,
    Phase.HEARING: GOLD,
    Phase.SPEAKING: GREEN,
    Phase.WORKING: GOLD,
    Phase.ERROR: ERR,
}


class Overlay:
    def __init__(
        self,
        hub: Hub,
        click_through: bool = False,
        *,
        on_wake: Callable[[], None] | None = None,
        on_standby: Callable[[], None] | None = None,
        on_teach: Callable[[str, str], str] | None = None,
        on_open_brain: Callable[[], None] | None = None,
    ) -> None:
        self.hub = hub
        self.click_through = click_through
        self.on_wake = on_wake
        self.on_standby = on_standby
        self.on_teach = on_teach
        self.on_open_brain = on_open_brain
        self._hidden = False
        self._last_heard = ""
        self.root = tk.Tk()
        self.root.title("Saltvoice Local")
        self.root.configure(bg=BG)
        self.root.attributes("-topmost", True)
        self.root.resizable(True, True)
        try:
            self.root.attributes("-alpha", 0.98)
        except tk.TclError:
            pass

        width, height = 720, 400
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        x = max(12, (screen_w - width) // 2)
        y = 12
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(560, 320)

        header = tk.Frame(self.root, bg=PANEL)
        header.pack(fill="x")
        top = tk.Frame(header, bg=PANEL)
        top.pack(fill="x", padx=16, pady=(12, 4))
        self.badge = tk.Label(
            top,
            text="STANDBY",
            fg=BG,
            bg=DIM,
            font=("Segoe UI", 11, "bold"),
            padx=12,
            pady=4,
        )
        self.badge.pack(side="left")
        self.phase_label = tk.Label(
            top,
            text="Saltvoice",
            fg=WHITE,
            bg=PANEL,
            font=("Segoe UI", 16, "bold"),
            anchor="w",
        )
        self.phase_label.pack(side="left", padx=(12, 0))
        self.target_label = tk.Label(
            top,
            text="→ Grok Bot",
            fg=GREEN,
            bg=PANEL,
            font=("Segoe UI", 10),
            anchor="e",
        )
        self.target_label.pack(side="right")

        self.hint = tk.Label(
            header,
            text="Wake with “Salt wake up”. Pause with “Salt go on standby”. Those stay in this window.",
            fg=DIM,
            bg=PANEL,
            font=("Segoe UI", 9),
            anchor="w",
            wraplength=680,
            justify="left",
        )
        self.hint.pack(fill="x", padx=16, pady=(0, 12))

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=(8, 0))

        self.you = self._card(body, "You said", "(waiting)")
        self.bot = self._card(body, "Sent to Grok Bot", "Nothing yet. Wake me, then speak a task.")

        teach = tk.LabelFrame(
            body,
            text="  Teach it your accent  ",
            fg=GOLD,
            bg=BG,
            font=("Segoe UI", 9, "bold"),
            padx=8,
            pady=8,
        )
        teach.pack(fill="x", pady=(8, 0))
        row = tk.Frame(teach, bg=BG)
        row.pack(fill="x")
        tk.Label(row, text="It heard", fg=DIM, bg=BG, font=("Segoe UI", 8)).grid(row=0, column=0, sticky="w")
        tk.Label(row, text="You meant", fg=DIM, bg=BG, font=("Segoe UI", 8)).grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.heard_var = tk.StringVar()
        self.meant_var = tk.StringVar()
        self.heard_entry = tk.Entry(row, textvariable=self.heard_var, bg=CARD, fg=WHITE, insertbackground=WHITE, relief="flat")
        self.meant_entry = tk.Entry(row, textvariable=self.meant_var, bg=CARD, fg=WHITE, insertbackground=WHITE, relief="flat")
        self.heard_entry.grid(row=1, column=0, sticky="ew", ipady=4, padx=(0, 8))
        self.meant_entry.grid(row=1, column=1, sticky="ew", ipady=4, padx=(0, 8))
        row.grid_columnconfigure(0, weight=1)
        row.grid_columnconfigure(1, weight=1)
        save = tk.Button(
            row,
            text="Save word",
            command=self._save_teach,
            bg=BTN_ON,
            fg=WHITE,
            activebackground="#2a7a4c",
            relief="flat",
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=4,
        )
        save.grid(row=1, column=2)
        self.teach_status = tk.Label(
            teach,
            text="If it keeps hearing “soat”, type soat → salt and Save. It remembers next time.",
            fg=DIM,
            bg=BG,
            font=("Segoe UI", 8),
            anchor="w",
            wraplength=660,
            justify="left",
        )
        self.teach_status.pack(fill="x", pady=(6, 0))

        actions = tk.Frame(self.root, bg=PANEL)
        actions.pack(fill="x", pady=(10, 0))
        inner = tk.Frame(actions, bg=PANEL)
        inner.pack(fill="x", padx=12, pady=8)
        self._action(inner, "Wake", self._do_wake, True).pack(side="left", padx=(0, 6))
        self._action(inner, "Standby", self._do_standby).pack(side="left", padx=6)
        self._action(inner, "Open memory", self._do_open_brain).pack(side="left", padx=6)
        tk.Label(
            inner,
            text="Ctrl+Alt+G listen   Ctrl+Alt+H hide   Ctrl+Alt+X quit",
            fg=DIM,
            bg=PANEL,
            font=("Segoe UI", 8),
        ).pack(side="right")

        self.root.protocol("WM_DELETE_WINDOW", self.hide)
        self.root.bind("<Configure>", self._on_resize)
        self.hub.subscribe(self._on_hub)
        self.root.after(100, self._raise)
        print(f"SALTVOICE LOCAL overlay at +{x}+{y} size {width}x{height}", flush=True)

    def _card(self, parent: tk.Frame, title: str, empty: str) -> tk.Label:
        wrap = tk.Frame(parent, bg=CARD)
        wrap.pack(fill="x", pady=(0, 8))
        tk.Label(wrap, text=title.upper(), fg=DIM, bg=CARD, font=("Segoe UI", 8, "bold"), anchor="w").pack(
            fill="x", padx=12, pady=(8, 0)
        )
        label = tk.Label(
            wrap,
            text=empty,
            fg=WHITE,
            bg=CARD,
            font=("Segoe UI", 12),
            wraplength=660,
            justify="left",
            anchor="nw",
        )
        label.pack(fill="x", padx=12, pady=(2, 10))
        return label

    def _action(self, parent: tk.Frame, text: str, cmd: Callable[[], None], accent: bool = False) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=cmd,
            bg=BTN_ON if accent else BTN,
            fg=WHITE,
            activebackground="#2a7a4c" if accent else "#244a63",
            relief="flat",
            font=("Segoe UI", 9),
            padx=10,
            pady=3,
        )

    def _on_resize(self, event: tk.Event) -> None:  # noqa: ANN001
        if event.widget is not self.root:
            return
        wrap = max(280, event.width - 56)
        for widget in (self.you, self.bot, self.hint, self.teach_status):
            widget.configure(wraplength=wrap)

    def _do_wake(self) -> None:
        if self.on_wake:
            self.on_wake()

    def _do_standby(self) -> None:
        if self.on_standby:
            self.on_standby()

    def _do_open_brain(self) -> None:
        if self.on_open_brain:
            self.on_open_brain()

    def _save_teach(self) -> None:
        heard = self.heard_var.get().strip() or self._last_heard
        meant = self.meant_var.get().strip()
        if not self.on_teach:
            self.teach_status.configure(text="Memory is not available in this session.")
            return
        message = self.on_teach(heard, meant)
        self.teach_status.configure(text=message, fg=GREEN if message.startswith("Saved") else GOLD)
        if message.startswith("Saved"):
            self.meant_var.set("")

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
            armed = bool(snapshot.get("armed"))
            color = PHASE_COLOR.get(snapshot["phase"], GREEN)
            label = "LISTENING" if armed else "STANDBY"
            self.badge.configure(text=label, bg=color, fg=BG if armed else WHITE)
            self.phase_label.configure(text="Saltvoice", fg=WHITE)
            target = str(snapshot.get("target") or "grok")
            self.target_label.configure(text="→ front window" if target == "here" else "→ Grok Bot")
            user = (snapshot.get("user_text") or "").strip()
            status = snapshot.get("status_line") or ""
            if user:
                self._last_heard = user
                if not self.heard_var.get().strip():
                    self.heard_var.set(user)
                self.you.configure(text=user[:400])
            elif not armed:
                self.you.configure(text=status[:400] or "Standby. Say Salt wake up when you want me to listen.")
            elif status:
                self.you.configure(text=status[:400])
            if not armed:
                self.bot.configure(text="Not sending to any app. Conversation in the room stays private.")
            elif status and ("HANDOFF" in status or "Sent" in status or "TASK" in status):
                self.bot.configure(text=status[:400])
            elif _event == "handoff":
                self.bot.configure(text=status[:400] or user)

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
