# -*- coding: utf-8 -*-
"""Constants, configuration data, and performance profiles for Pig Pointer."""

from __future__ import annotations

import ctypes
from collections import OrderedDict
from ctypes import wintypes
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Application metadata
# ---------------------------------------------------------------------------

APP_TITLE = "猪猪指针"
GIF_NAME = "pig_pointer.gif"
ICON_NAME = "pig_pointer.ico"
SETTINGS_FILE_NAME = "settings.json"
STARTUP_VALUE_NAME = "PigPointer"

# ---------------------------------------------------------------------------
# Win32 API constants
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Cursor capture / settings
# ---------------------------------------------------------------------------

_CURSOR_CAPTURE_API_READY = False
SETTINGS_VERSION = 1
CUSTOM_ASSETS_DIR_NAME = "assets"
DEFAULT_PIG_CUSTOM_ID = "__default_pig__"

# ---------------------------------------------------------------------------
# Custom asset configuration constants
# ---------------------------------------------------------------------------

CUSTOM_CONNECTION_MOUSE = "都连到鼠标"
CUSTOM_CONNECTION_CHAIN = "串成一串"
CUSTOM_CONNECTION_MODES = (CUSTOM_CONNECTION_MOUSE, CUSTOM_CONNECTION_CHAIN)
CUSTOM_ATTACH_AUTO = "自动识别"
CUSTOM_ATTACH_FIXED = "手动固定"
CUSTOM_ATTACH_MODES = (CUSTOM_ATTACH_AUTO, CUSTOM_ATTACH_FIXED)
CUSTOM_ASSET_SUFFIXES = {".gif", ".png", ".jpg", ".jpeg", ".webp", ".bmp"}

# ---------------------------------------------------------------------------
# Rope colors
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Default settings
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Custom resource presets
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Performance profiles
# ---------------------------------------------------------------------------

SMART_PERFORMANCE_MODE = "智能性能"
PERFORMANCE_MODE_ALIASES = {
    "低性能": SMART_PERFORMANCE_MODE,
}


@dataclass(frozen=True)
class PerformanceProfile:
    target_fps: int
    angle_step: int
    texture_cache_limit: int
    high_resolution_timer: bool
    adaptive: bool = False
    idle_fps: int = 18
    animation_fps: int = 30


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
    SMART_PERFORMANCE_MODE: PerformanceProfile(
        target_fps=60,
        angle_step=4,
        texture_cache_limit=260,
        high_resolution_timer=False,
        adaptive=True,
        idle_fps=18,
        animation_fps=30,
    ),
}

# ---------------------------------------------------------------------------
# ctypes type aliases used by win32.py
# ---------------------------------------------------------------------------

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
