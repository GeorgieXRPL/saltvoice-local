from __future__ import annotations

import tkinter as tk
import threading
from typing import Any, Callable

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
        on_shortcut: Callable[[str, str], str] | None = None,
        on_command: Callable[[str, str], str] | None = None,
        on_finish_wait: Callable[[float], str] | None = None,
        on_snapshot: Callable[[], dict[str, Any]] | None = None,
        on_open_brain: Callable[[], None] | None = None,
    ) -> None:
        self.hub = hub
        self.click_through = click_through
        self.on_wake = on_wake
        self.on_standby = on_standby
        self.on_teach = on_teach
        self.on_shortcut = on_shortcut
        self.on_command = on_command
        self.on_finish_wait = on_finish_wait
        self.on_snapshot = on_snapshot
        self.on_open_brain = on_open_brain
        self._hidden = False
        self._page = "listen"
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

        width, height = 760, 560
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        x = max(12, (screen_w - width) // 2)
        y = 12
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(640, 480)

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
        self._settings_btn = tk.Button(
            top,
            text="Settings",
            command=self.show_settings,
            bg=GOLD,
            fg=BG,
            activebackground="#ffd88a",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padx=14,
            pady=4,
        )
        self._settings_btn.pack(side="right")
        self.target_label = tk.Label(
            top,
            text="→ Grok Bot",
            fg=GREEN,
            bg=PANEL,
            font=("Segoe UI", 10),
            anchor="e",
        )
        self.target_label.pack(side="right", padx=(0, 12))

        self.hint = tk.Label(
            header,
            text="Wake: “Salt wake up”. Pause: “Salt go on standby”, “bye”, or “say bye”. Open Settings to teach words and saved phrases.",
            fg=DIM,
            bg=PANEL,
            font=("Segoe UI", 9),
            anchor="w",
            wraplength=720,
            justify="left",
        )
        self.hint.pack(fill="x", padx=16, pady=(0, 8))

        tabs = tk.Frame(header, bg=PANEL)
        tabs.pack(fill="x", padx=16, pady=(0, 10))
        self._tab_listen = self._tab_button(tabs, "Listen", lambda: self._show_page("listen"))
        self._tab_listen.pack(side="left", padx=(0, 6))
        self._tab_settings = self._tab_button(tabs, "Settings", self.show_settings, accent=True)
        self._tab_settings.pack(side="left")

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=(4, 0))

        self.listen_page = tk.Frame(body, bg=BG)
        self.settings_page = tk.Frame(body, bg=BG)
        self.you = self._card(self.listen_page, "You said", "(waiting)")
        self.bot = self._card(self.listen_page, "Sent to Grok Bot", "Nothing yet. Wake me, then speak a task.")
        self._build_settings(self.settings_page)
        self.listen_page.pack(fill="both", expand=True)

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
        self._paint_tabs()
        self._refresh_memory()
        self.root.after(100, self._raise)
        print(f"SALTVOICE LOCAL overlay at +{x}+{y} size {width}x{height}", flush=True)

    def _tab_button(self, parent: tk.Frame, text: str, cmd: Callable[[], None], accent: bool = False) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=cmd,
            bg=GOLD if accent else BTN,
            fg=BG if accent else WHITE,
            activebackground="#ffd88a" if accent else "#244a63",
            relief="flat",
            font=("Segoe UI", 10, "bold" if accent else "normal"),
            padx=16,
            pady=5,
        )

    def _build_settings(self, parent: tk.Frame) -> None:
        intro = tk.Label(
            parent,
            text="SETTINGS — teach it how you talk. Saved here, used the next time you speak. Grok Bot still does the work.",
            fg=GOLD,
            bg=BG,
            font=("Segoe UI", 10, "bold"),
            anchor="w",
            wraplength=700,
            justify="left",
        )
        intro.pack(fill="x", pady=(0, 8))
        self._settings_intro = intro

        teach = tk.LabelFrame(
            parent,
            text="  1. Teach a word it keeps mishearing  ",
            fg=GOLD,
            bg=BG,
            font=("Segoe UI", 9, "bold"),
            padx=8,
            pady=8,
        )
        teach.pack(fill="x", pady=(0, 8))
        row = tk.Frame(teach, bg=BG)
        row.pack(fill="x")
        tk.Label(row, text="It heard", fg=DIM, bg=BG, font=("Segoe UI", 8)).grid(row=0, column=0, sticky="w")
        tk.Label(row, text="You meant", fg=DIM, bg=BG, font=("Segoe UI", 8)).grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.heard_var = tk.StringVar()
        self.meant_var = tk.StringVar()
        self.heard_entry = tk.Entry(row, textvariable=self.heard_var, bg=CARD, fg=WHITE, insertbackground=WHITE, relief="flat")
        self.meant_entry = tk.Entry(row, textvariable=self.meant_var, bg=CARD, fg=WHITE, insertbackground=WHITE, relief="flat")
        self.heard_entry.grid(row=1, column=0, sticky="ew", ipady=5, padx=(0, 8))
        self.meant_entry.grid(row=1, column=1, sticky="ew", ipady=5, padx=(0, 8))
        row.grid_columnconfigure(0, weight=1)
        row.grid_columnconfigure(1, weight=1)
        tk.Button(
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
        ).grid(row=1, column=2)

        short = tk.LabelFrame(
            parent,
            text="  2. Saved task (shortcut)  ",
            fg=GOLD,
            bg=BG,
            font=("Segoe UI", 9, "bold"),
            padx=8,
            pady=8,
        )
        short.pack(fill="x", pady=(0, 8))
        srow = tk.Frame(short, bg=BG)
        srow.pack(fill="x")
        tk.Label(srow, text="You say", fg=DIM, bg=BG, font=("Segoe UI", 8)).grid(row=0, column=0, sticky="w")
        tk.Label(srow, text="Send this to Grok Bot", fg=DIM, bg=BG, font=("Segoe UI", 8)).grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.short_say = tk.StringVar()
        self.short_task = tk.StringVar()
        tk.Entry(srow, textvariable=self.short_say, bg=CARD, fg=WHITE, insertbackground=WHITE, relief="flat").grid(
            row=1, column=0, sticky="ew", ipady=5, padx=(0, 8)
        )
        tk.Entry(srow, textvariable=self.short_task, bg=CARD, fg=WHITE, insertbackground=WHITE, relief="flat").grid(
            row=1, column=1, sticky="ew", ipady=5, padx=(0, 8)
        )
        srow.grid_columnconfigure(0, weight=1)
        srow.grid_columnconfigure(1, weight=2)
        tk.Button(
            srow,
            text="Save task",
            command=self._save_shortcut,
            bg=BTN,
            fg=WHITE,
            relief="flat",
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=4,
        ).grid(row=1, column=2)

        cmdf = tk.LabelFrame(
            parent,
            text="  3. Your own wake / standby phrase  ",
            fg=GOLD,
            bg=BG,
            font=("Segoe UI", 9, "bold"),
            padx=8,
            pady=8,
        )
        cmdf.pack(fill="x", pady=(0, 8))
        crow = tk.Frame(cmdf, bg=BG)
        crow.pack(fill="x")
        tk.Label(crow, text="When you say", fg=DIM, bg=BG, font=("Segoe UI", 8)).grid(row=0, column=0, sticky="w")
        tk.Label(crow, text="It should", fg=DIM, bg=BG, font=("Segoe UI", 8)).grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.cmd_say = tk.StringVar()
        self.cmd_kind = tk.StringVar(value="standby")
        tk.Entry(crow, textvariable=self.cmd_say, bg=CARD, fg=WHITE, insertbackground=WHITE, relief="flat").grid(
            row=1, column=0, sticky="ew", ipady=5, padx=(0, 8)
        )
        kinds = tk.OptionMenu(crow, self.cmd_kind, "wake", "standby")
        kinds.configure(bg=BTN, fg=WHITE, highlightthickness=0, relief="flat")
        kinds.grid(row=1, column=1, sticky="ew", padx=(0, 8))
        crow.grid_columnconfigure(0, weight=2)
        crow.grid_columnconfigure(1, weight=1)
        tk.Button(
            crow,
            text="Save phrase",
            command=self._save_command,
            bg=BTN,
            fg=WHITE,
            relief="flat",
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=4,
        ).grid(row=1, column=2)

        waitf = tk.LabelFrame(
            parent,
            text="  4. Wait until I finish speaking  ",
            fg=GOLD,
            bg=BG,
            font=("Segoe UI", 9, "bold"),
            padx=8,
            pady=8,
        )
        waitf.pack(fill="x", pady=(0, 8))
        self.wait_var = tk.DoubleVar(value=2.2)
        tk.Label(
            waitf,
            text="Seconds of silence before a task is pasted into Grok Bot. Raise this if one request is split into several pastes.",
            fg=DIM,
            bg=BG,
            font=("Segoe UI", 8),
            anchor="w",
            wraplength=680,
            justify="left",
        ).pack(fill="x")
        self._wait_hint = waitf.winfo_children()[-1]
        scale = tk.Scale(
            waitf,
            from_=0.8,
            to=4.0,
            resolution=0.1,
            orient="horizontal",
            variable=self.wait_var,
            bg=BG,
            fg=WHITE,
            troughcolor=CARD,
            highlightthickness=0,
            length=420,
        )
        scale.pack(fill="x", pady=(4, 0))
        scale.bind("<ButtonRelease-1>", self._save_wait)

        self.memory_label = tk.Label(
            parent,
            text="No saved words yet.",
            fg=WHITE,
            bg=CARD,
            font=("Segoe UI", 9),
            anchor="nw",
            justify="left",
            wraplength=700,
            padx=10,
            pady=10,
        )
        self.memory_label.pack(fill="both", expand=True)

        self.settings_status = tk.Label(
            parent,
            text="Tip: if it hears “soat”, save soat → salt. If “bye” should pause, it already does — or add your own phrase above.",
            fg=DIM,
            bg=BG,
            font=("Segoe UI", 8),
            anchor="w",
            wraplength=700,
            justify="left",
        )
        self.settings_status.pack(fill="x", pady=(8, 0))

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
            wraplength=700,
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

    def _show_page(self, name: str) -> None:
        self._page = name
        self.listen_page.pack_forget()
        self.settings_page.pack_forget()
        if name == "settings":
            self.settings_page.pack(fill="both", expand=True)
            self._refresh_memory()
        else:
            self.listen_page.pack(fill="both", expand=True)
        self._paint_tabs()

    def show_settings(self) -> None:
        self.show()
        self._show_page("settings")

    def _paint_tabs(self) -> None:
        listen_on = self._page == "listen"
        self._tab_listen.configure(bg=BTN_ON if listen_on else BTN, fg=WHITE)
        self._tab_settings.configure(bg=GOLD if not listen_on else BTN, fg=BG if not listen_on else WHITE)

    def _on_resize(self, event: tk.Event) -> None:  # noqa: ANN001
        if event.widget is not self.root:
            return
        wrap = max(280, event.width - 56)
        widgets = [self.you, self.bot, self.hint, self.settings_status, self.memory_label, self._settings_intro]
        if hasattr(self, "_wait_hint"):
            widgets.append(self._wait_hint)
        for widget in widgets:
            try:
                widget.configure(wraplength=wrap)
            except tk.TclError:
                pass

    def _do_wake(self) -> None:
        if self.on_wake:
            self.on_wake()
        self._show_page("listen")

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
            self.settings_status.configure(text="Memory is not available in this session.")
            return
        message = self.on_teach(heard, meant)
        self.settings_status.configure(text=message, fg=GREEN if message.startswith("Saved") else GOLD)
        if message.startswith("Saved"):
            self.meant_var.set("")
        self._refresh_memory()

    def _save_shortcut(self) -> None:
        if not self.on_shortcut:
            self.settings_status.configure(text="Shortcuts are not available in this session.")
            return
        message = self.on_shortcut(self.short_say.get(), self.short_task.get())
        self.settings_status.configure(text=message, fg=GREEN if message.startswith("Saved") else GOLD)
        if message.startswith("Saved"):
            self.short_say.set("")
            self.short_task.set("")
        self._refresh_memory()

    def _save_command(self) -> None:
        if not self.on_command:
            self.settings_status.configure(text="Custom phrases are not available in this session.")
            return
        message = self.on_command(self.cmd_say.get(), self.cmd_kind.get())
        self.settings_status.configure(text=message, fg=GREEN if message.startswith("Saved") else GOLD)
        if message.startswith("Saved"):
            self.cmd_say.set("")
        self._refresh_memory()

    def _save_wait(self, _event: tk.Event | None = None) -> None:  # noqa: ANN001
        if not self.on_finish_wait:
            return
        message = self.on_finish_wait(float(self.wait_var.get()))
        self.settings_status.configure(text=message, fg=GREEN)
        self._refresh_memory()

    def _refresh_memory(self) -> None:
        if not self.on_snapshot:
            return
        snap = self.on_snapshot() or {}
        wait = snap.get("finish_wait")
        if wait is not None:
            try:
                self.wait_var.set(float(wait))
            except (TypeError, ValueError):
                pass
        lines = []
        corrections = snap.get("corrections") or {}
        shortcuts = snap.get("shortcuts") or {}
        commands = snap.get("commands") or {}
        path = snap.get("path") or ""
        if corrections:
            lines.append("Words: " + ", ".join(f"{k} → {v}" for k, v in corrections.items()))
        else:
            lines.append("No saved words yet. Example: soat → salt")
        if shortcuts:
            lines.append("Shortcuts: " + ", ".join(f"{k} → {v}" for k, v in shortcuts.items()))
        else:
            lines.append("No shortcuts yet. Example: the usual → Open the Windows Downloads folder.")
        if commands:
            lines.append("Phrases: " + ", ".join(f"{k} = {v}" for k, v in commands.items()))
        else:
            lines.append("No extra wake/standby phrases yet.")
        if path:
            lines.append(f"File: {path}")
        self.memory_label.configure(text="\n".join(lines))

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
