from __future__ import annotations

import threading
from typing import Callable

from PIL import Image, ImageDraw
import pystray


def _icon_image() -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((4, 4, 60, 60), fill=(7, 16, 24, 255), outline=(180, 255, 140, 255), width=3)
    draw.ellipse((22, 22, 42, 42), fill=(180, 255, 140, 255))
    return img


def start_tray(
    *,
    on_toggle: Callable[[], None],
    on_cancel: Callable[[], None],
    on_overlay: Callable[[], None],
    on_quit: Callable[[], None],
    on_open_config: Callable[[], None],
    on_open_brain: Callable[[], None] | None = None,
    on_overlay_settings: Callable[[], None] | None = None,
) -> pystray.Icon:
    items = [
        pystray.MenuItem("Talk / stop (Ctrl+Alt+G)", lambda: on_toggle()),
        pystray.MenuItem("Cancel (Ctrl+Alt+X)", lambda: on_cancel()),
        pystray.MenuItem("Show Saltvoice Local overlay", lambda: on_overlay()),
    ]
    if on_overlay_settings:
        items.append(pystray.MenuItem("Open Settings", lambda: on_overlay_settings()))
    items.append(pystray.MenuItem("Open config", lambda: on_open_config()))
    if on_open_brain:
        items.append(pystray.MenuItem("Open memory (brain.yaml)", lambda: on_open_brain()))
    items.append(pystray.MenuItem("Quit", lambda: on_quit()))
    menu = pystray.Menu(*items)
    icon = pystray.Icon("saltvoice-local", _icon_image(), "Saltvoice Local", menu)
    thread = threading.Thread(target=icon.run, name="tray", daemon=True)
    thread.start()
    return icon
