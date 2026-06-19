# -*- coding: utf-8 -*-
"""System tray icon for background operation."""

from __future__ import annotations

import queue
import threading
from pathlib import Path
from typing import Callable, TYPE_CHECKING

from pig_pointer.constants import APP_TITLE

if TYPE_CHECKING:
    import tkinter as tk

try:
    from PIL import Image, ImageDraw
except Exception as exc:
    import tkinter.messagebox

    tkinter.messagebox.showerror("缺少依赖", f"需要安装 Pillow：\n{exc}")
    raise

try:
    import pystray
except Exception:
    pystray = None


class SystemTrayIcon:
    def __init__(
        self,
        root: tk.Tk,
        icon_path: Path,
        on_show: Callable[[], None],
        on_toggle: Callable[[], None],
        on_exit: Callable[[], None],
        is_running: Callable[[], bool],
    ) -> None:
        self.root = root
        self.icon_path = icon_path
        self.on_show = on_show
        self.on_toggle = on_toggle
        self.on_exit = on_exit
        self.is_running = is_running
        self.pending_actions: queue.SimpleQueue[Callable[[], None]] = queue.SimpleQueue()
        self.icon: pystray.Icon | None = None
        self.thread: threading.Thread | None = None
        self.visible = False

    def show(self) -> None:
        if self.visible or pystray is None:
            return
        image = self._load_image()
        menu = pystray.Menu(
            pystray.MenuItem("打开面板", self._on_show, default=True),
            pystray.MenuItem(lambda _item: "关闭小猪" if self.is_running() else "启动小猪", self._on_toggle),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出软件", self._on_exit),
        )
        self.icon = pystray.Icon("PigPointer", image, APP_TITLE, menu)
        self.thread = threading.Thread(target=self.icon.run, name="PigPointerTray", daemon=True)
        self.thread.start()
        self.visible = True

    def hide(self) -> None:
        if not self.visible:
            return
        if self.icon is not None:
            try:
                self.icon.stop()
            except Exception:
                pass
            self.icon = None
        self.visible = False

    def destroy(self) -> None:
        self.hide()

    def process_pending_actions(self) -> None:
        while True:
            try:
                action = self.pending_actions.get_nowait()
            except queue.Empty:
                break
            action()

    def _load_image(self) -> Image.Image:
        if self.icon_path.exists():
            try:
                source = Image.open(self.icon_path)
                if source.format == "ICO" and (64, 64) in source.ico.sizes():
                    return source.ico.getimage((64, 64)).convert("RGBA")
                return source.convert("RGBA")
            except Exception:
                pass
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse((8, 12, 56, 52), fill=(255, 198, 166, 255), outline=(209, 89, 106, 255), width=2)
        draw.ellipse((14, 28, 32, 42), fill=(255, 116, 139, 255))
        draw.ellipse((19, 32, 23, 39), fill=(28, 28, 28, 255))
        draw.ellipse((27, 32, 31, 39), fill=(28, 28, 28, 255))
        return image

    def _on_show(self, _icon=None, _item=None) -> None:
        self.pending_actions.put(self.on_show)

    def _on_toggle(self, _icon=None, _item=None) -> None:
        self.pending_actions.put(self.on_toggle)

    def _on_exit(self, _icon=None, _item=None) -> None:
        self.pending_actions.put(self.on_exit)
