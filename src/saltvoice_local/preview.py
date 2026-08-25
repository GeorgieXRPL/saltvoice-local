"""Open the overlay with sample copy. No mic. No Whisper."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from saltvoice_local.overlay import (
    APP_TITLE,
    BG,
    BTN,
    BTN_ON,
    CARD,
    DIM,
    GOLD,
    GREEN,
    LISTEN_H,
    LISTEN_HINT,
    LISTEN_W,
    PANEL,
    SETTINGS_H,
    SETTINGS_W,
    STANDBY_HINT,
    WHITE,
    Overlay,
)
from saltvoice_local.state import Hub, Phase

_FONT_REG = "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf"
_FONT_BOLD = "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf"


def _sample_snapshot() -> dict:
    return {
        "corrections": {"soat": "salt"},
        "shortcuts": {"the usual": "Open the Windows Downloads folder."},
        "commands": {},
        "path": r"%LOCALAPPDATA%\SaltvoiceLocal\brain.yaml",
        "finish_wait": 2.2,
        "voice_floor": 0.018,
    }


def _fonts():
    from PIL import ImageFont

    def load(path: str, size: int):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            return ImageFont.load_default()

    return {
        "title": load(_FONT_BOLD, 18),
        "badge": load(_FONT_BOLD, 13),
        "hint": load(_FONT_REG, 13),
        "btn": load(_FONT_BOLD, 13),
        "card_k": load(_FONT_BOLD, 11),
        "card": load(_FONT_REG, 15),
        "foot": load(_FONT_REG, 11),
        "small": load(_FONT_REG, 12),
        "gold": load(_FONT_BOLD, 13),
    }


def _wrap(draw, text: str, font, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=font) <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines or [""]


def paint_reference(path: Path, mode: str) -> None:
    """Draw a layout-matched PNG when the compositor blocks window capture."""
    from PIL import Image, ImageDraw

    listening = mode == "listen"
    settings = mode == "settings"
    w, h = (SETTINGS_W, SETTINGS_H) if settings else (LISTEN_W, LISTEN_H)
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    fonts = _fonts()
    accent = GREEN if listening or settings else DIM
    d.rectangle((0, 0, w, 3), fill=accent)
    d.rectangle((0, 3, w, 72), fill=PANEL)
    badge = "SETTINGS" if settings else ("LISTENING" if listening else "STANDBY")
    badge_bg = GOLD if settings else (GREEN if listening else DIM)
    badge_fg = BG if listening or settings else WHITE
    bx1, by1, bx2, by2 = 16, 16, 16 + 108, 40
    d.rounded_rectangle((bx1, by1, bx2, by2), radius=3, fill=badge_bg)
    d.text((bx1 + 10, by1 + 4), badge, fill=badge_fg, font=fonts["badge"])
    d.text((bx2 + 12, 16), APP_TITLE, fill=WHITE, font=fonts["title"])
    d.text((w - 210, 20), "→ Grok Bot", fill=GREEN, font=fonts["hint"])
    btn = "Listen" if settings else "Settings"
    btn_bg = BTN_ON if settings else GOLD
    btn_fg = WHITE if settings else BG
    d.rounded_rectangle((w - 108, 14, w - 16, 42), radius=3, fill=btn_bg)
    d.text((w - 92, 20), btn, fill=btn_fg, font=fonts["btn"])
    hint = "Teach words, shortcuts, and how long to wait before a paste." if settings else (LISTEN_HINT if listening else STANDBY_HINT)
    d.text((16, 48), hint[:88], fill=DIM, font=fonts["hint"])

    def card(x: int, y: int, cw: int, ch: int, title: str, body: str, body_fill=WHITE) -> None:
        d.rectangle((x, y, x + cw, y + ch), fill=CARD)
        d.rectangle((x, y, x + 3, y + ch), fill=GREEN)
        d.text((x + 14, y + 10), title.upper(), fill=DIM, font=fonts["card_k"])
        ty = y + 32
        for line in _wrap(d, body, fonts["card"], cw - 28)[:4]:
            d.text((x + 14, ty), line, fill=body_fill, font=fonts["card"])
            ty += 20

    if settings:
        d.text((16, 86), "SETTINGS — teach it how you talk. Grok Bot still does the work.", fill=GOLD, font=fonts["gold"])
        blocks = [
            (118, "1. Teach a word it keeps mishearing", "It heard                 You meant                      Save word"),
            (188, "2. Saved task (shortcut)", "You say                   Send this to Grok Bot         Save task"),
            (258, "3. Your own wake / standby phrase", "When you say              It should: wake / standby     Save phrase"),
            (328, "4. Wait until I finish speaking", "Seconds of silence before a paste. Raise if one request splits."),
            (418, "5. Mic sensitivity", "Raise if kitchen/TV is picked up. Standby still hears Salt wake up."),
        ]
        for y, title, body in blocks:
            d.rectangle((16, y, w - 16, y + 62), outline=GOLD)
            d.text((26, y + 6), title, fill=GOLD, font=fonts["small"])
            d.text((26, y + 30), body, fill=DIM, font=fonts["small"])
        d.rectangle((16, 492, w - 16, 600), fill=CARD)
        mem = "Words: soat → salt\nShortcuts: the usual → Open the Windows Downloads folder.\nNo extra wake/standby phrases yet.\nFile: %LOCALAPPDATA%\\SaltvoiceLocal\\brain.yaml"
        ty = 504
        for line in mem.split("\n"):
            d.text((28, ty), line, fill=WHITE, font=fonts["small"])
            ty += 20
        d.text((16, 612), "Tip: if it hears “soat”, save soat → salt.", fill=DIM, font=fonts["foot"])
    else:
        you = (
            "Open the Downloads folder and list the last three files."
            if listening
            else "Standby. Say Salt wake up."
        )
        bot = (
            "HANDOFF pasted into Grok Bot."
            if listening
            else "Not sending tasks. Say Salt wake up, or press Wake."
        )
        card(16, 84, 338, 150, "You said", you)
        card(366, 84, 338, 150, "Sent to Grok Bot", bot, WHITE if listening else DIM)

    d.rectangle((0, h - 48, w, h), fill=PANEL)
    d.rounded_rectangle((12, h - 36, 78, h - 12), radius=3, fill=BTN_ON)
    d.text((28, h - 32), "Wake", fill=WHITE, font=fonts["foot"])
    d.rounded_rectangle((86, h - 36, 168, h - 12), radius=3, fill=BTN)
    d.text((98, h - 32), "Standby", fill=WHITE, font=fonts["foot"])
    d.rounded_rectangle((176, h - 36, 292, h - 12), radius=3, fill=BTN)
    d.text((186, h - 32), "Open memory", fill=WHITE, font=fonts["foot"])
    d.text((w - 318, h - 30), "Ctrl+Alt+G listen   Ctrl+Alt+H hide   Ctrl+Alt+X quit", fill=DIM, font=fonts["foot"])
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    print(f"REF {path} {w}x{h}", flush=True)


def _grab(overlay: Overlay, path: Path) -> None:
    overlay.root.update_idletasks()
    overlay.root.update()
    x = overlay.root.winfo_rootx()
    y = overlay.root.winfo_rooty()
    w = overlay.root.winfo_width()
    h = overlay.root.winfo_height()
    try:
        from PIL import ImageGrab

        ImageGrab.grab(bbox=(x, y, x + w, y + h)).save(path)
        print(f"SHOT {path} {w}x{h}+{x}+{y}", flush=True)
    except OSError as exc:
        print(f"SHOT failed ({exc}); drawing layout reference instead.", flush=True)
        mode = "settings" if overlay._page == "settings" else ("listen" if overlay.hub.armed else "standby")
        paint_reference(path, mode)


def run(shots: Path | None = None, stay: bool = True) -> int:
    hub = Hub()
    overlay = Overlay(
        hub,
        on_snapshot=_sample_snapshot,
        on_wake=lambda: hub.emit(
            "status",
            armed=True,
            phase=Phase.LISTENING,
            status_line="Listening.",
            target="grok",
        ),
        on_standby=lambda: hub.emit(
            "status",
            armed=False,
            phase=Phase.SLEEPING,
            status_line="Standby. Say Salt wake up.",
            user_text="",
            target="grok",
        ),
    )
    hub.emit(
        "handoff",
        armed=True,
        phase=Phase.LISTENING,
        user_text="Open the Downloads folder and list the last three files.",
        status_line="HANDOFF pasted into Grok Bot.",
        target="grok",
    )
    overlay._drain_hub()
    overlay.root.update()

    if shots is not None:
        shots.mkdir(parents=True, exist_ok=True)
        _grab(overlay, shots / "listen.png")
        overlay.show_settings()
        overlay.root.update()
        overlay.root.after(80, lambda: None)
        overlay.root.update()
        _grab(overlay, shots / "settings.png")
        overlay._show_listen()
        hub.emit(
            "status",
            armed=False,
            phase=Phase.SLEEPING,
            user_text="",
            status_line="Standby. Say Salt wake up.",
            target="grok",
        )
        overlay._drain_hub()
        overlay.root.update()
        _grab(overlay, shots / "standby.png")
        if not stay:
            overlay.shutdown()
            return 0

    print("Preview overlay. Close the window or Ctrl+C to quit.", flush=True)
    overlay.loop()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Preview the Saltvoice Local overlay (no mic).")
    parser.add_argument("--shots", type=Path, help="Save listen/settings/standby PNGs and exit if --exit.")
    parser.add_argument("--refs", type=Path, help="Draw layout-matched PNGs without capturing the window.")
    parser.add_argument("--exit", action="store_true", help="Quit after saving --shots.")
    args = parser.parse_args(argv)
    if args.refs:
        args.refs.mkdir(parents=True, exist_ok=True)
        paint_reference(args.refs / "listen.png", "listen")
        paint_reference(args.refs / "settings.png", "settings")
        paint_reference(args.refs / "standby.png", "standby")
        return 0
    return run(shots=args.shots, stay=not args.exit)


if __name__ == "__main__":
    sys.exit(main())
