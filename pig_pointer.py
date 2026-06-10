# -*- coding: utf-8 -*-
from __future__ import annotations

import atexit
import ctypes
import json
import math
import os
import queue
import random
import shutil
import sys
import threading
import time
import tkinter as tk
import uuid
from collections import OrderedDict
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk
from typing import Callable

try:
    import numpy as np
except Exception:  # pragma: no cover - NumPy is an optional speed path
    np = None

try:
    from PIL import Image, ImageDraw, ImageSequence, ImageTk
except Exception as exc:  # pragma: no cover - shown only on machines without Pillow
    messagebox.showerror("缺少依赖", f"需要安装 Pillow 才能播放 GIF：\n{exc}")
    raise

try:
    import pystray
except Exception:  # pragma: no cover - pystray is only needed for the packaged Windows app
    pystray = None


APP_TITLE = "猪猪指针"
GIF_NAME = "pig_pointer.gif"
ICON_NAME = "pig_pointer.ico"
SETTINGS_FILE_NAME = "settings.json"
STARTUP_VALUE_NAME = "PigPointer"

WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WS_POPUP = 0x80000000
WS_MAXIMIZEBOX = 0x00010000
GWL_STYLE = -16
SW_HIDE = 0
SW_SHOWNOACTIVATE = 4
ULW_ALPHA = 0x00000002
AC_SRC_OVER = 0
AC_SRC_ALPHA = 1
BI_RGB = 0
DIB_RGB_COLORS = 0
WM_SETICON = 0x0080
WM_NCHITTEST = 0x0084
HTTRANSPARENT = -1
ERROR_CLASS_ALREADY_EXISTS = 1410
IMAGE_ICON = 1
ICON_SMALL = 0
ICON_BIG = 1
ICON_SMALL2 = 2
LR_LOADFROMFILE = 0x00000010
SM_CXICON = 11
SM_CYICON = 12
SM_CXCURSOR = 13
SM_CYCURSOR = 14
SM_CXSMICON = 49
SM_CYSMICON = 50
DI_NORMAL = 0x0003
IDC_ARROW = 32512
SPI_SETCURSORS = 0x0057
STANDARD_CURSOR_IDS = (
    32512,  # OCR_NORMAL
    32513,  # OCR_IBEAM
    32514,  # OCR_WAIT
    32515,  # OCR_CROSS
    32516,  # OCR_UP
    32642,  # OCR_SIZENWSE
    32643,  # OCR_SIZENESW
    32644,  # OCR_SIZEWE
    32645,  # OCR_SIZENS
    32646,  # OCR_SIZEALL
    32648,  # OCR_NO
    32649,  # OCR_HAND
    32650,  # OCR_APPSTARTING
    32651,  # OCR_HELP
)
_CURSOR_CAPTURE_API_READY = False
SETTINGS_VERSION = 1
CUSTOM_ASSETS_DIR_NAME = "assets"
DEFAULT_PIG_CUSTOM_ID = "__default_pig__"
CUSTOM_CONNECTION_MOUSE = "都连到鼠标"
CUSTOM_CONNECTION_CHAIN = "串成一串"
CUSTOM_CONNECTION_MODES = (CUSTOM_CONNECTION_MOUSE, CUSTOM_CONNECTION_CHAIN)
CUSTOM_ATTACH_AUTO = "自动识别"
CUSTOM_ATTACH_FIXED = "手动固定"
CUSTOM_ATTACH_MODES = (CUSTOM_ATTACH_AUTO, CUSTOM_ATTACH_FIXED)
CUSTOM_ASSET_SUFFIXES = {".gif", ".png", ".jpg", ".jpeg", ".webp", ".bmp"}
ROPE_COLORS = OrderedDict(
    (
        ("棕色", "#744d2d"),
        ("红色", "#d84343"),
        ("粉色", "#ee7da7"),
        ("黑色", "#202020"),
        ("白色", "#f7f4ee"),
        ("蓝色", "#3f7fd8"),
        ("自定义", "#744d2d"),
    )
)
DEFAULT_GLOBAL_SETTINGS = {
    "size": 150.0,
    "probability": 15.0,
    "anchor_x": 24.0,
    "anchor_y": 30.0,
    "anim_speed": 1.6,
    "trigger_interval": 4.0,
    "weight": 70.0,
    "rope_length": 72.0,
    "rope_width": 4.0,
    "performance_mode": "普通",
    "absolute_binding": False,
    "background": True,
    "custom_mode": False,
    "custom_include_pig": False,
    "custom_connection": CUSTOM_CONNECTION_MOUSE,
    "custom_collision": True,
    "custom_pig_rope_color": "棕色",
    "custom_pig_custom_rope_color": "#744d2d",
}
DEFAULT_CUSTOM_ASSET_SETTINGS = {
    "enabled": True,
    "size": 130.0,
    "rope_length": 72.0,
    "rope_color": "棕色",
    "custom_rope_color": "#744d2d",
    "anim_speed": 1.0,
    "probability": 10.0,
    "collision_radius": 46.0,
    "weight": 70.0,
    "reverse_loop": True,
    "attach_mode": CUSTOM_ATTACH_AUTO,
    "attach_x": 50.0,
    "attach_y": 0.0,
    "always_animate": False,
    "rope_width": 3.0,
}
CUSTOM_RESOURCE_PRESETS = OrderedDict(
    (
        (
            "重物感",
            {
                "size": 150.0,
                "rope_length": 92.0,
                "anim_speed": 0.8,
                "probability": 8.0,
                "collision_radius": 58.0,
                "weight": 100.0,
            },
        ),
        (
            "气球感",
            {
                "size": 126.0,
                "rope_length": 118.0,
                "anim_speed": 0.9,
                "probability": 5.0,
                "collision_radius": 44.0,
                "weight": 0.0,
            },
        ),
        (
            "拖尾串串",
            {
                "size": 122.0,
                "rope_length": 110.0,
                "anim_speed": 1.1,
                "probability": 14.0,
                "collision_radius": 42.0,
                "weight": 72.0,
                "connection": CUSTOM_CONNECTION_CHAIN,
            },
        ),
        (
            "轻快摆动",
            {
                "size": 118.0,
                "rope_length": 64.0,
                "anim_speed": 1.8,
                "probability": 24.0,
                "collision_radius": 40.0,
                "weight": 42.0,
            },
        ),
    )
)


@dataclass
class CustomAssetConfig:
    asset_id: str
    name: str
    path: str
    enabled: bool = True
    size: float = 130.0
    rope_length: float = 72.0
    rope_color: str = "棕色"
    custom_rope_color: str = "#744d2d"
    anim_speed: float = 1.0
    probability: float = 10.0
    collision_radius: float = 46.0
    weight: float = 70.0
    reverse_loop: bool = True
    attach_mode: str = CUSTOM_ATTACH_AUTO
    attach_x: float = 50.0
    attach_y: float = 0.0
    always_animate: bool = False
    rope_width: float = 3.0

    @classmethod
    def from_dict(cls, data: object) -> "CustomAssetConfig | None":
        if not isinstance(data, dict):
            return None
        path = data.get("path")
        if not isinstance(path, str) or not path.strip():
            return None
        asset_id = data.get("id")
        if not isinstance(asset_id, str) or not asset_id.strip():
            asset_id = uuid.uuid4().hex
        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            name = Path(path).name
        rope_color = data.get("rope_color")
        if not isinstance(rope_color, str) or rope_color not in ROPE_COLORS:
            rope_color = "棕色"
        custom_rope_color = data.get("custom_rope_color")
        if not isinstance(custom_rope_color, str) or not _is_hex_color(custom_rope_color):
            custom_rope_color = "#744d2d"
        attach_mode = data.get("attach_mode")
        if not isinstance(attach_mode, str) or attach_mode not in CUSTOM_ATTACH_MODES:
            attach_mode = CUSTOM_ATTACH_AUTO
        return cls(
            asset_id=asset_id,
            name=name,
            path=path,
            enabled=bool(data.get("enabled", True)),
            size=_clamp(data.get("size"), 36, 320, 130),
            rope_length=_clamp(data.get("rope_length"), 20, 260, 72),
            rope_color=rope_color,
            custom_rope_color=custom_rope_color,
            anim_speed=_clamp(data.get("anim_speed"), 0.2, 4.0, 1.0),
            probability=_clamp(data.get("probability"), 0, 100, 10),
            collision_radius=_clamp(data.get("collision_radius"), 8, 180, 46),
            weight=_clamp(data.get("weight"), 0, 100, 70),
            reverse_loop=bool(data.get("reverse_loop", True)),
            attach_mode=attach_mode,
            attach_x=_clamp(data.get("attach_x"), 0, 100, 50),
            attach_y=_clamp(data.get("attach_y"), 0, 100, 0),
            always_animate=bool(data.get("always_animate", str(path).lower().endswith(".gif"))),
            rope_width=_clamp(data.get("rope_width"), 1, 12, 3),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.asset_id,
            "name": self.name,
            "path": self.path,
            "enabled": self.enabled,
            "size": self.size,
            "rope_length": self.rope_length,
            "rope_color": self.rope_color,
            "custom_rope_color": self.custom_rope_color,
            "anim_speed": self.anim_speed,
            "probability": self.probability,
            "collision_radius": self.collision_radius,
            "weight": self.weight,
            "reverse_loop": self.reverse_loop,
            "attach_mode": self.attach_mode,
            "attach_x": self.attach_x,
            "attach_y": self.attach_y,
            "always_animate": self.always_animate,
            "rope_width": self.rope_width,
        }


@dataclass
class CustomItemState:
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    angle: float = 0.0
    angular_velocity: float = 0.0
    frame_index: int = 0
    frame_time_ms: float = 0.0
    animation_active: bool = False
    trigger_timer: float = 0.0
    anchor_x: float = 0.0
    anchor_y: float = 0.0


@dataclass
class CustomRenderedItem:
    config: CustomAssetConfig
    state: CustomItemState
    image: Image.Image
    joint: tuple[float, float]
    image_x: float
    image_y: float


@dataclass(frozen=True)
class PerformanceProfile:
    target_fps: int
    angle_step: int
    texture_cache_limit: int
    high_resolution_timer: bool


PERFORMANCE_PROFILES = {
    "高性能": PerformanceProfile(
        target_fps=120,
        angle_step=1,
        texture_cache_limit=900,
        high_resolution_timer=True,
    ),
    "普通": PerformanceProfile(
        target_fps=60,
        angle_step=2,
        texture_cache_limit=520,
        high_resolution_timer=True,
    ),
    "低性能": PerformanceProfile(
        target_fps=30,
        angle_step=4,
        texture_cache_limit=180,
        high_resolution_timer=False,
    ),
}


def _performance_profile(mode: str) -> PerformanceProfile:
    return PERFORMANCE_PROFILES.get(mode, PERFORMANCE_PROFILES["普通"])


def _enable_dpi_awareness() -> None:
    """Keep cursor coordinates and the transparent overlay in the same scale."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _set_windows_app_id() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("PigPointer.DesktopPet")
    except Exception:
        pass


def _resource_path(name: str) -> Path:
    base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base_dir / name


def _settings_path() -> Path:
    if sys.platform == "win32":
        base_dir = os.environ.get("APPDATA")
        if base_dir:
            return Path(base_dir) / "PigPointer" / SETTINGS_FILE_NAME
    return Path.home() / ".pig_pointer" / SETTINGS_FILE_NAME


def _default_assets_dir() -> Path:
    return _settings_path().parent / CUSTOM_ASSETS_DIR_NAME


def _startup_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable).resolve()}"'
    return f'"{Path(sys.executable).resolve()}" "{Path(__file__).resolve()}"'


def _is_startup_enabled() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
            value, _value_type = winreg.QueryValueEx(key, STARTUP_VALUE_NAME)
        return bool(value)
    except Exception:
        return False


def _set_startup_enabled(enabled: bool) -> None:
    if sys.platform != "win32":
        raise RuntimeError("开机启动只支持 Windows。")
    import winreg

    with winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        access=winreg.KEY_SET_VALUE,
    ) as key:
        if enabled:
            winreg.SetValueEx(key, STARTUP_VALUE_NAME, 0, winreg.REG_SZ, _startup_command())
        else:
            try:
                winreg.DeleteValue(key, STARTUP_VALUE_NAME)
            except FileNotFoundError:
                pass


def _clamp(value: object, minimum: float, maximum: float, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def _is_hex_color(value: str) -> bool:
    if len(value) != 7 or not value.startswith("#"):
        return False
    return all(char in "0123456789abcdefABCDEF" for char in value[1:])


def _safe_asset_name(name: str) -> str:
    cleaned = "".join(char if char not in '<>:"/\\|?*' else "_" for char in name).strip()
    return cleaned or "asset"


def _unique_asset_path(directory: Path, filename: str) -> Path:
    source_name = Path(filename)
    safe_stem = _safe_asset_name(source_name.stem)
    suffix = source_name.suffix.lower()
    candidate = directory / f"{safe_stem}{suffix}"
    index = 2
    while candidate.exists():
        candidate = directory / f"{safe_stem}_{index}{suffix}"
        index += 1
    return candidate


def _load_settings_file() -> dict[str, object]:
    path = _settings_path()
    try:
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


LRESULT = ctypes.c_ssize_t
HBITMAP = getattr(wintypes, "HBITMAP", wintypes.HANDLE)
HGDIOBJ = getattr(wintypes, "HGDIOBJ", wintypes.HANDLE)
HICON = getattr(wintypes, "HICON", wintypes.HANDLE)
HCURSOR = getattr(wintypes, "HCURSOR", wintypes.HANDLE)
WNDPROC = ctypes.WINFUNCTYPE(
    LRESULT,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
)


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class CURSORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hCursor", HCURSOR),
        ("ptScreenPos", POINT),
    ]


class ICONINFO(ctypes.Structure):
    _fields_ = [
        ("fIcon", wintypes.BOOL),
        ("xHotspot", wintypes.DWORD),
        ("yHotspot", wintypes.DWORD),
        ("hbmMask", HBITMAP),
        ("hbmColor", HBITMAP),
    ]


class SIZE(ctypes.Structure):
    _fields_ = [("cx", wintypes.LONG), ("cy", wintypes.LONG)]


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ("BlendOp", wintypes.BYTE),
        ("BlendFlags", wintypes.BYTE),
        ("SourceConstantAlpha", wintypes.BYTE),
        ("AlphaFormat", wintypes.BYTE),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", wintypes.DWORD * 3),
    ]


def _alpha_overlay_proc(
    hwnd: wintypes.HWND,
    msg: wintypes.UINT,
    wparam: wintypes.WPARAM,
    lparam: wintypes.LPARAM,
) -> int:
    if msg == WM_NCHITTEST:
        return HTTRANSPARENT
    return ctypes.windll.user32.DefWindowProcW(hwnd, msg, wparam, lparam)


_ALPHA_OVERLAY_PROC = WNDPROC(_alpha_overlay_proc)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", HICON),
        ("hCursor", HCURSOR),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


class AlphaOverlay:
    _class_name = "PigPointerAlphaOverlayWindow"
    _registered = False
    _api_ready = False

    def __init__(self, title: str) -> None:
        if sys.platform != "win32":
            raise RuntimeError("AlphaOverlay is only available on Windows")
        self._configure_api()
        self._register_class()
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        self.hwnd = user32.CreateWindowExW(
            WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
            self._class_name,
            title,
            WS_POPUP,
            0,
            0,
            1,
            1,
            None,
            None,
            kernel32.GetModuleHandleW(None),
            None,
        )
        if not self.hwnd:
            raise ctypes.WinError(ctypes.get_last_error())
        self.visible = False

    @classmethod
    def _configure_api(cls) -> None:
        if cls._api_ready:
            return
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        kernel32 = ctypes.windll.kernel32

        kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        kernel32.GetModuleHandleW.restype = wintypes.HMODULE

        user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
        user32.RegisterClassW.restype = wintypes.ATOM
        user32.CreateWindowExW.argtypes = [
            wintypes.DWORD,
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.DWORD,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.HWND,
            wintypes.HMENU,
            wintypes.HINSTANCE,
            wintypes.LPVOID,
        ]
        user32.CreateWindowExW.restype = wintypes.HWND
        user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user32.DefWindowProcW.restype = LRESULT
        user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.ShowWindow.restype = wintypes.BOOL
        user32.DestroyWindow.argtypes = [wintypes.HWND]
        user32.DestroyWindow.restype = wintypes.BOOL
        user32.GetDC.argtypes = [wintypes.HWND]
        user32.GetDC.restype = wintypes.HDC
        user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
        user32.ReleaseDC.restype = ctypes.c_int
        user32.UpdateLayeredWindow.argtypes = [
            wintypes.HWND,
            wintypes.HDC,
            ctypes.POINTER(POINT),
            ctypes.POINTER(SIZE),
            wintypes.HDC,
            ctypes.POINTER(POINT),
            wintypes.COLORREF,
            ctypes.POINTER(BLENDFUNCTION),
            wintypes.DWORD,
        ]
        user32.UpdateLayeredWindow.restype = wintypes.BOOL

        gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
        gdi32.CreateCompatibleDC.restype = wintypes.HDC
        gdi32.DeleteDC.argtypes = [wintypes.HDC]
        gdi32.DeleteDC.restype = wintypes.BOOL
        gdi32.CreateDIBSection.argtypes = [
            wintypes.HDC,
            ctypes.POINTER(BITMAPINFO),
            wintypes.UINT,
            ctypes.POINTER(wintypes.LPVOID),
            wintypes.HANDLE,
            wintypes.DWORD,
        ]
        gdi32.CreateDIBSection.restype = HBITMAP
        gdi32.SelectObject.argtypes = [wintypes.HDC, HGDIOBJ]
        gdi32.SelectObject.restype = HGDIOBJ
        gdi32.DeleteObject.argtypes = [HGDIOBJ]
        gdi32.DeleteObject.restype = wintypes.BOOL
        cls._api_ready = True

    @classmethod
    def _register_class(cls) -> None:
        if cls._registered:
            return
        hinstance = ctypes.windll.kernel32.GetModuleHandleW(None)
        wndclass = WNDCLASSW()
        wndclass.lpfnWndProc = _ALPHA_OVERLAY_PROC
        wndclass.hInstance = hinstance
        wndclass.lpszClassName = cls._class_name
        atom = ctypes.windll.user32.RegisterClassW(ctypes.byref(wndclass))
        if not atom:
            error = ctypes.get_last_error()
            if error != ERROR_CLASS_ALREADY_EXISTS:
                raise ctypes.WinError(error)
        cls._registered = True

    def show(self) -> None:
        if not self.visible:
            ctypes.windll.user32.ShowWindow(self.hwnd, SW_SHOWNOACTIVATE)
            self.visible = True

    def hide(self) -> None:
        if self.hwnd:
            ctypes.windll.user32.ShowWindow(self.hwnd, SW_HIDE)
        self.visible = False

    def destroy(self) -> None:
        if self.hwnd:
            ctypes.windll.user32.DestroyWindow(self.hwnd)
            self.hwnd = None
        self.visible = False

    def update_pixels(self, bgra: bytes, width: int, height: int, x: int, y: int) -> None:
        if not self.hwnd:
            return
        if width <= 0 or height <= 0:
            return

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = width
        bmi.bmiHeader.biHeight = -height
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = BI_RGB
        bmi.bmiHeader.biSizeImage = len(bgra)

        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        screen_dc = user32.GetDC(None)
        memory_dc = gdi32.CreateCompatibleDC(screen_dc)
        bits = wintypes.LPVOID()
        bitmap = gdi32.CreateDIBSection(screen_dc, ctypes.byref(bmi), DIB_RGB_COLORS, ctypes.byref(bits), None, 0)
        if not bitmap:
            gdi32.DeleteDC(memory_dc)
            user32.ReleaseDC(None, screen_dc)
            return

        ctypes.memmove(bits, bgra, len(bgra))
        old_bitmap = gdi32.SelectObject(memory_dc, bitmap)
        destination = POINT(int(x), int(y))
        source = POINT(0, 0)
        size = SIZE(width, height)
        blend = BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)
        user32.UpdateLayeredWindow(
            self.hwnd,
            screen_dc,
            ctypes.byref(destination),
            ctypes.byref(size),
            memory_dc,
            ctypes.byref(source),
            0,
            ctypes.byref(blend),
            ULW_ALPHA,
        )
        gdi32.SelectObject(memory_dc, old_bitmap)
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(memory_dc)
        user32.ReleaseDC(None, screen_dc)
        self.show()

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


def _load_windows_icon(icon_path: Path, width: int, height: int) -> int | None:
    if sys.platform != "win32" or not icon_path.exists():
        return None
    user32 = ctypes.windll.user32
    user32.LoadImageW.argtypes = [
        wintypes.HINSTANCE,
        wintypes.LPCWSTR,
        wintypes.UINT,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
    ]
    user32.LoadImageW.restype = wintypes.HANDLE
    hicon = user32.LoadImageW(None, str(icon_path), IMAGE_ICON, width, height, LR_LOADFROMFILE)
    return int(hicon) if hicon else None


def _resample_filter() -> int:
    return getattr(Image, "Resampling", Image).LANCZOS


def _capture_system_cursor() -> tuple[Image.Image, tuple[float, float]] | None:
    if sys.platform != "win32":
        return None
    try:
        _configure_cursor_capture_api()
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32

        cursor_info = CURSORINFO()
        cursor_info.cbSize = ctypes.sizeof(CURSORINFO)
        cursor = None
        if user32.GetCursorInfo(ctypes.byref(cursor_info)) and cursor_info.hCursor:
            cursor = cursor_info.hCursor
        if not cursor:
            cursor = user32.LoadCursorW(None, wintypes.LPCWSTR(IDC_ARROW))
        if not cursor:
            return None

        icon_info = ICONINFO()
        hotspot = (0.0, 0.0)
        if user32.GetIconInfo(cursor, ctypes.byref(icon_info)):
            hotspot = (float(icon_info.xHotspot), float(icon_info.yHotspot))
            for handle in (icon_info.hbmMask, icon_info.hbmColor):
                if handle:
                    try:
                        gdi32.DeleteObject(handle)
                    except Exception:
                        pass

        width = max(16, user32.GetSystemMetrics(SM_CXCURSOR) or 32)
        height = max(16, user32.GetSystemMetrics(SM_CYCURSOR) or 32)
        screen_dc = user32.GetDC(None)
        if not screen_dc:
            return None
        try:
            black_raw = _draw_cursor_to_dib(screen_dc, cursor, width, height, (0, 0, 0, 255))
            white_raw = _draw_cursor_to_dib(screen_dc, cursor, width, height, (255, 255, 255, 255))
        finally:
            user32.ReleaseDC(None, screen_dc)
        if black_raw is None or white_raw is None:
            return None

        black = Image.frombytes("RGBA", (width, height), black_raw, "raw", "BGRA")
        white = Image.frombytes("RGBA", (width, height), white_raw, "raw", "BGRA")
        result = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        black_pixels = black.load()
        white_pixels = white.load()
        result_pixels = result.load()
        for y in range(height):
            for x in range(width):
                br, bg, bb, _ba = black_pixels[x, y]
                wr, wg, wb, _wa = white_pixels[x, y]
                alpha = 255 - max(abs(wr - br), abs(wg - bg), abs(wb - bb))
                if alpha <= 2:
                    continue
                red = min(255, max(0, round(br * 255 / alpha)))
                green = min(255, max(0, round(bg * 255 / alpha)))
                blue = min(255, max(0, round(bb * 255 / alpha)))
                result_pixels[x, y] = (red, green, blue, alpha)

        return result, hotspot
    except Exception:
        return None


def _configure_cursor_capture_api() -> None:
    global _CURSOR_CAPTURE_API_READY
    if _CURSOR_CAPTURE_API_READY:
        return
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    user32.GetCursorInfo.argtypes = [ctypes.POINTER(CURSORINFO)]
    user32.GetCursorInfo.restype = wintypes.BOOL
    user32.GetIconInfo.argtypes = [HCURSOR, ctypes.POINTER(ICONINFO)]
    user32.GetIconInfo.restype = wintypes.BOOL
    user32.GetSystemMetrics.argtypes = [ctypes.c_int]
    user32.GetSystemMetrics.restype = ctypes.c_int
    user32.GetDC.argtypes = [wintypes.HWND]
    user32.GetDC.restype = wintypes.HDC
    user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    user32.ReleaseDC.restype = ctypes.c_int
    user32.LoadCursorW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR]
    user32.LoadCursorW.restype = HCURSOR
    user32.DrawIconEx.argtypes = [
        wintypes.HDC,
        ctypes.c_int,
        ctypes.c_int,
        HCURSOR,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
        wintypes.HBRUSH,
        wintypes.UINT,
    ]
    user32.DrawIconEx.restype = wintypes.BOOL

    gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi32.CreateCompatibleDC.restype = wintypes.HDC
    gdi32.DeleteDC.argtypes = [wintypes.HDC]
    gdi32.DeleteDC.restype = wintypes.BOOL
    gdi32.CreateDIBSection.argtypes = [
        wintypes.HDC,
        ctypes.POINTER(BITMAPINFO),
        wintypes.UINT,
        ctypes.POINTER(wintypes.LPVOID),
        wintypes.HANDLE,
        wintypes.DWORD,
    ]
    gdi32.CreateDIBSection.restype = HBITMAP
    gdi32.SelectObject.argtypes = [wintypes.HDC, HGDIOBJ]
    gdi32.SelectObject.restype = HGDIOBJ
    gdi32.DeleteObject.argtypes = [HGDIOBJ]
    gdi32.DeleteObject.restype = wintypes.BOOL
    _CURSOR_CAPTURE_API_READY = True


def _draw_cursor_to_dib(
    screen_dc: int,
    cursor: int,
    width: int,
    height: int,
    background: tuple[int, int, int, int],
) -> bytes | None:
    try:
        _configure_cursor_capture_api()
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        memory_dc = gdi32.CreateCompatibleDC(screen_dc)
        if not memory_dc:
            return None
        bitmap_info = BITMAPINFO()
        bitmap_info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bitmap_info.bmiHeader.biWidth = width
        bitmap_info.bmiHeader.biHeight = -height
        bitmap_info.bmiHeader.biPlanes = 1
        bitmap_info.bmiHeader.biBitCount = 32
        bitmap_info.bmiHeader.biCompression = BI_RGB
        bitmap_info.bmiHeader.biSizeImage = width * height * 4
        bits = wintypes.LPVOID()
        bitmap = gdi32.CreateDIBSection(screen_dc, ctypes.byref(bitmap_info), DIB_RGB_COLORS, ctypes.byref(bits), None, 0)
        if not bitmap or not bits:
            gdi32.DeleteDC(memory_dc)
            return None
        fill = bytes((background[2], background[1], background[0], background[3])) * (width * height)
        ctypes.memmove(bits, fill, len(fill))
        old_bitmap = gdi32.SelectObject(memory_dc, bitmap)
        if not user32.DrawIconEx(memory_dc, 0, 0, cursor, width, height, 0, None, DI_NORMAL):
            gdi32.SelectObject(memory_dc, old_bitmap)
            gdi32.DeleteObject(bitmap)
            gdi32.DeleteDC(memory_dc)
            return None
        raw = ctypes.string_at(bits, width * height * 4)
        gdi32.SelectObject(memory_dc, old_bitmap)
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(memory_dc)
        return raw
    except Exception:
        return None


class CursorVisibilityGuard:
    def __init__(self) -> None:
        self.active = False
        self.hide_count = 0
        self.replaced_system_cursors = False
        self.atexit_registered = False

    def hide(self) -> None:
        if sys.platform != "win32" or self.active:
            return
        try:
            user32 = ctypes.windll.user32
            self.replaced_system_cursors = self._replace_system_cursors_with_transparent(user32)
            user32.ShowCursor.argtypes = [wintypes.BOOL]
            user32.ShowCursor.restype = ctypes.c_int
            count = 0
            for _ in range(32):
                count = user32.ShowCursor(False)
                self.hide_count += 1
                if count < 0:
                    break
            self.active = True
            if not self.atexit_registered:
                atexit.register(self.show)
                self.atexit_registered = True
        except Exception:
            self.active = self.replaced_system_cursors

    def show(self) -> None:
        if sys.platform != "win32" or not self.active:
            return
        try:
            user32 = ctypes.windll.user32
            if self.replaced_system_cursors:
                user32.SystemParametersInfoW.argtypes = [wintypes.UINT, wintypes.UINT, wintypes.LPVOID, wintypes.UINT]
                user32.SystemParametersInfoW.restype = wintypes.BOOL
                user32.SystemParametersInfoW(SPI_SETCURSORS, 0, None, 0)
                self.replaced_system_cursors = False
            for _ in range(max(1, self.hide_count + 4)):
                count = user32.ShowCursor(True)
                if count >= 0:
                    break
        except Exception:
            pass
        self.hide_count = 0
        self.active = False

    @staticmethod
    def _replace_system_cursors_with_transparent(user32) -> bool:
        kernel32 = ctypes.windll.kernel32
        user32.GetSystemMetrics.argtypes = [ctypes.c_int]
        user32.GetSystemMetrics.restype = ctypes.c_int
        user32.CreateCursor.argtypes = [
            wintypes.HINSTANCE,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        user32.CreateCursor.restype = HCURSOR
        user32.SetSystemCursor.argtypes = [HCURSOR, wintypes.DWORD]
        user32.SetSystemCursor.restype = wintypes.BOOL
        user32.DestroyCursor.argtypes = [HCURSOR]
        user32.DestroyCursor.restype = wintypes.BOOL
        user32.SystemParametersInfoW.argtypes = [wintypes.UINT, wintypes.UINT, wintypes.LPVOID, wintypes.UINT]
        user32.SystemParametersInfoW.restype = wintypes.BOOL
        kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        kernel32.GetModuleHandleW.restype = wintypes.HMODULE

        width = max(16, user32.GetSystemMetrics(SM_CXCURSOR) or 32)
        height = max(16, user32.GetSystemMetrics(SM_CYCURSOR) or 32)
        hinstance = kernel32.GetModuleHandleW(None)
        changed = False
        for cursor_id in STANDARD_CURSOR_IDS:
            cursor = CursorVisibilityGuard._create_transparent_cursor(user32, hinstance, width, height)
            if not cursor:
                if changed:
                    user32.SystemParametersInfoW(SPI_SETCURSORS, 0, None, 0)
                return False
            if user32.SetSystemCursor(cursor, cursor_id):
                changed = True
            else:
                user32.DestroyCursor(cursor)
                if changed:
                    user32.SystemParametersInfoW(SPI_SETCURSORS, 0, None, 0)
                return False
        return changed

    @staticmethod
    def _create_transparent_cursor(user32, hinstance: int, width: int, height: int) -> int:
        stride = ((width + 15) // 16) * 2
        mask_size = stride * height
        and_plane = (ctypes.c_ubyte * mask_size)(*([0xFF] * mask_size))
        xor_plane = (ctypes.c_ubyte * mask_size)()
        return int(user32.CreateCursor(hinstance, 0, 0, width, height, and_plane, xor_plane) or 0)


class GifRenderer:
    def __init__(self, gif_path: Path, tk_master: tk.Misc) -> None:
        self.gif_path = gif_path
        self.tk_master = tk_master
        self.frames: list[Image.Image] = []
        self.durations: list[int] = []
        self.body_joints: list[tuple[float, float]] = []
        self.base_size = (1, 1)
        self._cache: OrderedDict[
            tuple[int, int, int],
            tuple[Image.Image, tuple[float, float], bytes],
        ] = OrderedDict()
        self._photo_cache: OrderedDict[tuple[int, int, int], tuple[ImageTk.PhotoImage, tuple[float, float]]] = OrderedDict()
        self.cache_limit = PERFORMANCE_PROFILES["普通"].texture_cache_limit
        self._load_gif()

    def _load_gif(self) -> None:
        source = Image.open(self.gif_path)
        raw_frames = [frame.convert("RGBA") for frame in ImageSequence.Iterator(source)]
        if not raw_frames:
            raise ValueError("GIF 中没有可播放的帧")

        crop_box = self._union_bbox(raw_frames)
        source_frames = [frame.crop(crop_box) for frame in raw_frames]
        body_parts = [self._erase_upper_rope(frame) for frame in source_frames]
        body_frames = [part[0] for part in body_parts]
        body_joints = [part[1] for part in body_parts]
        source_durations = [
            max(32, min(60, int(frame.info.get("duration", source.info.get("duration", 40)) or 40)))
            for frame in ImageSequence.Iterator(source)
        ]
        if len(source_durations) != len(source_frames):
            source_durations = [40] * len(source_frames)

        self.frames = []
        self.durations = []
        for index, frame in enumerate(source_frames):
            body_frame = body_frames[index]
            body_joint = body_joints[index]

            self.frames.append(body_frame)
            self.body_joints.append(body_joint)
            self.durations.append(source_durations[index])

        forward_frames = self.frames
        forward_body_joints = self.body_joints
        forward_durations = self.durations
        self.frames = forward_frames + forward_frames[-2::-1]
        self.body_joints = forward_body_joints + forward_body_joints[-2::-1]
        self.durations = forward_durations + forward_durations[-2::-1]

        self.base_size = self.frames[0].size

    @staticmethod
    def _union_bbox(frames: list[Image.Image]) -> tuple[int, int, int, int]:
        left = top = 10**9
        right = bottom = -1
        for frame in frames:
            bbox = frame.getbbox()
            if bbox is None:
                continue
            left = min(left, bbox[0])
            top = min(top, bbox[1])
            right = max(right, bbox[2])
            bottom = max(bottom, bbox[3])
        if right <= left or bottom <= top:
            return (0, 0, frames[0].width, frames[0].height)
        return (left, top, right, bottom)

    @staticmethod
    def _find_top_rope_joint(frame: Image.Image) -> tuple[float, float]:
        alpha = frame.getchannel("A")
        for y in range(alpha.height):
            xs = [x for x in range(alpha.width) if alpha.getpixel((x, y)) > 24]
            if xs:
                return (sum(xs) / len(xs), float(y))
        return (frame.width / 2.0, 0.0)

    @staticmethod
    def _is_rope_pixel(red: int, green: int, blue: int, alpha: int) -> bool:
        return alpha > 24 and 55 <= red <= 170 and 25 <= green <= 125 and 8 <= blue <= 105 and red > green > blue

    @classmethod
    def _erase_upper_rope(cls, frame: Image.Image) -> tuple[Image.Image, tuple[float, float]]:
        image = frame.copy()
        pixels = image.load()
        width, height = image.size
        centers = []
        attach_y = 122
        for y in range(min(height, 150)):
            rope_xs = []
            for x in range(width):
                red, green, blue, alpha = pixels[x, y]
                if cls._is_rope_pixel(red, green, blue, alpha):
                    rope_xs.append(x)
            if rope_xs and len(rope_xs) <= 26:
                centers.append(sum(rope_xs) / len(rope_xs))
                attach_y = y
            elif rope_xs and y > 35:
                attach_y = max(0, y - 1)
                break
            elif y > 35:
                break

        if centers:
            center_x = int(round(sum(centers[: min(len(centers), 80)]) / min(len(centers), 80)))
            erase_bottom = min(height, max(0, attach_y))
            erase_left = max(0, center_x - 9)
            erase_right = min(width, center_x + 10)
            for y in range(erase_bottom):
                for x in range(erase_left, erase_right):
                    red, green, blue, alpha = pixels[x, y]
                    if alpha > 0:
                        pixels[x, y] = (red, green, blue, 0)
            attach_joint = (float(center_x), float(attach_y))
        else:
            attach_joint = cls._find_top_rope_joint(frame)

        for y in range(min(height, max(0, attach_y))):
            rope_xs = []
            for x in range(width):
                red, green, blue, alpha = pixels[x, y]
                if cls._is_rope_pixel(red, green, blue, alpha):
                    rope_xs.append(x)
            if rope_xs and (len(rope_xs) <= 18 or y < 122):
                for x in range(max(0, min(rope_xs) - 3), min(width, max(rope_xs) + 4)):
                    red, green, blue, alpha = pixels[x, y]
                    if alpha > 0:
                        pixels[x, y] = (red, green, blue, 0)
        for y in range(min(height, 120)):
            for x in range(width):
                red, green, blue, alpha = pixels[x, y]
                if alpha <= 18:
                    pixels[x, y] = (red, green, blue, 0)
        return image, attach_joint

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    @staticmethod
    def to_premultiplied_bgra(image: Image.Image) -> bytes:
        rgba = image.convert("RGBA")
        if np is not None:
            data = np.asarray(rgba, dtype=np.uint16)
            alpha = data[:, :, 3:4]
            rgb = (data[:, :, :3] * alpha // 255).astype(np.uint8)
            alpha8 = alpha.astype(np.uint8)
            bgra = np.concatenate((rgb[:, :, 2:3], rgb[:, :, 1:2], rgb[:, :, 0:1], alpha8), axis=2)
            return bgra.tobytes()

        pixels = rgba.tobytes("raw", "RGBA")
        bgra = bytearray(len(pixels))
        for index in range(0, len(pixels), 4):
            red = pixels[index]
            green = pixels[index + 1]
            blue = pixels[index + 2]
            alpha = pixels[index + 3]
            bgra[index] = blue * alpha // 255
            bgra[index + 1] = green * alpha // 255
            bgra[index + 2] = red * alpha // 255
            bgra[index + 3] = alpha
        return bytes(bgra)

    def render_asset(
        self, frame_index: int, display_height: int, angle: float, angle_step: int = 2
    ) -> tuple[Image.Image, tuple[float, float], bytes]:
        display_height = max(36, min(320, int(display_height)))
        angle_step = max(1, int(angle_step))
        angle_key = int(round(angle / angle_step) * angle_step)
        key = (frame_index % self.frame_count, display_height, angle_key)
        cached = self._cache.get(key)
        if cached is not None:
            self._cache.move_to_end(key)
            return cached

        frame = self.frames[key[0]]
        scale = display_height / frame.height
        display_width = max(1, int(round(frame.width * scale)))
        scaled = frame.resize((display_width, display_height), _resample_filter())
        frame_joint = self.body_joints[key[0]]
        pivot = (frame_joint[0] * scale, frame_joint[1] * scale)
        rotated, joint = self._rotate_about_joint(scaled, pivot, angle_key)

        result = (rotated, joint, self.to_premultiplied_bgra(rotated))
        self._cache[key] = result
        while len(self._cache) > self.cache_limit:
            self._cache.popitem(last=False)
        return result

    def render(self, frame_index: int, display_height: int, angle: float) -> tuple[ImageTk.PhotoImage, tuple[float, float]]:
        display_height = max(36, min(320, int(display_height)))
        angle_key = int(round(angle / 2.0) * 2)
        key = (frame_index % self.frame_count, display_height, angle_key)
        cached = self._photo_cache.get(key)
        if cached is not None:
            self._photo_cache.move_to_end(key)
            return cached

        image, joint, _bgra = self.render_asset(frame_index, display_height, angle_key)
        photo = ImageTk.PhotoImage(image, master=self.tk_master)
        result = (photo, joint)
        self._photo_cache[key] = result
        while len(self._photo_cache) > 90:
            self._photo_cache.popitem(last=False)
        return result

    @staticmethod
    def _rotate_about_joint(
        image: Image.Image, joint: tuple[float, float], angle: int
    ) -> tuple[Image.Image, tuple[float, float]]:
        w, h = image.size
        pad = int(max(w, h) * 3.0)
        canvas_w = max(pad, w + 80)
        canvas_h = max(pad, h + 120)
        pivot = (canvas_w // 2, int(canvas_h * 0.24))

        temp = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        paste_xy = (int(round(pivot[0] - joint[0])), int(round(pivot[1] - joint[1])))
        temp.alpha_composite(image, paste_xy)

        rotated = temp.rotate(
            angle,
            resample=getattr(Image, "Resampling", Image).BICUBIC,
            center=pivot,
            fillcolor=(0, 0, 0, 0),
        )
        bbox = rotated.getbbox()
        if bbox is None:
            return image, joint
        cropped = rotated.crop(bbox)
        new_joint = (pivot[0] - bbox[0], pivot[1] - bbox[1])
        return cropped, new_joint


class CustomAssetRenderer:
    def __init__(self, asset_path: Path, tk_master: tk.Misc) -> None:
        self.asset_path = asset_path
        self.tk_master = tk_master
        self.frames: list[Image.Image] = []
        self.durations: list[int] = []
        self.joints: list[tuple[float, float]] = []
        self.base_size = (1, 1)
        self._cache: OrderedDict[tuple[object, ...], tuple[Image.Image, tuple[float, float], bytes]] = OrderedDict()
        self._photo_cache: OrderedDict[tuple[object, ...], tuple[ImageTk.PhotoImage, tuple[float, float]]] = OrderedDict()
        self.cache_limit = 160
        self._load()

    def _load(self) -> None:
        source = Image.open(self.asset_path)
        raw_frames = [frame.convert("RGBA") for frame in ImageSequence.Iterator(source)]
        if not raw_frames:
            raw_frames = [source.convert("RGBA")]
        crop_box = GifRenderer._union_bbox(raw_frames)
        self.frames = []
        self.joints = []
        for frame in raw_frames:
            cropped = frame.crop(crop_box)
            self.frames.append(cropped)
            self.joints.append(self._find_attach_joint(cropped))
        self.durations = [
            max(24, min(200, int(frame.info.get("duration", source.info.get("duration", 40)) or 40)))
            for frame in ImageSequence.Iterator(source)
        ]
        if len(self.durations) != len(self.frames):
            self.durations = [40] * len(self.frames)
        self.base_size = self.frames[0].size

    @staticmethod
    def _find_attach_joint(frame: Image.Image) -> tuple[float, float]:
        alpha = frame.getchannel("A")
        for y in range(alpha.height):
            xs = [x for x in range(alpha.width) if alpha.getpixel((x, y)) > 24]
            if xs:
                return (sum(xs) / len(xs), float(y))
        return (frame.width / 2.0, 0.0)

    @staticmethod
    def _attach_cache_key(attach_mode: str, attach_x: float, attach_y: float) -> tuple[object, ...]:
        if attach_mode != CUSTOM_ATTACH_FIXED:
            return (CUSTOM_ATTACH_AUTO,)
        return (CUSTOM_ATTACH_FIXED, round(_clamp(attach_x, 0, 100, 50), 1), round(_clamp(attach_y, 0, 100, 0), 1))

    def _joint_for_frame(
        self,
        resolved_index: int,
        attach_mode: str,
        attach_x: float,
        attach_y: float,
    ) -> tuple[float, float]:
        if attach_mode == CUSTOM_ATTACH_FIXED:
            frame = self.frames[resolved_index]
            return (
                frame.width * _clamp(attach_x, 0, 100, 50) / 100.0,
                frame.height * _clamp(attach_y, 0, 100, 0) / 100.0,
            )
        return self.joints[resolved_index]

    def clear_cache(self) -> None:
        self._cache.clear()
        self._photo_cache.clear()

    def frame_count(self, reverse_loop: bool) -> int:
        if reverse_loop and len(self.frames) > 2:
            return len(self.frames) * 2 - 2
        return len(self.frames)

    def duration(self, frame_index: int, reverse_loop: bool) -> int:
        return self.durations[self._resolve_frame_index(frame_index, reverse_loop)]

    def _resolve_frame_index(self, frame_index: int, reverse_loop: bool) -> int:
        if not self.frames:
            return 0
        if reverse_loop and len(self.frames) > 2:
            sequence_count = len(self.frames) * 2 - 2
            index = frame_index % sequence_count
            if index >= len(self.frames):
                index = sequence_count - index
            return index
        return frame_index % len(self.frames)

    def render_asset(
        self,
        frame_index: int,
        display_height: int,
        angle: float,
        reverse_loop: bool,
        angle_step: int = 2,
        attach_mode: str = CUSTOM_ATTACH_AUTO,
        attach_x: float = 50.0,
        attach_y: float = 0.0,
    ) -> tuple[Image.Image, tuple[float, float], bytes]:
        display_height = max(24, min(420, int(display_height)))
        angle_step = max(1, int(angle_step))
        angle_key = int(round(angle / angle_step) * angle_step)
        resolved_index = self._resolve_frame_index(frame_index, reverse_loop)
        key = (resolved_index, display_height, angle_key, *self._attach_cache_key(attach_mode, attach_x, attach_y))
        cached = self._cache.get(key)
        if cached is not None:
            self._cache.move_to_end(key)
            return cached

        frame = self.frames[resolved_index]
        scale = display_height / frame.height
        display_width = max(1, int(round(frame.width * scale)))
        scaled = frame.resize((display_width, display_height), _resample_filter())
        joint = self._joint_for_frame(resolved_index, attach_mode, attach_x, attach_y)
        pivot = (joint[0] * scale, joint[1] * scale)
        rotated, rotated_joint = GifRenderer._rotate_about_joint(scaled, pivot, angle_key)
        result = (rotated, rotated_joint, GifRenderer.to_premultiplied_bgra(rotated))
        self._cache[key] = result
        while len(self._cache) > self.cache_limit:
            self._cache.popitem(last=False)
        return result

    def render(
        self,
        frame_index: int,
        display_height: int,
        angle: float,
        reverse_loop: bool,
        attach_mode: str = CUSTOM_ATTACH_AUTO,
        attach_x: float = 50.0,
        attach_y: float = 0.0,
    ) -> tuple[ImageTk.PhotoImage, tuple[float, float]]:
        display_height = max(24, min(420, int(display_height)))
        angle_key = int(round(angle / 2.0) * 2)
        resolved_index = self._resolve_frame_index(frame_index, reverse_loop)
        key = (resolved_index, display_height, angle_key, *self._attach_cache_key(attach_mode, attach_x, attach_y))
        cached = self._photo_cache.get(key)
        if cached is not None:
            self._photo_cache.move_to_end(key)
            return cached
        image, joint, _bgra = self.render_asset(
            frame_index,
            display_height,
            angle_key,
            reverse_loop,
            attach_mode=attach_mode,
            attach_x=attach_x,
            attach_y=attach_y,
        )
        photo = ImageTk.PhotoImage(image, master=self.tk_master)
        result = (photo, joint)
        self._photo_cache[key] = result
        while len(self._photo_cache) > 60:
            self._photo_cache.popitem(last=False)
        return result


class PigPointerApp:
    def __init__(self, root: tk.Tk, gif_path: Path) -> None:
        self.root = root
        self.renderer = GifRenderer(gif_path, root)
        self.settings_path = _settings_path()
        self.settings = _load_settings_file()
        self.save_after_id: str | None = None

        self.running = False
        self.overlay: AlphaOverlay | None = None
        self.tray_icon: SystemTrayIcon | None = None
        self.window_icon_handles: list[int] = []
        self.preview_photo: ImageTk.PhotoImage | None = None
        self.preview_last_time = 0.0
        self.cursor_api_ready = False
        self.timer_resolution_enabled = False
        self.cursor_guard = CursorVisibilityGuard()
        self.absolute_cursor_asset: tuple[Image.Image, tuple[float, float]] | None = None

        self.size_var = tk.DoubleVar(value=self._setting_float("size", DEFAULT_GLOBAL_SETTINGS["size"], 70, 260))
        self.prob_var = tk.DoubleVar(value=self._setting_float("probability", DEFAULT_GLOBAL_SETTINGS["probability"], 0, 100))
        self.anchor_x_var = tk.DoubleVar(value=self._setting_float("anchor_x", DEFAULT_GLOBAL_SETTINGS["anchor_x"], -30, 80))
        self.anchor_y_var = tk.DoubleVar(value=self._setting_float("anchor_y", DEFAULT_GLOBAL_SETTINGS["anchor_y"], -20, 90))
        self.anim_speed_var = tk.DoubleVar(value=self._setting_float("anim_speed", DEFAULT_GLOBAL_SETTINGS["anim_speed"], 0.5, 3.0))
        self.trigger_interval_var = tk.DoubleVar(value=self._setting_float("trigger_interval", DEFAULT_GLOBAL_SETTINGS["trigger_interval"], 1.0, 20.0))
        self.weight_var = tk.DoubleVar(value=self._setting_float("weight", DEFAULT_GLOBAL_SETTINGS["weight"], 0, 100))
        self.rope_length_var = tk.DoubleVar(value=self._setting_float("rope_length", DEFAULT_GLOBAL_SETTINGS["rope_length"], 36, 160))
        self.rope_width_var = tk.DoubleVar(value=self._setting_float("rope_width", DEFAULT_GLOBAL_SETTINGS["rope_width"], 1, 12))
        self.performance_mode_var = tk.StringVar(value=self._setting_mode("performance_mode", DEFAULT_GLOBAL_SETTINGS["performance_mode"]))
        self.absolute_binding_var = tk.BooleanVar(value=self._setting_bool("absolute_binding", DEFAULT_GLOBAL_SETTINGS["absolute_binding"]))
        self.background_var = tk.BooleanVar(value=self._setting_bool("background", DEFAULT_GLOBAL_SETTINGS["background"]))
        self.start_with_windows_var = tk.BooleanVar(value=_is_startup_enabled())
        self.custom_mode_var = tk.BooleanVar(value=self._setting_bool("custom_mode", DEFAULT_GLOBAL_SETTINGS["custom_mode"]))
        self.custom_include_pig_var = tk.BooleanVar(value=self._setting_bool("custom_include_pig", DEFAULT_GLOBAL_SETTINGS["custom_include_pig"]))
        self.custom_connection_var = tk.StringVar(value=self._setting_connection_mode("custom_connection", DEFAULT_GLOBAL_SETTINGS["custom_connection"]))
        self.custom_collision_var = tk.BooleanVar(value=self._setting_bool("custom_collision", DEFAULT_GLOBAL_SETTINGS["custom_collision"]))
        self.custom_preset_var = tk.StringVar(value=next(iter(CUSTOM_RESOURCE_PRESETS)))
        self.custom_assets_dir_var = tk.StringVar(value=self._setting_assets_dir("custom_assets_dir"))
        self.custom_pig_rope_color_var = tk.StringVar(value=self._setting_rope_color("custom_pig_rope_color", DEFAULT_GLOBAL_SETTINGS["custom_pig_rope_color"]))
        self.custom_pig_custom_rope_color_var = tk.StringVar(
            value=self._setting_hex_color("custom_pig_custom_rope_color", DEFAULT_GLOBAL_SETTINGS["custom_pig_custom_rope_color"])
        )
        self.status_var = tk.StringVar(value="准备就绪")
        self.custom_assets_dir_text = tk.StringVar()
        self.custom_status_var = tk.StringVar()
        self.custom_selected_id = tk.StringVar()
        self.custom_item_name_var = tk.StringVar(value="未选择资源")
        self.custom_item_enabled_var = tk.BooleanVar(value=True)
        self.custom_item_size_var = tk.DoubleVar(value=130)
        self.custom_item_rope_length_var = tk.DoubleVar(value=72)
        self.custom_item_rope_color_var = tk.StringVar(value="棕色")
        self.custom_item_anim_speed_var = tk.DoubleVar(value=1.0)
        self.custom_item_probability_var = tk.DoubleVar(value=10)
        self.custom_item_collision_var = tk.DoubleVar(value=46)
        self.custom_item_weight_var = tk.DoubleVar(value=70)
        self.custom_item_reverse_loop_var = tk.BooleanVar(value=True)
        self.custom_item_always_animate_var = tk.BooleanVar(value=False)
        self.custom_item_rope_width_var = tk.DoubleVar(value=3)
        self.custom_item_attach_mode_var = tk.StringVar(value=CUSTOM_ATTACH_AUTO)
        self.custom_item_attach_x_var = tk.DoubleVar(value=50)
        self.custom_item_attach_y_var = tk.DoubleVar(value=0)
        self.custom_item_size_text = tk.StringVar()
        self.custom_item_rope_length_text = tk.StringVar()
        self.custom_item_anim_speed_text = tk.StringVar()
        self.custom_item_probability_text = tk.StringVar()
        self.custom_item_collision_text = tk.StringVar()
        self.custom_item_weight_text = tk.StringVar()
        self.custom_item_rope_width_text = tk.StringVar()
        self.custom_item_attach_x_text = tk.StringVar()
        self.custom_item_attach_y_text = tk.StringVar()
        self.custom_color_swatch: tk.Canvas | None = None
        self.custom_color_swatch_rect: int | None = None
        self.custom_status_label: ttk.Label | None = None
        self.preview_attach_marker: int | None = None
        self.size_text = tk.StringVar()
        self.prob_text = tk.StringVar()
        self.anchor_x_text = tk.StringVar()
        self.anchor_y_text = tk.StringVar()
        self.anim_speed_text = tk.StringVar()
        self.trigger_interval_text = tk.StringVar()
        self.weight_text = tk.StringVar()
        self.rope_length_text = tk.StringVar()
        self.rope_width_text = tk.StringVar()

        self.frame_index = 0
        self.frame_time_ms = 0.0
        self.last_tick = time.perf_counter()
        self.animation_active = False
        self.trigger_timer = 0.0
        self.prewarm_jobs: list[tuple[int, int, int]] = []
        self.last_prewarm_time = 0.0

        self.rope_end_x = 0.0
        self.rope_end_y = 0.0
        self.rope_vel_x = 0.0
        self.rope_vel_y = 0.0
        self.pig_x = 0.0
        self.pig_y = 0.0
        self.pig_vel_x = 0.0
        self.pig_vel_y = 0.0
        self.pig_angle = 0.0
        self.pig_angular_velocity = 0.0
        self.last_anchor = (0.0, 0.0)
        self.last_cursor_velocity = (0.0, 0.0)
        self.initialized_physics = False
        self.custom_assets = self._load_custom_assets()
        self.custom_renderers: dict[str, CustomAssetRenderer] = {}
        self.custom_states: dict[str, CustomItemState] = {}
        self.custom_selected_ids: set[str] = set()
        self.custom_syncing_ui = False
        self.custom_preview_photo: ImageTk.PhotoImage | None = None
        self.custom_preview_bounds: tuple[str, float, float, float, float] | None = None

        self._build_control_panel()
        self._build_overlay()
        self._sync_slider_labels()
        self._prepare_prewarm_jobs()
        self._tick()

    def _build_control_panel(self) -> None:
        self.root.title(APP_TITLE)
        self._apply_window_icon(self.root)
        self.root.geometry("360x520")
        self.root.minsize(360, 360)
        self.root.maxsize(560, 760)
        self.root.resizable(True, True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close_window)

        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", font=("Microsoft YaHei UI", 9))
        style.configure("Title.TLabel", font=("Microsoft YaHei UI", 13, "bold"))
        style.configure("Status.TLabel", foreground="#5b4636")
        style.configure("Primary.TButton", padding=(12, 6))

        scroll_shell = ttk.Frame(self.root)
        scroll_shell.pack(fill="both", expand=True)

        self.scroll_canvas = tk.Canvas(scroll_shell, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(scroll_shell, orient="vertical", command=self.scroll_canvas.yview)
        self.scroll_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.scroll_canvas.pack(side="left", fill="both", expand=True)

        outer = ttk.Frame(self.scroll_canvas, padding=16)
        self.scroll_window = self.scroll_canvas.create_window((0, 0), window=outer, anchor="nw")
        outer.bind(
            "<Configure>",
            lambda _event: self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all")),
        )
        self.scroll_canvas.bind(
            "<Configure>",
            lambda event: self.scroll_canvas.itemconfigure(self.scroll_window, width=event.width),
        )
        self.scroll_canvas.bind("<Enter>", self._bind_mousewheel)
        self.scroll_canvas.bind("<Leave>", self._unbind_mousewheel)

        title_row = ttk.Frame(outer)
        title_row.pack(fill="x")
        ttk.Label(title_row, text=APP_TITLE, style="Title.TLabel").pack(side="left")
        ttk.Checkbutton(
            title_row,
            text="自定义模式",
            variable=self.custom_mode_var,
            command=self._on_custom_mode_changed,
        ).pack(side="right")
        ttk.Label(
            outer,
            text="鼠标后面会牵着 GIF 摆动，透明层不会挡住点击。",
            foreground="#6c625c",
        ).pack(anchor="w", pady=(4, 12))

        button_row = ttk.Frame(outer)
        button_row.pack(fill="x", pady=(0, 12))
        self.start_button = ttk.Button(button_row, text="启动", command=self.start_pet, style="Primary.TButton")
        self.stop_button = ttk.Button(button_row, text="关闭", command=self.stop_pet, style="Primary.TButton")
        self.hide_button = ttk.Button(button_row, text="后台运行", command=self.hide_to_background, style="Primary.TButton")
        self.start_button.pack(side="left", expand=True, fill="x", padx=(0, 6))
        self.stop_button.pack(side="left", expand=True, fill="x", padx=6)
        self.hide_button.pack(side="left", expand=True, fill="x", padx=(6, 0))

        ttk.Button(outer, text="预览触发一次动画", command=self.trigger_animation_once).pack(fill="x", pady=(0, 12))

        ttk.Checkbutton(
            outer,
            text="关闭面板时继续后台工作",
            variable=self.background_var,
            command=self._schedule_save_settings,
        ).pack(anchor="w", pady=(0, 14))

        ttk.Checkbutton(
            outer,
            text="开机自动启动",
            variable=self.start_with_windows_var,
            command=self._on_startup_changed,
        ).pack(anchor="w", pady=(0, 14))

        ttk.Checkbutton(
            outer,
            text="绝对绑定模式（隐藏系统鼠标并自绘鼠标）",
            variable=self.absolute_binding_var,
            command=self._on_absolute_binding_changed,
        ).pack(anchor="w", pady=(0, 14))

        performance_row = ttk.Frame(outer)
        performance_row.pack(fill="x", pady=(0, 14))
        ttk.Label(performance_row, text="性能模式").pack(side="left")
        performance_options = ttk.Frame(performance_row)
        performance_options.pack(side="right")
        for mode in ("高性能", "普通", "低性能"):
            ttk.Radiobutton(
                performance_options,
                text=mode,
                value=mode,
                variable=self.performance_mode_var,
                command=self._on_performance_mode_changed,
            ).pack(side="left", padx=(8, 0))

        ttk.Button(outer, text="恢复默认设置", command=self._reset_default_settings).pack(fill="x", pady=(0, 12))

        self.preview = tk.Canvas(
            outer,
            width=316,
            height=150,
            bg="#f7f4ee",
            highlightthickness=1,
            highlightbackground="#d8cec2",
        )
        self.preview.pack(fill="x", pady=(0, 14))
        self.preview_anchor = self.preview.create_oval(153, 14, 163, 24, fill="#5b4636", outline="")
        self.preview_anchor_ring = self.preview.create_oval(149, 13, 167, 31, outline="#e53935", width=2)
        self.preview_rope = self.preview.create_line(158, 22, 158, 74, fill="#744d2d", width=3, smooth=True)
        self.preview_image = self.preview.create_image(158, 22, anchor="nw")
        self.preview_attach_marker = self.preview.create_oval(
            154,
            18,
            162,
            26,
            fill="#e53935",
            outline="#ffffff",
            width=1,
            state="hidden",
        )
        self.preview.bind("<ButtonPress-1>", self._on_preview_attach_drag)
        self.preview.bind("<B1-Motion>", self._on_preview_attach_drag)

        self.custom_attach_section = ttk.Frame(outer)
        self._build_custom_attach_panel(self.custom_attach_section)

        self.default_settings_section = ttk.Frame(outer)
        self.default_settings_section.pack(fill="x")
        self._add_slider(self.default_settings_section, "GIF 大小", self.size_var, 70, 260, self.size_text)
        self._add_slider(self.default_settings_section, "绳子长度", self.rope_length_var, 36, 160, self.rope_length_text)
        self._add_slider(self.default_settings_section, "绳子粗细", self.rope_width_var, 1, 12, self.rope_width_text)
        self._add_slider(self.default_settings_section, "重量感", self.weight_var, 0, 100, self.weight_text)
        self._add_slider(self.default_settings_section, "动画触发概率", self.prob_var, 0, 100, self.prob_text)
        self._add_slider(self.default_settings_section, "动画播放速度", self.anim_speed_var, 0.5, 3.0, self.anim_speed_text)
        self._add_slider(self.default_settings_section, "触发间隔", self.trigger_interval_var, 1.0, 20.0, self.trigger_interval_text)
        self._add_slider(self.default_settings_section, "绑定点横向", self.anchor_x_var, -30, 80, self.anchor_x_text)
        self._add_slider(self.default_settings_section, "绑定点纵向", self.anchor_y_var, -20, 90, self.anchor_y_text)

        self.custom_section = ttk.Frame(outer)
        self.custom_section.pack(fill="x", pady=(14, 0))
        self._build_custom_panel(self.custom_section)

        self.status_separator = ttk.Separator(outer)
        self.status_separator.pack(fill="x", pady=(14, 10))
        status_row = ttk.Frame(outer)
        status_row.pack(fill="x")
        ttk.Label(status_row, textvariable=self.status_var, style="Status.TLabel").pack(side="left")
        ttk.Button(status_row, text="退出软件", command=self.quit_app).pack(side="right")

        self._update_buttons()
        self._refresh_custom_panel()
        self._sync_custom_status()
        self.root.after(100, self._disable_maximize_button)
        self.root.after(250, self._refresh_taskbar_icon)

    def _add_slider(
        self,
        parent: ttk.Frame,
        title: str,
        variable: tk.DoubleVar,
        minimum: int,
        maximum: int,
        label_var: tk.StringVar,
    ) -> None:
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(8, 0))
        ttk.Label(row, text=title).pack(side="left")
        ttk.Label(row, textvariable=label_var, foreground="#6c625c").pack(side="right")
        ttk.Scale(
            parent,
            variable=variable,
            from_=minimum,
            to=maximum,
            command=lambda _value: self._on_setting_changed(),
        ).pack(fill="x")

    def _add_custom_slider(
        self,
        parent: ttk.Frame,
        title: str,
        variable: tk.DoubleVar,
        minimum: int | float,
        maximum: int | float,
        label_var: tk.StringVar,
        command: Callable[[], None] | None = None,
    ) -> None:
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(8, 0))
        ttk.Label(row, text=title).pack(side="left")
        ttk.Label(row, textvariable=label_var, foreground="#6c625c").pack(side="right")
        change_command = command or self._on_custom_item_setting_changed
        ttk.Scale(
            parent,
            variable=variable,
            from_=minimum,
            to=maximum,
            command=lambda _value: change_command(),
        ).pack(fill="x")

    def _build_custom_attach_panel(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="连接点校准", foreground="#5b4636").pack(anchor="w")
        attach_mode_row = ttk.Frame(parent)
        attach_mode_row.pack(fill="x", pady=(6, 0))
        ttk.Label(attach_mode_row, text="连接点模式").pack(side="left")
        ttk.OptionMenu(
            attach_mode_row,
            self.custom_item_attach_mode_var,
            self.custom_item_attach_mode_var.get(),
            *CUSTOM_ATTACH_MODES,
            command=lambda _value: self._on_custom_attach_mode_changed(),
        ).pack(side="right")
        self._add_custom_slider(
            parent,
            "连接点横向",
            self.custom_item_attach_x_var,
            0,
            100,
            self.custom_item_attach_x_text,
            self._on_custom_attach_slider_changed,
        )
        self._add_custom_slider(
            parent,
            "连接点纵向",
            self.custom_item_attach_y_var,
            0,
            100,
            self.custom_item_attach_y_text,
            self._on_custom_attach_slider_changed,
        )

    def _build_custom_panel(self, parent: ttk.Frame) -> None:
        ttk.Separator(parent).pack(fill="x", pady=(0, 10))
        top_row = ttk.Frame(parent)
        top_row.pack(fill="x", pady=(0, 8))
        ttk.Label(top_row, text="自定义资源").pack(side="left")
        ttk.Button(top_row, text="添加图片/GIF", command=self._add_custom_assets).pack(side="right")

        location_row = ttk.Frame(parent)
        location_row.pack(fill="x", pady=(0, 8))
        ttk.Button(location_row, text="保存位置", command=self._choose_custom_assets_dir).pack(side="left")
        ttk.Label(location_row, textvariable=self.custom_assets_dir_text, foreground="#6c625c").pack(
            side="left", fill="x", expand=True, padx=(8, 0)
        )

        connection_row = ttk.Frame(parent)
        connection_row.pack(fill="x", pady=(0, 8))
        ttk.Label(connection_row, text="连接方式").pack(side="left")
        ttk.OptionMenu(
            connection_row,
            self.custom_connection_var,
            self.custom_connection_var.get(),
            *CUSTOM_CONNECTION_MODES,
            command=lambda _value: self._on_custom_connection_changed(),
        ).pack(side="right")

        ttk.Checkbutton(
            parent,
            text="猪猪也参与",
            variable=self.custom_include_pig_var,
            command=self._on_custom_include_pig_changed,
        ).pack(anchor="w", pady=(0, 8))

        batch_row = ttk.Frame(parent)
        batch_row.pack(fill="x", pady=(0, 8))
        ttk.Button(batch_row, text="全部启用", command=self._enable_all_custom_assets).pack(
            side="left", expand=True, fill="x", padx=(0, 4)
        )
        ttk.Button(batch_row, text="全部暂停", command=self._pause_all_custom_assets).pack(
            side="left", expand=True, fill="x", padx=4
        )
        ttk.Button(batch_row, text="清空上传资源", command=self._clear_uploaded_custom_assets).pack(
            side="left", expand=True, fill="x", padx=(4, 0)
        )

        self.custom_listbox = tk.Listbox(
            parent,
            height=4,
            exportselection=False,
            activestyle="dotbox",
            selectmode=tk.EXTENDED,
        )
        self.custom_listbox.pack(fill="x", pady=(0, 8))
        self.custom_listbox.bind("<<ListboxSelect>>", self._on_custom_selection_changed)

        action_row = ttk.Frame(parent)
        action_row.pack(fill="x", pady=(0, 8))
        ttk.Button(action_row, text="重命名", command=self._rename_selected_custom_asset).pack(
            side="left", expand=True, fill="x", padx=(0, 3)
        )
        ttk.Button(action_row, text="上移", command=lambda: self._move_selected_custom_asset(-1)).pack(
            side="left", expand=True, fill="x", padx=3
        )
        ttk.Button(action_row, text="下移", command=lambda: self._move_selected_custom_asset(1)).pack(
            side="left", expand=True, fill="x", padx=3
        )
        ttk.Button(action_row, text="删除", command=self._delete_selected_custom_asset).pack(
            side="left", expand=True, fill="x", padx=(3, 0)
        )
        enable_row = ttk.Frame(parent)
        enable_row.pack(fill="x", pady=(0, 8))
        ttk.Checkbutton(
            enable_row,
            text="启用选中",
            variable=self.custom_item_enabled_var,
            command=self._on_custom_item_setting_changed,
        ).pack(anchor="w")

        self.custom_editor = ttk.Frame(parent)
        self.custom_editor.pack(fill="x")
        ttk.Label(self.custom_editor, textvariable=self.custom_item_name_var, foreground="#5b4636").pack(anchor="w")
        preset_row = ttk.Frame(self.custom_editor)
        preset_row.pack(fill="x", pady=(8, 0))
        ttk.Label(preset_row, text="资源预设").pack(side="left")
        ttk.Button(preset_row, text="应用", command=self._apply_custom_preset).pack(side="right")
        ttk.OptionMenu(
            preset_row,
            self.custom_preset_var,
            self.custom_preset_var.get(),
            *CUSTOM_RESOURCE_PRESETS.keys(),
        ).pack(side="right", padx=(0, 8))
        self._add_custom_slider(
            self.custom_editor,
            "显示大小",
            self.custom_item_size_var,
            36,
            320,
            self.custom_item_size_text,
        )
        self._add_custom_slider(
            self.custom_editor,
            "绳子长度",
            self.custom_item_rope_length_var,
            20,
            260,
            self.custom_item_rope_length_text,
        )
        self._add_custom_slider(
            self.custom_editor,
            "绳子粗细",
            self.custom_item_rope_width_var,
            1,
            12,
            self.custom_item_rope_width_text,
        )
        color_row = ttk.Frame(self.custom_editor)
        color_row.pack(fill="x", pady=(8, 0))
        ttk.Label(color_row, text="绳子颜色").pack(side="left")
        self.custom_color_swatch = tk.Canvas(
            color_row,
            width=24,
            height=16,
            highlightthickness=1,
            highlightbackground="#b8aca2",
        )
        self.custom_color_swatch_rect = self.custom_color_swatch.create_rectangle(0, 0, 24, 16, outline="")
        self.custom_color_swatch.pack(side="right", padx=(8, 0))
        ttk.OptionMenu(
            color_row,
            self.custom_item_rope_color_var,
            self.custom_item_rope_color_var.get(),
            *ROPE_COLORS.keys(),
            command=lambda _value: self._on_custom_rope_color_changed(),
        ).pack(side="right")
        self.custom_color_button = ttk.Button(
            self.custom_editor,
            text="选择自定义颜色",
            command=self._choose_custom_rope_color,
        )
        self.custom_color_button.pack(fill="x", pady=(6, 0))
        self._add_custom_slider(
            self.custom_editor,
            "动画播放速度",
            self.custom_item_anim_speed_var,
            0.2,
            4.0,
            self.custom_item_anim_speed_text,
        )
        self._add_custom_slider(
            self.custom_editor,
            "动画触发概率",
            self.custom_item_probability_var,
            0,
            100,
            self.custom_item_probability_text,
        )
        self._add_custom_slider(
            self.custom_editor,
            "碰撞体积",
            self.custom_item_collision_var,
            8,
            180,
            self.custom_item_collision_text,
        )
        self._add_custom_slider(
            self.custom_editor,
            "重量感",
            self.custom_item_weight_var,
            0,
            100,
            self.custom_item_weight_text,
        )
        ttk.Checkbutton(
            self.custom_editor,
            text="GIF 连续播放",
            variable=self.custom_item_always_animate_var,
            command=self._on_custom_item_setting_changed,
        ).pack(anchor="w", pady=(8, 0))
        ttk.Checkbutton(
            self.custom_editor,
            text="GIF 往返循环",
            variable=self.custom_item_reverse_loop_var,
            command=self._on_custom_item_setting_changed,
        ).pack(anchor="w", pady=(4, 0))
        self.custom_global_section = ttk.Frame(parent)
        self.custom_global_section.pack(fill="x", pady=(10, 0))
        ttk.Label(self.custom_global_section, text="全局设置", foreground="#5b4636").pack(anchor="w")
        ttk.Checkbutton(
            self.custom_global_section,
            text="资源相互碰撞",
            variable=self.custom_collision_var,
            command=self._on_custom_collision_changed,
        ).pack(anchor="w", pady=(8, 0))
        self._add_custom_slider(
            self.custom_global_section,
            "触发间隔",
            self.trigger_interval_var,
            1.0,
            20.0,
            self.trigger_interval_text,
            self._on_setting_changed,
        )
        self._add_custom_slider(
            self.custom_global_section,
            "绑定点横向",
            self.anchor_x_var,
            -30,
            80,
            self.anchor_x_text,
            self._on_setting_changed,
        )
        self._add_custom_slider(
            self.custom_global_section,
            "绑定点纵向",
            self.anchor_y_var,
            -20,
            90,
            self.anchor_y_text,
            self._on_setting_changed,
        )
        self.custom_status_label = ttk.Label(
            parent,
            textvariable=self.custom_status_var,
            foreground="#8a6a43",
            justify="left",
            wraplength=320,
        )
        self.custom_status_label.pack(fill="x", pady=(8, 0))
        parent.bind("<Configure>", self._on_custom_panel_configure, add="+")

    def _build_overlay(self) -> None:
        self.overlay = AlphaOverlay(APP_TITLE)
        self.tray_icon = SystemTrayIcon(
            self.root,
            _resource_path(ICON_NAME),
            self.restore_from_background,
            self.toggle_pet_from_tray,
            self.quit_app,
            lambda: self.running,
        )

    def _setting_float(self, name: str, default: float, minimum: float, maximum: float) -> float:
        return _clamp(self.settings.get(name), minimum, maximum, default)

    def _setting_bool(self, name: str, default: bool) -> bool:
        value = self.settings.get(name)
        return value if isinstance(value, bool) else default

    def _setting_mode(self, name: str, default: str) -> str:
        value = self.settings.get(name)
        return value if isinstance(value, str) and value in PERFORMANCE_PROFILES else default

    def _setting_connection_mode(self, name: str, default: str) -> str:
        value = self.settings.get(name)
        return value if isinstance(value, str) and value in CUSTOM_CONNECTION_MODES else default

    def _setting_rope_color(self, name: str, default: str) -> str:
        value = self.settings.get(name)
        return value if isinstance(value, str) and value in ROPE_COLORS else default

    def _setting_hex_color(self, name: str, default: str) -> str:
        value = self.settings.get(name)
        return value if isinstance(value, str) and _is_hex_color(value) else default

    def _setting_assets_dir(self, name: str) -> str:
        value = self.settings.get(name)
        if isinstance(value, str) and value.strip():
            return value
        return str(_default_assets_dir())

    def _load_custom_assets(self) -> list[CustomAssetConfig]:
        raw_assets = self.settings.get("custom_assets")
        if not isinstance(raw_assets, list):
            return []
        assets: list[CustomAssetConfig] = []
        seen_ids: set[str] = set()
        for raw_asset in raw_assets:
            asset = CustomAssetConfig.from_dict(raw_asset)
            if asset is None:
                continue
            if asset.asset_id in seen_ids:
                asset.asset_id = uuid.uuid4().hex
            seen_ids.add(asset.asset_id)
            assets.append(asset)
        return assets

    def _on_setting_changed(self) -> None:
        self._sync_slider_labels()
        self._schedule_save_settings()

    def _schedule_save_settings(self) -> None:
        if self.save_after_id is not None:
            try:
                self.root.after_cancel(self.save_after_id)
            except tk.TclError:
                pass
        self.save_after_id = self.root.after(400, self._save_settings)

    def _save_settings(self) -> None:
        self.save_after_id = None
        data = {
            "version": SETTINGS_VERSION,
            "size": self.size_var.get(),
            "probability": self.prob_var.get(),
            "anchor_x": self.anchor_x_var.get(),
            "anchor_y": self.anchor_y_var.get(),
            "anim_speed": self.anim_speed_var.get(),
            "trigger_interval": self.trigger_interval_var.get(),
            "weight": self.weight_var.get(),
            "rope_length": self.rope_length_var.get(),
            "rope_width": self.rope_width_var.get(),
            "performance_mode": self.performance_mode_var.get(),
            "absolute_binding": self.absolute_binding_var.get(),
            "background": self.background_var.get(),
            "start_with_windows": self.start_with_windows_var.get(),
            "custom_mode": self.custom_mode_var.get(),
            "custom_include_pig": self.custom_include_pig_var.get(),
            "custom_pig_rope_color": self.custom_pig_rope_color_var.get(),
            "custom_pig_custom_rope_color": self.custom_pig_custom_rope_color_var.get(),
            "custom_connection": self.custom_connection_var.get(),
            "custom_collision": self.custom_collision_var.get(),
            "custom_assets_dir": self.custom_assets_dir_var.get(),
            "custom_assets": [asset.to_dict() for asset in self.custom_assets],
        }
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            self.settings_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _sync_slider_labels(self) -> None:
        self.size_text.set(f"{int(self.size_var.get())} px")
        self.prob_text.set(f"{int(self.prob_var.get())}%")
        self.anchor_x_text.set(f"{int(self.anchor_x_var.get()):+d} px")
        self.anchor_y_text.set(f"{int(self.anchor_y_var.get()):+d} px")
        self.rope_length_text.set(f"{int(self.rope_length_var.get())} px")
        self.rope_width_text.set(f"{self.rope_width_var.get():.1f} px")
        self.weight_text.set(f"{int(self.weight_var.get())}%")
        self.anim_speed_text.set(f"{self.anim_speed_var.get():.1f}x")
        self.trigger_interval_text.set(f"{self.trigger_interval_var.get():.0f} s")
        self.renderer.cache_limit = self._current_performance_profile().texture_cache_limit
        self._sync_custom_editor_labels()
        self._sync_custom_assets_dir_text()
        custom_cache_limit = max(32, self._current_performance_profile().texture_cache_limit // max(2, len(self.custom_renderers) or 2))
        for renderer in self.custom_renderers.values():
            renderer.cache_limit = custom_cache_limit

    def _sync_custom_editor_labels(self) -> None:
        self.custom_item_size_text.set(f"{int(self.custom_item_size_var.get())} px")
        self.custom_item_rope_length_text.set(f"{int(self.custom_item_rope_length_var.get())} px")
        self.custom_item_anim_speed_text.set(f"{self.custom_item_anim_speed_var.get():.1f}x")
        self.custom_item_probability_text.set(f"{int(self.custom_item_probability_var.get())}%")
        self.custom_item_collision_text.set(f"{int(self.custom_item_collision_var.get())} px")
        self.custom_item_weight_text.set(f"{int(self.custom_item_weight_var.get())}%")
        self.custom_item_rope_width_text.set(f"{self.custom_item_rope_width_var.get():.1f} px")
        self.custom_item_attach_x_text.set(f"{int(self.custom_item_attach_x_var.get())}%")
        self.custom_item_attach_y_text.set(f"{int(self.custom_item_attach_y_var.get())}%")
        try:
            color_is_custom = self.custom_item_rope_color_var.get() == "自定义"
            self.custom_color_button.state(["!disabled"] if color_is_custom else ["disabled"])
        except AttributeError:
            pass
        self._sync_custom_color_swatch()
        self._sync_custom_status_wrap()

    def _on_custom_panel_configure(self, event: tk.Event) -> None:
        self._sync_custom_status_wrap(event.width)

    def _sync_custom_status_wrap(self, width: int | None = None) -> None:
        if self.custom_status_label is None:
            return
        panel_width = width if width is not None else self.custom_section.winfo_width()
        wrap = max(240, min(520, panel_width - 24))
        self.custom_status_label.configure(wraplength=wrap)

    def _sync_custom_assets_dir_text(self) -> None:
        path = self.custom_assets_dir_var.get()
        if len(path) > 34:
            path = "..." + path[-31:]
        self.custom_assets_dir_text.set(path)

    def _custom_rope_hex(self, rope_color: str, custom_color: str) -> str:
        color = custom_color if rope_color == "自定义" else ROPE_COLORS.get(rope_color, "#744d2d")
        return color if _is_hex_color(color) else "#744d2d"

    def _sync_custom_color_swatch(self) -> None:
        if self.custom_color_swatch is None or self.custom_color_swatch_rect is None:
            return
        asset = self._selected_custom_asset()
        custom_color = "#744d2d"
        if asset is not None:
            custom_color = asset.custom_rope_color
        if asset is not None and asset.asset_id == DEFAULT_PIG_CUSTOM_ID:
            custom_color = self.custom_pig_custom_rope_color_var.get()
        color = self._custom_rope_hex(self.custom_item_rope_color_var.get(), custom_color)
        self.custom_color_swatch.itemconfigure(self.custom_color_swatch_rect, fill=color)

    def _default_pig_custom_asset(self) -> CustomAssetConfig:
        return CustomAssetConfig(
            asset_id=DEFAULT_PIG_CUSTOM_ID,
            name="猪猪（默认）",
            path=GIF_NAME,
            enabled=True,
            size=float(self.size_var.get()),
            rope_length=float(self.rope_length_var.get()),
            rope_color=self.custom_pig_rope_color_var.get(),
            custom_rope_color=self.custom_pig_custom_rope_color_var.get(),
            anim_speed=float(self.anim_speed_var.get()),
            probability=float(self.prob_var.get()),
            collision_radius=max(24.0, float(self.size_var.get()) * 0.32),
            weight=float(self.weight_var.get()),
            reverse_loop=True,
            rope_width=float(self.rope_width_var.get()),
        )

    def _custom_asset_choices(self) -> list[CustomAssetConfig]:
        assets: list[CustomAssetConfig] = []
        if self.custom_include_pig_var.get():
            assets.append(self._default_pig_custom_asset())
        assets.extend(self.custom_assets)
        return assets

    def _uploaded_custom_assets(self) -> list[CustomAssetConfig]:
        return [asset for asset in self.custom_assets if asset.enabled and Path(asset.path).exists()]

    def _active_custom_assets(self) -> list[CustomAssetConfig]:
        assets: list[CustomAssetConfig] = []
        if self.custom_include_pig_var.get():
            assets.append(self._default_pig_custom_asset())
        assets.extend(self._uploaded_custom_assets())
        return assets

    def _selected_custom_asset(self) -> CustomAssetConfig | None:
        selected_id = self.custom_selected_id.get()
        for asset in self._custom_asset_choices():
            if asset.asset_id == selected_id:
                return asset
        return None

    def _selected_custom_assets(self) -> list[CustomAssetConfig]:
        selected_ids = set(self.custom_selected_ids)
        if not selected_ids and self.custom_selected_id.get():
            selected_ids.add(self.custom_selected_id.get())
        choices = self._custom_asset_choices()
        return [asset for asset in choices if asset.asset_id in selected_ids]

    def _refresh_custom_panel(self) -> None:
        if self.custom_mode_var.get():
            self.default_settings_section.pack_forget()
            self.custom_attach_section.pack(fill="x", pady=(0, 14), before=self.status_separator)
            self.custom_section.pack(fill="x", pady=(14, 0), before=self.status_separator)
        else:
            self.custom_attach_section.pack_forget()
            self.custom_section.pack_forget()
            self.default_settings_section.pack(fill="x", before=self.status_separator)
        self._refresh_custom_asset_list()
        self._sync_custom_assets_dir_text()
        self._load_selected_custom_asset_to_editor()
        self._sync_custom_status()

    def _refresh_custom_asset_list(self) -> None:
        self.custom_listbox.delete(0, tk.END)
        selected_index = None
        choices = self._custom_asset_choices()
        selected_ids = set(self.custom_selected_ids)
        if not selected_ids and self.custom_selected_id.get():
            selected_ids.add(self.custom_selected_id.get())
        for index, asset in enumerate(choices):
            marker = "✓" if asset.enabled else " "
            missing = "" if asset.asset_id == DEFAULT_PIG_CUSTOM_ID or Path(asset.path).exists() else "（文件缺失）"
            self.custom_listbox.insert(tk.END, f"{index + 1}. [{marker}] {asset.name}{missing}")
            if asset.asset_id in selected_ids:
                self.custom_listbox.selection_set(index)
            if asset.asset_id == self.custom_selected_id.get():
                selected_index = index
        if selected_index is None and choices:
            selected_index = 0
            self.custom_selected_id.set(choices[0].asset_id)
            self.custom_selected_ids = {choices[0].asset_id}
        if selected_index is not None:
            self.custom_listbox.selection_set(selected_index)
            self.custom_listbox.activate(selected_index)

    def _load_selected_custom_asset_to_editor(self) -> None:
        asset = self._selected_custom_asset()
        self.custom_syncing_ui = True
        try:
            if asset is None:
                self.custom_item_name_var.set("未选择资源")
                self.custom_item_enabled_var.set(False)
                self.custom_item_attach_mode_var.set(CUSTOM_ATTACH_AUTO)
                self.custom_item_attach_x_var.set(50)
                self.custom_item_attach_y_var.set(0)
                self.custom_item_always_animate_var.set(False)
                self.custom_item_rope_width_var.set(3)
                return
            selected_count = len(self._selected_custom_assets())
            if selected_count > 1:
                self.custom_item_name_var.set(f"已选 {selected_count} 个资源（以 {asset.name} 为模板）")
            else:
                self.custom_item_name_var.set(asset.name)
            self.custom_item_enabled_var.set(asset.enabled)
            self.custom_item_size_var.set(asset.size)
            self.custom_item_rope_length_var.set(asset.rope_length)
            self.custom_item_rope_color_var.set(asset.rope_color)
            self.custom_item_anim_speed_var.set(asset.anim_speed)
            self.custom_item_probability_var.set(asset.probability)
            self.custom_item_collision_var.set(asset.collision_radius)
            self.custom_item_weight_var.set(asset.weight)
            self.custom_item_reverse_loop_var.set(asset.reverse_loop)
            self.custom_item_attach_mode_var.set(asset.attach_mode)
            self.custom_item_attach_x_var.set(asset.attach_x)
            self.custom_item_attach_y_var.set(asset.attach_y)
            self.custom_item_always_animate_var.set(asset.always_animate)
            self.custom_item_rope_width_var.set(asset.rope_width)
        finally:
            self.custom_syncing_ui = False
            self._sync_custom_editor_labels()

    def _sync_custom_status(self) -> None:
        active_assets = self._active_custom_assets()
        active_count = len(active_assets)
        uploaded_total = len(self.custom_assets)
        uploaded_active = len(self._uploaded_custom_assets())
        pig_text = "，猪猪参与" if self.custom_include_pig_var.get() else ""
        if not self.custom_mode_var.get():
            self.custom_status_var.set("")
        elif active_count == 0:
            self.custom_status_var.set("自定义模式开启后，默认猪猪不会显示；请添加图片/GIF，或勾选“猪猪也参与”。")
        else:
            base = f"已添加 {uploaded_total} 个上传资源，启用 {uploaded_active} 个{pig_text}。"
            notes = self._custom_performance_notes(active_assets)
            if notes:
                base += " 提醒：" + "；".join(notes[:2]) + "。"
            self.custom_status_var.set(base)
        self._update_buttons()

    def _custom_performance_notes(self, active_assets: list[CustomAssetConfig]) -> list[str]:
        notes: list[str] = []
        active_count = len(active_assets)
        if active_count >= 12:
            notes.append("资源很多，可暂停一部分")
        elif active_count >= 7:
            notes.append("资源偏多，绘制压力会上升")

        total_area = sum(asset.size * asset.size for asset in active_assets)
        if total_area >= 260_000:
            notes.append("总面积很大，缩小会更稳")
        elif total_area >= 150_000:
            notes.append("总显示面积偏大")

        frame_counts = [self._custom_asset_frame_count(asset) for asset in active_assets]
        total_frames = sum(frame_counts)
        gif_count = sum(1 for count in frame_counts if count > 1)
        if total_frames >= 180:
            notes.append("GIF 帧数多，缓存占用会增加")
        elif gif_count >= 4:
            notes.append("GIF 较多，触发过密会显得卡")

        if self.custom_collision_var.get():
            collision_pairs = active_count * (active_count - 1) // 2
            if collision_pairs >= 45:
                notes.append("碰撞计算多，可关闭碰撞")
            elif collision_pairs >= 21:
                notes.append("碰撞对象较多，关闭碰撞会更省")
        elif active_count >= 2:
            notes.append("资源碰撞已关闭，会更省但可能互相穿过")

        high_probability = sum(1 for asset in active_assets if asset.probability >= 60 and self._custom_asset_frame_count(asset) > 1)
        if high_probability >= 3:
            notes.append("多个 GIF 触发概率很高，建议拉开触发间隔")
        return notes

    def _on_custom_mode_changed(self) -> None:
        if self.custom_mode_var.get() and self.running:
            self._place_physics_at_cursor()
        self._refresh_custom_panel()
        self._schedule_save_settings()

    def _on_custom_include_pig_changed(self) -> None:
        if self.custom_include_pig_var.get():
            self.custom_selected_id.set(DEFAULT_PIG_CUSTOM_ID)
            self.custom_selected_ids = {DEFAULT_PIG_CUSTOM_ID}
        elif self.custom_selected_id.get() == DEFAULT_PIG_CUSTOM_ID:
            self.custom_selected_id.set(self.custom_assets[0].asset_id if self.custom_assets else "")
            self.custom_selected_ids = {self.custom_selected_id.get()} if self.custom_selected_id.get() else set()
        if self.running:
            self._place_custom_physics_at_cursor()
        self._refresh_custom_panel()
        self._schedule_save_settings()

    def _on_custom_connection_changed(self) -> None:
        if self.running:
            self._place_custom_physics_at_cursor()
        self._sync_custom_status()
        self._schedule_save_settings()

    def _on_custom_collision_changed(self) -> None:
        self._sync_custom_status()
        self._schedule_save_settings()

    def _on_custom_attach_mode_changed(self) -> None:
        if self.custom_item_attach_mode_var.get() == CUSTOM_ATTACH_FIXED:
            self._set_attach_point_from_current_auto_joint()
        self._on_custom_item_setting_changed()

    def _on_custom_attach_slider_changed(self) -> None:
        if not self.custom_syncing_ui:
            self.custom_item_attach_mode_var.set(CUSTOM_ATTACH_FIXED)
        self._on_custom_item_setting_changed()

    def _on_custom_selection_changed(self, _event: tk.Event | None = None) -> None:
        selection = self.custom_listbox.curselection()
        if not selection:
            self.custom_selected_ids.clear()
            return
        choices = self._custom_asset_choices()
        selected_indices = [int(index) for index in selection if 0 <= int(index) < len(choices)]
        self.custom_selected_ids = {choices[index].asset_id for index in selected_indices}
        active_index = self.custom_listbox.index("active")
        if active_index not in selected_indices:
            active_index = selected_indices[-1]
        if 0 <= active_index < len(choices):
            self.custom_selected_id.set(choices[active_index].asset_id)
        self._load_selected_custom_asset_to_editor()

    def _uploaded_custom_asset_index(self, asset_id: str) -> int | None:
        for index, asset in enumerate(self.custom_assets):
            if asset.asset_id == asset_id:
                return index
        return None

    def _rename_selected_custom_asset(self) -> None:
        asset = self._selected_custom_asset()
        if asset is None:
            return
        if asset.asset_id == DEFAULT_PIG_CUSTOM_ID:
            messagebox.showinfo("不能重命名", "默认猪猪的名称是固定的。")
            return
        new_name = simpledialog.askstring(
            "重命名资源",
            "输入新的资源名称：",
            initialvalue=asset.name,
            parent=self.root,
        )
        if new_name is None:
            return
        new_name = new_name.strip()
        if not new_name:
            messagebox.showinfo("名称为空", "资源名称不能为空。")
            return
        asset.name = new_name
        self._refresh_custom_panel()
        self._schedule_save_settings()

    def _move_selected_custom_asset(self, direction: int) -> None:
        asset = self._selected_custom_asset()
        if asset is None or asset.asset_id == DEFAULT_PIG_CUSTOM_ID:
            return
        index = self._uploaded_custom_asset_index(asset.asset_id)
        if index is None:
            return
        new_index = index + direction
        if new_index < 0 or new_index >= len(self.custom_assets):
            return
        self.custom_assets[index], self.custom_assets[new_index] = self.custom_assets[new_index], self.custom_assets[index]
        self.custom_selected_id.set(asset.asset_id)
        self.custom_selected_ids = {asset.asset_id}
        if self.running:
            self._place_custom_physics_at_cursor()
        self._refresh_custom_panel()
        self._schedule_save_settings()

    def _enable_all_custom_assets(self) -> None:
        if not self.custom_assets:
            messagebox.showinfo("没有上传资源", "还没有添加图片或 GIF。")
            return
        for asset in self.custom_assets:
            asset.enabled = True
        if self.running:
            self._place_custom_physics_at_cursor()
        self._refresh_custom_panel()
        self._schedule_save_settings()

    def _pause_all_custom_assets(self) -> None:
        for asset in self.custom_assets:
            asset.enabled = False
        self.custom_include_pig_var.set(False)
        self.custom_selected_id.set(self.custom_assets[0].asset_id if self.custom_assets else "")
        self.custom_selected_ids = {self.custom_selected_id.get()} if self.custom_selected_id.get() else set()
        if self.running:
            self.custom_states.clear()
        self._refresh_custom_panel()
        self._schedule_save_settings()

    def _clear_uploaded_custom_assets(self) -> None:
        if not self.custom_assets:
            messagebox.showinfo("没有上传资源", "当前列表里没有上传资源。")
            return
        confirmed = messagebox.askyesno(
            "清空上传资源",
            "这会从列表中移除所有上传资源，但不会删除磁盘上的原文件或已复制文件。继续吗？",
            parent=self.root,
        )
        if not confirmed:
            return
        uploaded_ids = {asset.asset_id for asset in self.custom_assets}
        self.custom_assets = []
        for asset_id in uploaded_ids:
            self.custom_renderers.pop(asset_id, None)
            self.custom_states.pop(asset_id, None)
        self.custom_selected_id.set(DEFAULT_PIG_CUSTOM_ID if self.custom_include_pig_var.get() else "")
        self.custom_selected_ids = {self.custom_selected_id.get()} if self.custom_selected_id.get() else set()
        self._refresh_custom_panel()
        self._schedule_save_settings()

    def _apply_custom_preset(self) -> None:
        asset = self._selected_custom_asset()
        if asset is None:
            return
        preset = CUSTOM_RESOURCE_PRESETS.get(self.custom_preset_var.get())
        if preset is None:
            return
        self.custom_item_size_var.set(float(preset["size"]))
        self.custom_item_rope_length_var.set(float(preset["rope_length"]))
        self.custom_item_anim_speed_var.set(float(preset["anim_speed"]))
        self.custom_item_probability_var.set(float(preset["probability"]))
        self.custom_item_collision_var.set(float(preset["collision_radius"]))
        self.custom_item_weight_var.set(float(preset["weight"]))
        connection = preset.get("connection")
        if isinstance(connection, str) and connection in CUSTOM_CONNECTION_MODES:
            self.custom_connection_var.set(connection)
            self._on_custom_connection_changed()
        self._on_custom_item_setting_changed()

    def _set_attach_point_from_current_auto_joint(self) -> None:
        asset = self._selected_custom_asset()
        if asset is None or asset.asset_id == DEFAULT_PIG_CUSTOM_ID:
            return
        renderer = self._custom_renderer(asset)
        if renderer is None or not renderer.frames:
            return
        frame = renderer.frames[0]
        joint = renderer.joints[0]
        if frame.width <= 0 or frame.height <= 0:
            return
        self.custom_item_attach_x_var.set(_clamp(joint[0] / frame.width * 100.0, 0, 100, 50))
        self.custom_item_attach_y_var.set(_clamp(joint[1] / frame.height * 100.0, 0, 100, 0))

    def _on_custom_item_setting_changed(self) -> None:
        if self.custom_syncing_ui:
            return
        asset = self._selected_custom_asset()
        if asset is None:
            return
        selected_assets = self._selected_custom_assets() or [asset]
        update_default_pig = any(item.asset_id == DEFAULT_PIG_CUSTOM_ID for item in selected_assets)

        if update_default_pig:
            self.size_var.set(_clamp(self.custom_item_size_var.get(), 70, 260, 150))
            self.rope_length_var.set(_clamp(self.custom_item_rope_length_var.get(), 36, 160, 72))
            self.rope_width_var.set(_clamp(self.custom_item_rope_width_var.get(), 1, 12, 4))
            self.anim_speed_var.set(_clamp(self.custom_item_anim_speed_var.get(), 0.5, 3.0, 1.6))
            self.prob_var.set(_clamp(self.custom_item_probability_var.get(), 0, 100, 15))
            self.weight_var.set(_clamp(self.custom_item_weight_var.get(), 0, 100, 70))
            rope_color = self.custom_item_rope_color_var.get()
            self.custom_pig_rope_color_var.set(rope_color if rope_color in ROPE_COLORS else "棕色")
            self.custom_include_pig_var.set(self.custom_item_enabled_var.get())
            self._sync_slider_labels()

        for target in selected_assets:
            if target.asset_id == DEFAULT_PIG_CUSTOM_ID:
                continue
            target.enabled = self.custom_item_enabled_var.get()
            target.size = _clamp(self.custom_item_size_var.get(), 36, 320, 130)
            target.rope_length = _clamp(self.custom_item_rope_length_var.get(), 20, 260, 72)
            target.rope_color = self.custom_item_rope_color_var.get() if self.custom_item_rope_color_var.get() in ROPE_COLORS else "棕色"
            target.anim_speed = _clamp(self.custom_item_anim_speed_var.get(), 0.2, 4.0, 1.0)
            target.probability = _clamp(self.custom_item_probability_var.get(), 0, 100, 10)
            target.collision_radius = _clamp(self.custom_item_collision_var.get(), 8, 180, 46)
            target.weight = _clamp(self.custom_item_weight_var.get(), 0, 100, 70)
            target.reverse_loop = self.custom_item_reverse_loop_var.get()
            target.always_animate = self.custom_item_always_animate_var.get()
            target.rope_width = _clamp(self.custom_item_rope_width_var.get(), 1, 12, 3)
            old_attach = (target.attach_mode, round(target.attach_x, 2), round(target.attach_y, 2))
            attach_mode = self.custom_item_attach_mode_var.get()
            target.attach_mode = attach_mode if attach_mode in CUSTOM_ATTACH_MODES else CUSTOM_ATTACH_AUTO
            target.attach_x = _clamp(self.custom_item_attach_x_var.get(), 0, 100, 50)
            target.attach_y = _clamp(self.custom_item_attach_y_var.get(), 0, 100, 0)
            new_attach = (target.attach_mode, round(target.attach_x, 2), round(target.attach_y, 2))
            if old_attach != new_attach:
                self._clear_custom_renderer_cache(target.asset_id)

        if self.running:
            self._place_custom_physics_at_cursor()
        self._sync_custom_editor_labels()
        self._refresh_custom_asset_list()
        self._sync_custom_status()
        self._schedule_save_settings()

    def _on_custom_rope_color_changed(self) -> None:
        self._on_custom_item_setting_changed()

    def _choose_custom_rope_color(self) -> None:
        asset = self._selected_custom_asset()
        if asset is None:
            return
        initial_color = asset.custom_rope_color if _is_hex_color(asset.custom_rope_color) else "#744d2d"
        _rgb, color = colorchooser.askcolor(color=initial_color, parent=self.root, title="选择绳子颜色")
        if isinstance(color, str) and _is_hex_color(color):
            if asset.asset_id == DEFAULT_PIG_CUSTOM_ID:
                self.custom_pig_custom_rope_color_var.set(color)
                self.custom_item_rope_color_var.set("自定义")
                self.custom_pig_rope_color_var.set("自定义")
                self._on_custom_item_setting_changed()
                return
            for target in self._selected_custom_assets() or [asset]:
                if target.asset_id != DEFAULT_PIG_CUSTOM_ID:
                    target.custom_rope_color = color
            self.custom_item_rope_color_var.set("自定义")
            self._on_custom_item_setting_changed()

    def _choose_custom_assets_dir(self) -> None:
        current = Path(self.custom_assets_dir_var.get())
        initialdir = str(current if current.exists() else _default_assets_dir())
        directory = filedialog.askdirectory(parent=self.root, title="选择自定义素材保存位置", initialdir=initialdir)
        if not directory:
            return
        target_dir = Path(directory).expanduser()
        try:
            same_dir = current.expanduser().resolve() == target_dir.resolve()
        except Exception:
            same_dir = str(current) == str(target_dir)
        if same_dir:
            self.custom_assets_dir_var.set(str(target_dir))
            self._sync_custom_assets_dir_text()
            self._schedule_save_settings()
            return
        migrate_assets = False
        if self.custom_assets:
            answer = messagebox.askyesnocancel(
                "迁移保存目录",
                "要把当前列表里的已复制素材移动到新保存位置吗？\n\n选择“否”只会让之后新增的素材保存到新位置。",
                parent=self.root,
            )
            if answer is None:
                return
            migrate_assets = bool(answer)
        if migrate_assets:
            if not self._migrate_custom_assets_dir(target_dir):
                return
        else:
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
            except Exception as exc:
                messagebox.showerror("无法创建保存位置", f"请换一个保存位置：\n{exc}", parent=self.root)
                return
        self.custom_assets_dir_var.set(str(target_dir))
        self._sync_custom_assets_dir_text()
        self._refresh_custom_panel()
        self._schedule_save_settings()

    def _migrate_custom_assets_dir(self, target_dir: Path) -> bool:
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            messagebox.showerror("无法创建保存位置", f"请换一个保存位置：\n{exc}", parent=self.root)
            return False
        moved = 0
        missing = 0
        failed = 0
        try:
            target_resolved = target_dir.resolve()
        except Exception:
            target_resolved = target_dir
        for asset in self.custom_assets:
            source = Path(asset.path).expanduser()
            if not source.exists():
                missing += 1
                continue
            try:
                if source.resolve().parent == target_resolved:
                    continue
                target = _unique_asset_path(target_dir, source.name)
                shutil.move(str(source), str(target))
                asset.path = str(target)
                self.custom_renderers.pop(asset.asset_id, None)
                moved += 1
            except Exception:
                failed += 1
        if self.running:
            self._place_custom_physics_at_cursor()
        if missing or failed:
            messagebox.showwarning(
                "目录迁移完成",
                f"已迁移 {moved} 个资源；缺失 {missing} 个，失败 {failed} 个。缺失或失败的资源仍保留原路径。",
                parent=self.root,
            )
        return True

    def _add_custom_assets(self) -> None:
        filetypes = (
            ("图片和 GIF", "*.gif *.png *.jpg *.jpeg *.webp *.bmp"),
            ("所有文件", "*.*"),
        )
        paths = filedialog.askopenfilenames(parent=self.root, title="选择图片或 GIF", filetypes=filetypes)
        if not paths:
            return
        target_dir = Path(self.custom_assets_dir_var.get()).expanduser()
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            messagebox.showerror("无法创建保存位置", f"请换一个保存位置：\n{exc}")
            return

        added = 0
        skipped = 0
        for raw_path in paths:
            source = Path(raw_path)
            if source.suffix.lower() not in CUSTOM_ASSET_SUFFIXES:
                skipped += 1
                continue
            asset_id = uuid.uuid4().hex
            safe_stem = _safe_asset_name(source.stem)
            target = target_dir / f"{safe_stem}_{asset_id[:8]}{source.suffix.lower()}"
            try:
                shutil.copy2(source, target)
                renderer = CustomAssetRenderer(target, self.root)
            except Exception as exc:
                skipped += 1
                messagebox.showwarning("素材添加失败", f"{source.name}\n{exc}")
                continue
            self.custom_renderers[asset_id] = renderer
            self.custom_assets.append(
                CustomAssetConfig(
                    asset_id=asset_id,
                    name=source.name,
                    path=str(target),
                    size=float(self.size_var.get()),
                    rope_length=float(self.rope_length_var.get()),
                    probability=float(self.prob_var.get()),
                    anim_speed=float(self.anim_speed_var.get()),
                    weight=float(self.weight_var.get()),
                    rope_width=float(self.rope_width_var.get()),
                    always_animate=source.suffix.lower() == ".gif",
                )
            )
            self.custom_selected_id.set(asset_id)
            self.custom_selected_ids = {asset_id}
            added += 1
        if skipped and not added:
            messagebox.showinfo("没有添加素材", "请选择 gif、png、jpg、jpeg、webp 或 bmp 文件。")
        self._refresh_custom_panel()
        self._schedule_save_settings()

    def _delete_selected_custom_asset(self) -> None:
        asset = self._selected_custom_asset()
        if asset is None:
            return
        if asset.asset_id == DEFAULT_PIG_CUSTOM_ID:
            self.custom_include_pig_var.set(False)
            self.custom_selected_id.set(self.custom_assets[0].asset_id if self.custom_assets else "")
            self.custom_selected_ids = {self.custom_selected_id.get()} if self.custom_selected_id.get() else set()
            self.custom_states.pop(DEFAULT_PIG_CUSTOM_ID, None)
            self._refresh_custom_panel()
            self._schedule_save_settings()
            return
        self.custom_assets = [item for item in self.custom_assets if item.asset_id != asset.asset_id]
        self.custom_renderers.pop(asset.asset_id, None)
        self.custom_states.pop(asset.asset_id, None)
        if self.custom_assets:
            self.custom_selected_id.set(self.custom_assets[0].asset_id)
            self.custom_selected_ids = {self.custom_assets[0].asset_id}
        else:
            self.custom_selected_id.set("")
            self.custom_selected_ids.clear()
        self._refresh_custom_panel()
        self._schedule_save_settings()

    def _custom_rope_rgba(self, config: CustomAssetConfig) -> tuple[int, int, int, int]:
        color = self._custom_rope_hex(config.rope_color, config.custom_rope_color)
        return (int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16), 245)

    def _current_performance_profile(self) -> PerformanceProfile:
        return _performance_profile(self.performance_mode_var.get())

    def _on_performance_mode_changed(self) -> None:
        self._sync_slider_labels()
        profile = self._current_performance_profile()
        self._set_timer_resolution(self.running and profile.high_resolution_timer)
        self._schedule_save_settings()

    def _on_startup_changed(self) -> None:
        enabled = self.start_with_windows_var.get()
        try:
            _set_startup_enabled(enabled)
        except Exception as exc:
            self.start_with_windows_var.set(_is_startup_enabled())
            messagebox.showerror("开机启动设置失败", f"无法修改开机启动：\n{exc}", parent=self.root)
            return
        self._schedule_save_settings()

    def _reset_default_settings(self) -> None:
        confirmed = messagebox.askyesno(
            "恢复默认设置",
            "会恢复显示、物理、性能、自定义开关和资源参数；已上传的资源列表与保存目录会保留。继续吗？",
            parent=self.root,
        )
        if not confirmed:
            return
        self.size_var.set(DEFAULT_GLOBAL_SETTINGS["size"])
        self.prob_var.set(DEFAULT_GLOBAL_SETTINGS["probability"])
        self.anchor_x_var.set(DEFAULT_GLOBAL_SETTINGS["anchor_x"])
        self.anchor_y_var.set(DEFAULT_GLOBAL_SETTINGS["anchor_y"])
        self.anim_speed_var.set(DEFAULT_GLOBAL_SETTINGS["anim_speed"])
        self.trigger_interval_var.set(DEFAULT_GLOBAL_SETTINGS["trigger_interval"])
        self.weight_var.set(DEFAULT_GLOBAL_SETTINGS["weight"])
        self.rope_length_var.set(DEFAULT_GLOBAL_SETTINGS["rope_length"])
        self.rope_width_var.set(DEFAULT_GLOBAL_SETTINGS["rope_width"])
        self.performance_mode_var.set(DEFAULT_GLOBAL_SETTINGS["performance_mode"])
        self.absolute_binding_var.set(DEFAULT_GLOBAL_SETTINGS["absolute_binding"])
        self.background_var.set(DEFAULT_GLOBAL_SETTINGS["background"])
        self.custom_mode_var.set(DEFAULT_GLOBAL_SETTINGS["custom_mode"])
        self.custom_include_pig_var.set(DEFAULT_GLOBAL_SETTINGS["custom_include_pig"])
        self.custom_connection_var.set(DEFAULT_GLOBAL_SETTINGS["custom_connection"])
        self.custom_collision_var.set(DEFAULT_GLOBAL_SETTINGS["custom_collision"])
        self.custom_pig_rope_color_var.set(DEFAULT_GLOBAL_SETTINGS["custom_pig_rope_color"])
        self.custom_pig_custom_rope_color_var.set(DEFAULT_GLOBAL_SETTINGS["custom_pig_custom_rope_color"])
        if self.start_with_windows_var.get():
            try:
                _set_startup_enabled(False)
            except Exception as exc:
                messagebox.showwarning("开机启动未关闭", f"无法关闭开机启动：\n{exc}", parent=self.root)
        self.start_with_windows_var.set(_is_startup_enabled())

        for asset in self.custom_assets:
            asset.enabled = bool(DEFAULT_CUSTOM_ASSET_SETTINGS["enabled"])
            asset.size = float(DEFAULT_CUSTOM_ASSET_SETTINGS["size"])
            asset.rope_length = float(DEFAULT_CUSTOM_ASSET_SETTINGS["rope_length"])
            asset.rope_color = str(DEFAULT_CUSTOM_ASSET_SETTINGS["rope_color"])
            asset.custom_rope_color = str(DEFAULT_CUSTOM_ASSET_SETTINGS["custom_rope_color"])
            asset.anim_speed = float(DEFAULT_CUSTOM_ASSET_SETTINGS["anim_speed"])
            asset.probability = float(DEFAULT_CUSTOM_ASSET_SETTINGS["probability"])
            asset.collision_radius = float(DEFAULT_CUSTOM_ASSET_SETTINGS["collision_radius"])
            asset.weight = float(DEFAULT_CUSTOM_ASSET_SETTINGS["weight"])
            asset.reverse_loop = bool(DEFAULT_CUSTOM_ASSET_SETTINGS["reverse_loop"])
            asset.attach_mode = str(DEFAULT_CUSTOM_ASSET_SETTINGS["attach_mode"])
            asset.attach_x = float(DEFAULT_CUSTOM_ASSET_SETTINGS["attach_x"])
            asset.attach_y = float(DEFAULT_CUSTOM_ASSET_SETTINGS["attach_y"])
            asset.always_animate = bool(DEFAULT_CUSTOM_ASSET_SETTINGS["always_animate"])
            asset.rope_width = float(DEFAULT_CUSTOM_ASSET_SETTINGS["rope_width"])

        self.custom_selected_id.set(self.custom_assets[0].asset_id if self.custom_assets else "")
        self.animation_active = False
        self.frame_index = 0
        self.frame_time_ms = 0.0
        self.custom_states.clear()
        self.cursor_guard.show()
        self.absolute_cursor_asset = None
        self._set_timer_resolution(self.running and self._current_performance_profile().high_resolution_timer)
        if self.running:
            self._place_physics_at_cursor()
        self._sync_slider_labels()
        self._refresh_custom_panel()
        self._schedule_save_settings()

    def _on_absolute_binding_changed(self) -> None:
        if self.running and self.absolute_binding_var.get():
            self._refresh_absolute_cursor_asset()
            self.cursor_guard.hide()
        else:
            self.cursor_guard.show()
            if not self.absolute_binding_var.get():
                self.absolute_cursor_asset = None
        self._update_buttons()
        self._schedule_save_settings()

    def _refresh_absolute_cursor_asset(self) -> None:
        self.absolute_cursor_asset = _capture_system_cursor()

    def _prepare_prewarm_jobs(self) -> None:
        sizes = [110, 150, 190]
        static_angles = list(range(-36, 37, 4))
        animation_angles = [-24, -12, 0, 12, 24]
        self.prewarm_jobs = [(0, size, angle) for size in sizes for angle in static_angles]
        self.prewarm_jobs.extend(
            (frame, size, angle)
            for size in sizes
            for frame in range(0, self.renderer.frame_count, 2)
            for angle in animation_angles
        )

    def _prewarm_one_asset(self) -> None:
        if not self.prewarm_jobs:
            return
        frame, size, angle = self.prewarm_jobs.pop(0)
        self.renderer.render_asset(frame, size, angle)

    def _prewarm_current_static_angles(self) -> None:
        size = int(self.size_var.get())
        profile = self._current_performance_profile()
        for angle in range(-44, 45, max(1, profile.angle_step * 2)):
            self.renderer.render_asset(0, size, angle, profile.angle_step)

    def _update_buttons(self) -> None:
        self.start_button.state(["disabled"] if self.running else ["!disabled"])
        self.stop_button.state(["!disabled"] if self.running else ["disabled"])
        self.hide_button.state(["!disabled"] if self.running else ["disabled"])
        mode = "自定义" if self.custom_mode_var.get() else "默认"
        binding = "绝对绑定" if self.absolute_binding_var.get() else "普通"
        backend = f"{mode} / {binding}"
        self.status_var.set(f"运行中：{backend}" if self.running else f"已关闭：{backend}")

    def _bind_mousewheel(self, _event: tk.Event) -> None:
        self.scroll_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.scroll_canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.scroll_canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _unbind_mousewheel(self, _event: tk.Event) -> None:
        self.scroll_canvas.unbind_all("<MouseWheel>")
        self.scroll_canvas.unbind_all("<Button-4>")
        self.scroll_canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event: tk.Event) -> None:
        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            delta = -1 if event.delta > 0 else 1
        self.scroll_canvas.yview_scroll(delta, "units")

    def trigger_animation_once(self) -> None:
        if self.custom_mode_var.get():
            for state in self.custom_states.values():
                state.animation_active = True
                state.frame_index = 0
                state.frame_time_ms = 0.0
                state.trigger_timer = 0.0
            return
        self.animation_active = True
        self.frame_index = 0
        self.frame_time_ms = 0.0
        self.trigger_timer = 0.0

    def start_pet(self) -> None:
        if self.running:
            return
        profile = self._current_performance_profile()
        self._set_timer_resolution(profile.high_resolution_timer)
        self.running = True
        self._prewarm_current_static_angles()
        self._place_physics_at_cursor()
        if self.overlay is not None:
            self.overlay.show()
        if self.absolute_binding_var.get():
            self._refresh_absolute_cursor_asset()
            self.cursor_guard.hide()
        self._update_buttons()

    def stop_pet(self) -> None:
        if not self.running:
            return
        self.running = False
        if self.overlay is not None:
            self.overlay.hide()
        self.cursor_guard.show()
        self.absolute_cursor_asset = None
        self.rope_vel_x = self.rope_vel_y = 0.0
        self.pig_vel_x = self.pig_vel_y = 0.0
        self.pig_angular_velocity = 0.0
        self.custom_states.clear()
        self.animation_active = False
        self.frame_index = 0
        self.frame_time_ms = 0.0
        self._set_timer_resolution(False)
        self._update_buttons()

    def hide_to_background(self) -> None:
        if not self.running:
            return
        self.background_var.set(True)
        self._save_settings()
        self.root.withdraw()
        if self.tray_icon is not None:
            self.tray_icon.show()

    def _on_close_window(self) -> None:
        if self.running and self.background_var.get():
            self.hide_to_background()
        else:
            self.quit_app()

    def quit_app(self) -> None:
        self.running = False
        self._save_settings()
        if self.tray_icon is not None:
            self.tray_icon.destroy()
            self.tray_icon = None
        if self.overlay is not None:
            self.overlay.destroy()
            self.overlay = None
        self.cursor_guard.show()
        self._set_timer_resolution(False)
        self._destroy_window_icons()
        self.root.destroy()

    def restore_from_background(self) -> None:
        if self.tray_icon is not None:
            self.tray_icon.hide()
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def toggle_pet_from_tray(self) -> None:
        if self.running:
            self.stop_pet()
        else:
            self.start_pet()

    def _apply_window_icon(self, window: tk.Misc) -> None:
        icon_path = _resource_path(ICON_NAME)
        if not icon_path.exists():
            return
        photos: list[ImageTk.PhotoImage] = []
        try:
            icon_source = Image.open(icon_path)
            source_sizes = sorted(icon_source.ico.sizes()) if icon_source.format == "ICO" else [icon_source.size]
            for size in [(16, 16), (32, 32), (48, 48), (256, 256)]:
                try:
                    if icon_source.format == "ICO" and size in source_sizes:
                        icon_image = icon_source.ico.getimage(size).convert("RGBA")
                    else:
                        icon_image = icon_source.convert("RGBA").resize(size, _resample_filter())
                    photos.append(ImageTk.PhotoImage(icon_image, master=window))
                except Exception:
                    continue
            if photos:
                window.iconphoto(True, *photos)
                setattr(window, "_pig_pointer_icon_refs", photos)
        except Exception:
            pass
        try:
            window.iconbitmap(default=str(icon_path))
        except tk.TclError:
            pass
        self._apply_native_window_icon(window, icon_path)

    def _apply_native_window_icon(self, window: tk.Misc, icon_path: Path) -> None:
        if sys.platform != "win32" or not icon_path.exists():
            return
        try:
            hwnd = self._window_frame_handle(window)
            user32 = ctypes.windll.user32
            user32.GetSystemMetrics.argtypes = [ctypes.c_int]
            user32.GetSystemMetrics.restype = ctypes.c_int
            user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
            user32.SendMessageW.restype = wintypes.LPARAM
            small_w = user32.GetSystemMetrics(SM_CXSMICON) or 16
            small_h = user32.GetSystemMetrics(SM_CYSMICON) or 16
            big_w = user32.GetSystemMetrics(SM_CXICON) or 32
            big_h = user32.GetSystemMetrics(SM_CYICON) or 32
            small_icon = _load_windows_icon(icon_path, small_w, small_h)
            big_icon = _load_windows_icon(icon_path, big_w, big_h)
            if small_icon:
                user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, small_icon)
                user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL2, small_icon)
                self.window_icon_handles.append(small_icon)
            if big_icon:
                user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, big_icon)
                self.window_icon_handles.append(big_icon)
        except Exception:
            pass

    def _window_frame_handle(self, window: tk.Misc) -> int:
        try:
            window.update_idletasks()
            frame = window.tk.call("wm", "frame", window._w)
            hwnd = int(str(frame), 0)
            if hwnd:
                return hwnd
        except Exception:
            pass
        return int(window.winfo_id())

    def _disable_maximize_button(self) -> None:
        if sys.platform != "win32":
            return
        try:
            hwnd = self._window_frame_handle(self.root)
            user32 = ctypes.windll.user32
            user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
            user32.GetWindowLongW.restype = wintypes.LONG
            user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.LONG]
            user32.SetWindowLongW.restype = wintypes.LONG
            style = user32.GetWindowLongW(hwnd, GWL_STYLE)
            if style & WS_MAXIMIZEBOX:
                user32.SetWindowLongW(hwnd, GWL_STYLE, style & ~WS_MAXIMIZEBOX)
                self.root.update_idletasks()
        except Exception:
            pass

    def _refresh_taskbar_icon(self) -> None:
        try:
            if self.root.winfo_exists():
                self._apply_native_window_icon(self.root, _resource_path(ICON_NAME))
        except tk.TclError:
            pass

    def _destroy_window_icons(self) -> None:
        if sys.platform != "win32":
            return
        for hicon in self.window_icon_handles:
            try:
                ctypes.windll.user32.DestroyIcon(hicon)
            except Exception:
                pass
        self.window_icon_handles.clear()

    def _place_physics_at_cursor(self) -> None:
        anchor_x, anchor_y = self._cursor_anchor()
        rope_length = self._rope_length()
        balloon_start = max(0.0, min(1.0, (0.5 - self._weight_factor()) * 2.0))
        initial_direction = 1.0 - 2.0 * balloon_start
        self.rope_end_x = anchor_x
        self.rope_end_y = anchor_y + rope_length * initial_direction
        self.rope_vel_x = self.rope_vel_y = 0.0
        self.pig_x = self.rope_end_x
        self.pig_y = self.rope_end_y
        self.pig_vel_x = self.pig_vel_y = 0.0
        self.pig_angle = 0.0
        self.pig_angular_velocity = 0.0
        self.last_anchor = (anchor_x, anchor_y)
        self.last_cursor_velocity = (0.0, 0.0)
        self.initialized_physics = True
        self.frame_index = 0
        self.frame_time_ms = 0.0
        self.animation_active = False
        self.trigger_timer = 0.0
        self._place_custom_physics_at_cursor()

    def _place_custom_physics_at_cursor(self) -> None:
        self.custom_states.clear()
        anchor_x, anchor_y = self._cursor_anchor()
        previous_x, previous_y = anchor_x, anchor_y
        for index, asset in enumerate(self._active_custom_assets()):
            weight = max(0.0, min(1.0, asset.weight / 100.0))
            balloon_start = max(0.0, min(1.0, (0.5 - weight) * 2.0))
            direction = 1.0 - 2.0 * balloon_start
            if self.custom_connection_var.get() == CUSTOM_CONNECTION_MOUSE:
                item_anchor_x = anchor_x
                item_anchor_y = anchor_y
            else:
                item_anchor_x = previous_x
                item_anchor_y = previous_y
            state = CustomItemState(
                x=item_anchor_x,
                y=item_anchor_y + asset.rope_length * direction,
                anchor_x=item_anchor_x,
                anchor_y=item_anchor_y,
            )
            self.custom_states[asset.asset_id] = state
            previous_x, previous_y = state.x, state.y

    def _cursor_anchor(self) -> tuple[float, float]:
        pointer_x, pointer_y = self._cursor_position()
        return (pointer_x + self.anchor_x_var.get(), pointer_y + self.anchor_y_var.get())

    def _cursor_position(self) -> tuple[int, int]:
        if sys.platform == "win32":
            try:
                user32 = ctypes.windll.user32
                if not self.cursor_api_ready:
                    user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
                    user32.GetCursorPos.restype = wintypes.BOOL
                    self.cursor_api_ready = True
                point = POINT()
                if user32.GetCursorPos(ctypes.byref(point)):
                    return (int(point.x), int(point.y))
            except Exception:
                pass
        return self.root.winfo_pointerxy()

    def _rope_length(self) -> float:
        return max(20.0, self.rope_length_var.get())

    def _weight_factor(self) -> float:
        return max(0.0, min(1.0, self.weight_var.get() / 100.0))

    def _set_timer_resolution(self, enabled: bool) -> None:
        if sys.platform != "win32" or enabled == self.timer_resolution_enabled:
            return
        try:
            winmm = ctypes.windll.winmm
            if enabled:
                if winmm.timeBeginPeriod(1) == 0:
                    self.timer_resolution_enabled = True
            else:
                if winmm.timeEndPeriod(1) == 0:
                    self.timer_resolution_enabled = False
        except Exception:
            pass

    def _tick(self) -> None:
        now = time.perf_counter()
        profile = self._current_performance_profile()
        max_dt = 1 / max(30, profile.target_fps)
        dt = min(max_dt * 1.8, max(0.001, now - self.last_tick))
        self.last_tick = now

        if self.tray_icon is not None:
            self.tray_icon.process_pending_actions()
        self._advance_animation(dt)
        if not self.running and now - self.last_prewarm_time >= 0.025 and profile.texture_cache_limit > 180:
            self._prewarm_one_asset()
            self.last_prewarm_time = now
        if now - self.preview_last_time >= 1 / 20:
            self._draw_preview(now)
            self.preview_last_time = now
        if self.running:
            self._update_physics(dt)
            self._draw_overlay()

        delay = max(1, int(1000 / max(1, profile.target_fps))) if self.running else 12
        self.root.after(delay, self._tick)

    def _advance_animation(self, dt: float) -> None:
        if self.custom_mode_var.get():
            self._advance_custom_animations(dt)
            return
        probability = self.prob_var.get() / 100.0
        if not self.animation_active:
            self.frame_index = 0
            self.frame_time_ms = 0.0
            self.trigger_timer += dt
            trigger_interval = max(0.5, self.trigger_interval_var.get())
            if self.trigger_timer >= trigger_interval:
                self.trigger_timer %= trigger_interval
                if random.random() < probability:
                    self.animation_active = True
                    self.frame_index = 0
                    self.frame_time_ms = 0.0
            return

        self.frame_time_ms += dt * 1000.0 * max(0.2, self.anim_speed_var.get())
        while self.frame_time_ms >= self.renderer.durations[self.frame_index]:
            self.frame_time_ms -= self.renderer.durations[self.frame_index]
            self.frame_index += 1
            if self.frame_index >= self.renderer.frame_count:
                self.frame_index = 0
                self.frame_time_ms = 0.0
                self.animation_active = False
                self.trigger_timer = 0.0
                break

    def _advance_custom_animations(self, dt: float) -> None:
        for asset in self._active_custom_assets():
            state = self.custom_states.setdefault(asset.asset_id, CustomItemState())
            frame_count = self._custom_asset_frame_count(asset)
            if frame_count <= 1 or (asset.probability <= 0 and not asset.always_animate):
                state.animation_active = False
                state.frame_index = 0
                state.frame_time_ms = 0.0
                state.trigger_timer = 0.0
                continue
            if asset.always_animate:
                state.animation_active = True
                state.trigger_timer = 0.0
            if not state.animation_active:
                state.frame_index = 0
                state.frame_time_ms = 0.0
                state.trigger_timer += dt
                trigger_interval = max(0.5, self.trigger_interval_var.get())
                if state.trigger_timer >= trigger_interval:
                    state.trigger_timer %= trigger_interval
                    if random.random() < asset.probability / 100.0:
                        state.animation_active = True
                        state.frame_index = 0
                        state.frame_time_ms = 0.0
                continue

            state.frame_time_ms += dt * 1000.0 * max(0.2, asset.anim_speed)
            while state.frame_time_ms >= self._custom_asset_duration(asset, state.frame_index):
                state.frame_time_ms -= self._custom_asset_duration(asset, state.frame_index)
                state.frame_index += 1
                if state.frame_index >= frame_count:
                    state.frame_index = 0
                    state.frame_time_ms = 0.0
                    state.animation_active = False
                    state.trigger_timer = 0.0
                    break

    def _update_physics(self, dt: float) -> None:
        if not self.initialized_physics:
            self._place_physics_at_cursor()

        anchor_x, anchor_y = self._cursor_anchor()
        last_x, last_y = self.last_anchor
        cursor_vx = (anchor_x - last_x) / dt
        cursor_vy = (anchor_y - last_y) / dt
        self.last_anchor = (anchor_x, anchor_y)
        self.last_cursor_velocity = (cursor_vx, cursor_vy)
        if self.custom_mode_var.get():
            self._update_custom_physics(dt, anchor_x, anchor_y, cursor_vx, cursor_vy)
            return

        rope_length = self._rope_length()
        weight = self._weight_factor()
        balloon = 1.0 - weight
        dx = self.rope_end_x - anchor_x
        dy = self.rope_end_y - anchor_y
        distance = max(1.0, math.hypot(dx, dy))
        nx = dx / distance
        ny = dy / distance

        tangent_x = -ny
        tangent_y = nx
        tangent_velocity = self.rope_vel_x * tangent_x + self.rope_vel_y * tangent_y
        anchor_tangent_velocity = cursor_vx * tangent_x + cursor_vy * tangent_y

        rope_damping = 4.3 + 3.2 * balloon
        cursor_coupling = 0.78 - 0.50 * balloon
        gravity_strength = 1700.0 * weight - 900.0 * balloon
        tangential_force = -rope_damping * (tangent_velocity - anchor_tangent_velocity * cursor_coupling)
        gravity_force = gravity_strength * tangent_y

        self.rope_vel_x += (tangential_force + gravity_force) * tangent_x * dt
        self.rope_vel_y += (tangential_force + gravity_force) * tangent_y * dt
        air_drag = 1.1 * balloon
        if air_drag > 0:
            drag_scale = max(0.0, 1.0 - air_drag * dt)
            self.rope_vel_x *= drag_scale
            self.rope_vel_y *= drag_scale
        max_rope_speed = 2100.0 - 800.0 * balloon
        rope_speed = math.hypot(self.rope_vel_x, self.rope_vel_y)
        if rope_speed > max_rope_speed:
            scale = max_rope_speed / rope_speed
            self.rope_vel_x *= scale
            self.rope_vel_y *= scale
        self.rope_end_x += self.rope_vel_x * dt
        self.rope_end_y += self.rope_vel_y * dt

        self._constrain_rope_to_anchor(anchor_x, anchor_y, rope_length)

        self.pig_x = self.rope_end_x
        self.pig_y = self.rope_end_y
        self.pig_vel_x = self.rope_vel_x
        self.pig_vel_y = self.rope_vel_y

        target_angle = max(
            -48.0,
            min(48.0, self.rope_vel_x * (0.050 - 0.032 * balloon) + cursor_vx * (0.009 - 0.007 * balloon)),
        )
        target_angle = math.radians(target_angle)
        rotation_spring = 17.0 - 5.0 * balloon
        rotation_damping = 4.0 - 1.6 * balloon
        self.pig_angular_velocity += (target_angle - self.pig_angle) * rotation_spring * dt
        self.pig_angular_velocity *= max(0.0, 1.0 - rotation_damping * dt)
        self.pig_angle += self.pig_angular_velocity * dt

    def _update_custom_physics(
        self,
        dt: float,
        anchor_x: float,
        anchor_y: float,
        cursor_vx: float,
        cursor_vy: float,
    ) -> None:
        active_assets = self._active_custom_assets()
        if not active_assets:
            return
        active_ids = {asset.asset_id for asset in active_assets}
        for asset_id in list(self.custom_states.keys()):
            if asset_id not in active_ids:
                self.custom_states.pop(asset_id, None)

        previous_x, previous_y = anchor_x, anchor_y
        previous_vx, previous_vy = cursor_vx, cursor_vy
        for index, asset in enumerate(active_assets):
            state = self.custom_states.setdefault(asset.asset_id, CustomItemState())
            if state.x == 0.0 and state.y == 0.0:
                state.x = previous_x
                state.y = previous_y + asset.rope_length
            if self.custom_connection_var.get() == CUSTOM_CONNECTION_MOUSE:
                item_anchor_x = anchor_x
                item_anchor_y = anchor_y
                item_anchor_vx = cursor_vx
                item_anchor_vy = cursor_vy
            else:
                item_anchor_x = previous_x
                item_anchor_y = previous_y
                item_anchor_vx = previous_vx
                item_anchor_vy = previous_vy
            self._update_custom_item_physics(state, asset, item_anchor_x, item_anchor_y, item_anchor_vx, item_anchor_vy, dt)
            previous_x, previous_y = state.x, state.y
            previous_vx, previous_vy = state.vx, state.vy

        self._resolve_custom_collisions(active_assets, dt)

    def _update_custom_item_physics(
        self,
        state: CustomItemState,
        asset: CustomAssetConfig,
        anchor_x: float,
        anchor_y: float,
        anchor_vx: float,
        anchor_vy: float,
        dt: float,
    ) -> None:
        rope_length = max(20.0, asset.rope_length)
        weight = max(0.0, min(1.0, asset.weight / 100.0))
        balloon = 1.0 - weight
        dx = state.x - anchor_x
        dy = state.y - anchor_y
        distance = max(1.0, math.hypot(dx, dy))
        nx = dx / distance
        ny = dy / distance
        tangent_x = -ny
        tangent_y = nx
        tangent_velocity = state.vx * tangent_x + state.vy * tangent_y
        anchor_tangent_velocity = anchor_vx * tangent_x + anchor_vy * tangent_y
        rope_damping = 3.5 + 3.0 * balloon
        cursor_coupling = 0.72 - 0.45 * balloon
        gravity_strength = 1500.0 * weight - 900.0 * balloon
        tangential_force = -rope_damping * (tangent_velocity - anchor_tangent_velocity * cursor_coupling)
        gravity_force = gravity_strength * tangent_y
        state.vx += (tangential_force + gravity_force) * tangent_x * dt
        state.vy += (tangential_force + gravity_force) * tangent_y * dt
        air_drag = 0.9 * balloon
        if air_drag > 0:
            drag_scale = max(0.0, 1.0 - air_drag * dt)
            state.vx *= drag_scale
            state.vy *= drag_scale
        max_speed = 2200.0 - 700.0 * balloon
        speed = math.hypot(state.vx, state.vy)
        if speed > max_speed:
            scale = max_speed / speed
            state.vx *= scale
            state.vy *= scale
        state.x += state.vx * dt
        state.y += state.vy * dt
        self._constrain_custom_state_to_anchor(state, anchor_x, anchor_y, rope_length)
        state.anchor_x = anchor_x
        state.anchor_y = anchor_y

        target_angle = max(-50.0, min(50.0, state.vx * (0.045 - 0.028 * balloon) + anchor_vx * (0.008 - 0.006 * balloon)))
        target_angle = math.radians(target_angle)
        rotation_spring = 15.0 - 4.0 * balloon
        rotation_damping = 3.6 - 1.2 * balloon
        state.angular_velocity += (target_angle - state.angle) * rotation_spring * dt
        state.angular_velocity *= max(0.0, 1.0 - rotation_damping * dt)
        state.angle += state.angular_velocity * dt

    @staticmethod
    def _constrain_custom_state_to_anchor(
        state: CustomItemState,
        anchor_x: float,
        anchor_y: float,
        rope_length: float,
    ) -> None:
        dx = state.x - anchor_x
        dy = state.y - anchor_y
        distance = math.hypot(dx, dy)
        if distance < 1.0:
            dx, dy, distance = 0.0, rope_length, rope_length
        nx = dx / distance
        ny = dy / distance
        state.x = anchor_x + nx * rope_length
        state.y = anchor_y + ny * rope_length
        radial_velocity = state.vx * nx + state.vy * ny
        state.vx -= radial_velocity * nx
        state.vy -= radial_velocity * ny

    def _resolve_custom_collisions(self, active_assets: list[CustomAssetConfig], dt: float) -> None:
        if not self.custom_collision_var.get():
            return
        for first_index in range(len(active_assets)):
            first = active_assets[first_index]
            first_state = self.custom_states.get(first.asset_id)
            if first_state is None:
                continue
            for second in active_assets[first_index + 1 :]:
                second_state = self.custom_states.get(second.asset_id)
                if second_state is None:
                    continue
                dx = second_state.x - first_state.x
                dy = second_state.y - first_state.y
                distance = math.hypot(dx, dy)
                minimum = max(2.0, first.collision_radius + second.collision_radius)
                if distance >= minimum:
                    continue
                if distance < 0.01:
                    nx, ny = 1.0, 0.0
                else:
                    nx, ny = dx / distance, dy / distance
                penetration = minimum - distance
                softness = 0.42
                push = penetration * softness * 0.5
                first_state.x -= nx * push
                first_state.y -= ny * push
                second_state.x += nx * push
                second_state.y += ny * push
                relative_velocity = (second_state.vx - first_state.vx) * nx + (second_state.vy - first_state.vy) * ny
                if relative_velocity < 0:
                    impulse = -(1.0 + 0.10) * relative_velocity * 0.5
                    first_state.vx -= nx * impulse
                    first_state.vy -= ny * impulse
                    second_state.vx += nx * impulse
                    second_state.vy += ny * impulse
                first_state.vx *= max(0.0, 1.0 - 0.8 * dt)
                first_state.vy *= max(0.0, 1.0 - 0.8 * dt)
                second_state.vx *= max(0.0, 1.0 - 0.8 * dt)
                second_state.vy *= max(0.0, 1.0 - 0.8 * dt)

    def _constrain_rope_to_anchor(self, anchor_x: float, anchor_y: float, rope_length: float) -> None:
        dx = self.rope_end_x - anchor_x
        dy = self.rope_end_y - anchor_y
        distance = math.hypot(dx, dy)
        if distance < 1.0:
            dx, dy, distance = 0.0, rope_length, rope_length
        nx = dx / distance
        ny = dy / distance
        self.rope_end_x = anchor_x + nx * rope_length
        self.rope_end_y = anchor_y + ny * rope_length

        radial_velocity = self.rope_vel_x * nx + self.rope_vel_y * ny
        self.rope_vel_x -= radial_velocity * nx
        self.rope_vel_y -= radial_velocity * ny

    def _draw_overlay(self) -> None:
        if self.overlay is None:
            return
        if self.custom_mode_var.get():
            self._draw_custom_overlay()
            return
        display_height = int(self.size_var.get())
        angle = math.degrees(self.pig_angle)
        image, joint, _bgra = self.renderer.render_asset(self.frame_index, display_height, angle)
        anchor_x, anchor_y = self._cursor_anchor()
        self._constrain_rope_to_anchor(anchor_x, anchor_y, self._rope_length())
        self.pig_x = self.rope_end_x
        self.pig_y = self.rope_end_y
        image_x = self.pig_x - joint[0]
        image_y = self.pig_y - joint[1]

        margin = max(18, int(display_height * 0.2))
        absolute_binding = self.absolute_binding_var.get()
        cursor_asset = None
        pointer_x = pointer_y = 0
        if absolute_binding:
            pointer_x, pointer_y = self._cursor_position()
            cursor_asset = self.absolute_cursor_asset
            if cursor_asset is None:
                cursor_asset = _capture_system_cursor()
                self.absolute_cursor_asset = cursor_asset
        if absolute_binding and cursor_asset is not None:
            cursor_image, cursor_hotspot = cursor_asset
            cursor_left = pointer_x - cursor_hotspot[0]
            cursor_top = pointer_y - cursor_hotspot[1]
            left = math.floor(min(anchor_x, self.rope_end_x, image_x, cursor_left) - margin)
            top = math.floor(min(anchor_y, self.rope_end_y, image_y, cursor_top) - margin)
            right = math.ceil(max(anchor_x, self.rope_end_x, image_x + image.width, cursor_left + cursor_image.width) + margin)
            bottom = math.ceil(max(anchor_y, self.rope_end_y, image_y + image.height, cursor_top + cursor_image.height) + margin)
        elif absolute_binding:
            cursor_points = self._cursor_polygon(pointer_x, pointer_y)
            cursor_outline = self._cursor_outline(cursor_points)
            cursor_xs = [point[0] for point in cursor_points + cursor_outline]
            cursor_ys = [point[1] for point in cursor_points + cursor_outline]
            left = math.floor(min(anchor_x, self.rope_end_x, image_x, min(cursor_xs)) - margin)
            top = math.floor(min(anchor_y, self.rope_end_y, image_y, min(cursor_ys)) - margin)
            right = math.ceil(max(anchor_x, self.rope_end_x, image_x + image.width, max(cursor_xs)) + margin)
            bottom = math.ceil(max(anchor_y, self.rope_end_y, image_y + image.height, max(cursor_ys)) + margin)
        else:
            left = math.floor(min(anchor_x, self.rope_end_x, image_x) - margin)
            top = math.floor(min(anchor_y, self.rope_end_y, image_y) - margin)
            right = math.ceil(max(anchor_x, self.rope_end_x, image_x + image.width) + margin)
            bottom = math.ceil(max(anchor_y, self.rope_end_y, image_y + image.height) + margin)
        canvas_w = max(16, right - left)
        canvas_h = max(16, bottom - top)

        composite = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(composite)
        weight = self._weight_factor()
        sag = min(48.0, self._rope_length() * (0.16 + 0.15 * weight) + abs(self.rope_vel_x) * (0.004 + 0.005 * weight))
        control_x = (anchor_x + self.rope_end_x) / 2 - left + (self.rope_vel_x * 0.018)
        control_y = (anchor_y + self.rope_end_y) / 2 - top + sag
        points = []
        for step in range(18):
            t = step / 17
            inv = 1.0 - t
            x = inv * inv * (anchor_x - left) + 2 * inv * t * control_x + t * t * (self.rope_end_x - left)
            y = inv * inv * (anchor_y - top) + 2 * inv * t * control_y + t * t * (self.rope_end_y - top)
            points.append((x, y))
        draw.line(points, fill=(116, 77, 45, 245), width=max(1, int(round(self.rope_width_var.get()))), joint="curve")
        composite.alpha_composite(image, (int(round(image_x - left)), int(round(image_y - top))))
        if absolute_binding and cursor_asset is not None:
            cursor_image, cursor_hotspot = cursor_asset
            cursor_left = int(round(pointer_x - cursor_hotspot[0] - left))
            cursor_top = int(round(pointer_y - cursor_hotspot[1] - top))
            composite.alpha_composite(cursor_image, (cursor_left, cursor_top))
        elif absolute_binding:
            cursor_points = self._cursor_polygon(pointer_x, pointer_y)
            cursor_outline = self._cursor_outline(cursor_points)
            self._draw_cursor_on_pil(draw, cursor_points, cursor_outline, left, top)
        bgra = GifRenderer.to_premultiplied_bgra(composite)
        self.overlay.update_pixels(bgra, composite.width, composite.height, left, top)

    def _draw_custom_overlay(self) -> None:
        if self.overlay is None:
            return
        active_assets = self._active_custom_assets()
        if not active_assets:
            if self.absolute_binding_var.get():
                self._draw_cursor_only_overlay()
            elif self.overlay.visible:
                self.overlay.hide()
            return

        rendered_items: list[CustomRenderedItem] = []
        profile = self._current_performance_profile()
        for asset in active_assets:
            state = self.custom_states.get(asset.asset_id)
            if state is None:
                continue
            frame_index = state.frame_index if state.animation_active else 0
            rendered = self._render_custom_asset(
                asset,
                frame_index,
                int(asset.size),
                math.degrees(state.angle),
                profile.angle_step,
            )
            if rendered is None:
                continue
            image, joint, _bgra = rendered
            image_x = state.x - joint[0]
            image_y = state.y - joint[1]
            rendered_items.append(CustomRenderedItem(asset, state, image, joint, image_x, image_y))

        if not rendered_items:
            if self.overlay.visible:
                self.overlay.hide()
            return

        absolute_binding = self.absolute_binding_var.get()
        cursor_asset = None
        pointer_x = pointer_y = 0
        if absolute_binding:
            pointer_x, pointer_y = self._cursor_position()
            cursor_asset = self.absolute_cursor_asset
            if cursor_asset is None:
                cursor_asset = _capture_system_cursor()
                self.absolute_cursor_asset = cursor_asset

        margin = max(24, int(max(item.config.size for item in rendered_items) * 0.22))
        xs: list[float] = []
        ys: list[float] = []
        for item in rendered_items:
            xs.extend([item.state.anchor_x, item.state.x, item.image_x, item.image_x + item.image.width])
            ys.extend([item.state.anchor_y, item.state.y, item.image_y, item.image_y + item.image.height])
        if absolute_binding and cursor_asset is not None:
            cursor_image, cursor_hotspot = cursor_asset
            xs.extend([pointer_x - cursor_hotspot[0], pointer_x - cursor_hotspot[0] + cursor_image.width])
            ys.extend([pointer_y - cursor_hotspot[1], pointer_y - cursor_hotspot[1] + cursor_image.height])
        elif absolute_binding:
            cursor_points = self._cursor_polygon(pointer_x, pointer_y)
            cursor_outline = self._cursor_outline(cursor_points)
            xs.extend(point[0] for point in cursor_points + cursor_outline)
            ys.extend(point[1] for point in cursor_points + cursor_outline)

        left = math.floor(min(xs) - margin)
        top = math.floor(min(ys) - margin)
        right = math.ceil(max(xs) + margin)
        bottom = math.ceil(max(ys) + margin)
        canvas_w = max(16, right - left)
        canvas_h = max(16, bottom - top)
        composite = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(composite)

        for item in rendered_items:
            state = item.state
            config = item.config
            weight = max(0.0, min(1.0, config.weight / 100.0))
            sag = min(54.0, config.rope_length * (0.12 + 0.18 * weight) + abs(state.vx) * (0.003 + 0.004 * weight))
            control_x = (state.anchor_x + state.x) / 2 - left + state.vx * 0.014
            control_y = (state.anchor_y + state.y) / 2 - top + sag
            points = []
            for step in range(18):
                t = step / 17
                inv = 1.0 - t
                x = inv * inv * (state.anchor_x - left) + 2 * inv * t * control_x + t * t * (state.x - left)
                y = inv * inv * (state.anchor_y - top) + 2 * inv * t * control_y + t * t * (state.y - top)
                points.append((x, y))
            draw.line(points, fill=self._custom_rope_rgba(config), width=max(1, int(round(config.rope_width))), joint="curve")

        for item in rendered_items:
            composite.alpha_composite(item.image, (int(round(item.image_x - left)), int(round(item.image_y - top))))

        if absolute_binding and cursor_asset is not None:
            cursor_image, cursor_hotspot = cursor_asset
            cursor_left = int(round(pointer_x - cursor_hotspot[0] - left))
            cursor_top = int(round(pointer_y - cursor_hotspot[1] - top))
            composite.alpha_composite(cursor_image, (cursor_left, cursor_top))
        elif absolute_binding:
            cursor_points = self._cursor_polygon(pointer_x, pointer_y)
            cursor_outline = self._cursor_outline(cursor_points)
            self._draw_cursor_on_pil(draw, cursor_points, cursor_outline, left, top)

        bgra = GifRenderer.to_premultiplied_bgra(composite)
        self.overlay.update_pixels(bgra, composite.width, composite.height, left, top)

    def _custom_asset_frame_count(self, asset: CustomAssetConfig) -> int:
        if asset.asset_id == DEFAULT_PIG_CUSTOM_ID:
            return self.renderer.frame_count
        renderer = self._custom_renderer(asset)
        return renderer.frame_count(asset.reverse_loop) if renderer is not None else 1

    def _custom_asset_duration(self, asset: CustomAssetConfig, frame_index: int) -> int:
        if asset.asset_id == DEFAULT_PIG_CUSTOM_ID:
            return self.renderer.durations[frame_index % self.renderer.frame_count]
        renderer = self._custom_renderer(asset)
        return renderer.duration(frame_index, asset.reverse_loop) if renderer is not None else 40

    def _render_custom_asset(
        self,
        asset: CustomAssetConfig,
        frame_index: int,
        display_height: int,
        angle: float,
        angle_step: int,
    ) -> tuple[Image.Image, tuple[float, float], bytes] | None:
        if asset.asset_id == DEFAULT_PIG_CUSTOM_ID:
            return self.renderer.render_asset(frame_index, display_height, angle, angle_step)
        renderer = self._custom_renderer(asset)
        if renderer is None:
            return None
        return renderer.render_asset(
            frame_index,
            display_height,
            angle,
            asset.reverse_loop,
            angle_step=angle_step,
            attach_mode=asset.attach_mode,
            attach_x=asset.attach_x,
            attach_y=asset.attach_y,
        )

    def _render_custom_preview_asset(
        self,
        asset: CustomAssetConfig,
        frame_index: int,
        display_height: int,
        angle: float,
    ) -> tuple[ImageTk.PhotoImage, tuple[float, float]] | None:
        if asset.asset_id == DEFAULT_PIG_CUSTOM_ID:
            return self.renderer.render(frame_index, display_height, angle)
        renderer = self._custom_renderer(asset)
        if renderer is None:
            return None
        return renderer.render(
            frame_index,
            display_height,
            angle,
            asset.reverse_loop,
            attach_mode=asset.attach_mode,
            attach_x=asset.attach_x,
            attach_y=asset.attach_y,
        )

    def _draw_cursor_only_overlay(self) -> None:
        if self.overlay is None:
            return
        pointer_x, pointer_y = self._cursor_position()
        cursor_asset = self.absolute_cursor_asset
        if cursor_asset is None:
            cursor_asset = _capture_system_cursor()
            self.absolute_cursor_asset = cursor_asset
        margin = 6
        if cursor_asset is not None:
            cursor_image, cursor_hotspot = cursor_asset
            left = int(math.floor(pointer_x - cursor_hotspot[0] - margin))
            top = int(math.floor(pointer_y - cursor_hotspot[1] - margin))
            composite = Image.new("RGBA", (cursor_image.width + margin * 2, cursor_image.height + margin * 2), (0, 0, 0, 0))
            composite.alpha_composite(cursor_image, (margin, margin))
        else:
            cursor_points = self._cursor_polygon(pointer_x, pointer_y)
            cursor_outline = self._cursor_outline(cursor_points)
            xs = [point[0] for point in cursor_points + cursor_outline]
            ys = [point[1] for point in cursor_points + cursor_outline]
            left = int(math.floor(min(xs) - margin))
            top = int(math.floor(min(ys) - margin))
            composite = Image.new(
                "RGBA",
                (int(math.ceil(max(xs) - min(xs) + margin * 2)), int(math.ceil(max(ys) - min(ys) + margin * 2))),
                (0, 0, 0, 0),
            )
            draw = ImageDraw.Draw(composite)
            self._draw_cursor_on_pil(draw, cursor_points, cursor_outline, left, top)
        bgra = GifRenderer.to_premultiplied_bgra(composite)
        self.overlay.update_pixels(bgra, composite.width, composite.height, left, top)

    def _custom_renderer(self, asset: CustomAssetConfig) -> CustomAssetRenderer | None:
        renderer = self.custom_renderers.get(asset.asset_id)
        if renderer is not None:
            return renderer
        path = Path(asset.path)
        if not path.exists():
            return None
        try:
            renderer = CustomAssetRenderer(path, self.root)
        except Exception:
            return None
        renderer.cache_limit = max(32, self._current_performance_profile().texture_cache_limit // max(2, len(self.custom_assets) or 2))
        self.custom_renderers[asset.asset_id] = renderer
        return renderer

    def _clear_custom_renderer_cache(self, asset_id: str) -> None:
        renderer = self.custom_renderers.get(asset_id)
        if renderer is not None:
            renderer.clear_cache()

    @staticmethod
    def _cursor_polygon(pointer_x: float, pointer_y: float) -> list[tuple[float, float]]:
        return [
            (pointer_x, pointer_y),
            (pointer_x, pointer_y + 22),
            (pointer_x + 7, pointer_y + 17),
            (pointer_x + 12, pointer_y + 29),
            (pointer_x + 17, pointer_y + 27),
            (pointer_x + 12, pointer_y + 15),
            (pointer_x + 20, pointer_y + 14),
        ]

    @staticmethod
    def _cursor_outline(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
        return [
            (points[0][0] - 1, points[0][1] + 1),
            (points[1][0] - 2, points[1][1] - 1),
            (points[2][0] - 1, points[2][1] - 1),
            (points[3][0] - 1, points[3][1] - 1),
            (points[4][0] + 2, points[4][1]),
            (points[5][0] + 1, points[5][1] + 1),
            (points[6][0] + 2, points[6][1] + 1),
        ]

    @staticmethod
    def _draw_cursor_on_pil(
        draw: ImageDraw.ImageDraw,
        points: list[tuple[float, float]],
        outline: list[tuple[float, float]],
        left: int,
        top: int,
    ) -> None:
        outline_points = [(x - left, y - top) for x, y in outline]
        cursor_points = [(x - left, y - top) for x, y in points]
        draw.polygon(outline_points, fill=(20, 20, 20, 255))
        draw.polygon(cursor_points, fill=(255, 255, 255, 255))

    def _hide_preview_attach_marker(self) -> None:
        self.custom_preview_bounds = None
        if self.preview_attach_marker is not None:
            self.preview.itemconfigure(self.preview_attach_marker, state="hidden")

    def _on_preview_attach_drag(self, event: tk.Event) -> None:
        if not self.custom_mode_var.get() or self.custom_preview_bounds is None:
            return
        asset = self._selected_custom_asset()
        if asset is None or asset.asset_id == DEFAULT_PIG_CUSTOM_ID:
            return
        asset_id, image_x, image_y, image_width, image_height = self.custom_preview_bounds
        if asset.asset_id != asset_id or image_width <= 1 or image_height <= 1:
            return
        local_x = _clamp(event.x - image_x, 0, image_width, image_width / 2)
        local_y = _clamp(event.y - image_y, 0, image_height, 0)
        self.custom_item_attach_mode_var.set(CUSTOM_ATTACH_FIXED)
        self.custom_item_attach_x_var.set(local_x / image_width * 100.0)
        self.custom_item_attach_y_var.set(local_y / image_height * 100.0)
        self._on_custom_item_setting_changed()
        self._draw_preview(time.perf_counter())

    def _draw_preview(self, now: float) -> None:
        width = max(1, self.preview.winfo_width() or int(self.preview["width"]))
        if self.custom_mode_var.get():
            self._draw_custom_preview(now, width)
            return
        self._hide_preview_attach_marker()
        preview_height = int(max(52, min(112, self.size_var.get() * 0.55)))
        sway = math.sin(now * 2.2) * 8.0
        angle = sway * 0.85

        photo, joint = self.renderer.render(self.frame_index, preview_height, angle)
        self.preview_photo = photo

        anchor_x = width / 2
        anchor_y = 22
        rope_end_x = anchor_x + math.sin(now * 1.7) * 12
        rope_end_y = anchor_y + self._rope_length() * 0.52

        self.preview.coords(self.preview_anchor, anchor_x - 5, anchor_y - 5, anchor_x + 5, anchor_y + 5)
        self.preview.coords(self.preview_anchor_ring, anchor_x - 9, anchor_y - 9, anchor_x + 9, anchor_y + 9)
        self.preview.coords(
            self.preview_rope,
            anchor_x,
            anchor_y,
            (anchor_x + rope_end_x) / 2,
            (anchor_y + rope_end_y) / 2 + 8,
            rope_end_x,
            rope_end_y,
        )
        self.preview.coords(self.preview_image, rope_end_x - joint[0], rope_end_y - joint[1])
        self.preview.itemconfigure(self.preview_rope, width=max(1, int(round(self.rope_width_var.get()))))
        self.preview.itemconfigure(self.preview_image, image=photo)

    def _draw_custom_preview(self, now: float, width: int) -> None:
        asset = self._selected_custom_asset()
        if asset is None:
            self.preview.coords(self.preview_anchor, width / 2 - 5, 17, width / 2 + 5, 27)
            self.preview.coords(self.preview_anchor_ring, width / 2 - 9, 16, width / 2 + 9, 34)
            self.preview.coords(self.preview_rope, width / 2, 25, width / 2, 70)
            self.preview.itemconfigure(self.preview_rope, fill="#744d2d", width=3)
            self.preview.itemconfigure(self.preview_image, image="")
            self._hide_preview_attach_marker()
            return
        preview_height = int(max(42, min(112, asset.size * 0.55)))
        frame_count = self._custom_asset_frame_count(asset)
        if frame_count > 1 and (asset.probability > 0 or asset.always_animate):
            frame_index = int(now * 1000 / max(24, self._custom_asset_duration(asset, 0)) * max(0.2, asset.anim_speed)) % frame_count
        else:
            frame_index = 0
        rendered = self._render_custom_preview_asset(asset, frame_index, preview_height, 0.0)
        if rendered is None:
            self.preview.itemconfigure(self.preview_image, image="")
            self._hide_preview_attach_marker()
            return
        photo, joint = rendered
        self.custom_preview_photo = photo
        anchor_x = width / 2
        anchor_y = 22
        image_x = (width - photo.width()) / 2
        image_y = max(34.0, min(148.0 - photo.height(), anchor_y + 42.0))
        rope_end_x = image_x + joint[0]
        rope_end_y = image_y + joint[1]
        self.preview.coords(self.preview_anchor, anchor_x - 5, anchor_y - 5, anchor_x + 5, anchor_y + 5)
        self.preview.coords(self.preview_anchor_ring, anchor_x - 9, anchor_y - 9, anchor_x + 9, anchor_y + 9)
        self.preview.coords(
            self.preview_rope,
            anchor_x,
            anchor_y,
            (anchor_x + rope_end_x) / 2,
            (anchor_y + rope_end_y) / 2 + 8,
            rope_end_x,
            rope_end_y,
        )
        rgba = self._custom_rope_rgba(asset)
        self.preview.itemconfigure(
            self.preview_rope,
            fill=f"#{rgba[0]:02x}{rgba[1]:02x}{rgba[2]:02x}",
            width=max(1, int(round(asset.rope_width))),
        )
        self.preview.coords(self.preview_image, image_x, image_y)
        self.preview.itemconfigure(self.preview_image, image=photo)
        self.custom_preview_bounds = (asset.asset_id, image_x, image_y, float(photo.width()), float(photo.height()))
        if self.preview_attach_marker is not None and asset.asset_id != DEFAULT_PIG_CUSTOM_ID:
            self.preview.coords(self.preview_attach_marker, rope_end_x - 4, rope_end_y - 4, rope_end_x + 4, rope_end_y + 4)
            marker_fill = "#e53935" if asset.attach_mode == CUSTOM_ATTACH_FIXED else "#f0a22e"
            self.preview.itemconfigure(self.preview_attach_marker, fill=marker_fill, state="normal")
            self.preview.tag_raise(self.preview_attach_marker)
        else:
            self._hide_preview_attach_marker()


def main() -> None:
    _enable_dpi_awareness()
    _set_windows_app_id()
    gif_path = _resource_path(GIF_NAME)
    if not gif_path.exists():
        messagebox.showerror("找不到 GIF", f"请把 {GIF_NAME} 放在程序同一目录下。")
        return

    root = tk.Tk()
    PigPointerApp(root, gif_path)
    root.mainloop()


if __name__ == "__main__":
    main()
