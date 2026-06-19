# -*- coding: utf-8 -*-
"""Windows API wrappers: layered overlay window, cursor capture, DPI helpers."""

from __future__ import annotations

import atexit
import ctypes
import sys
from ctypes import wintypes
from pathlib import Path
from typing import TYPE_CHECKING

from pig_pointer.constants import (
    APP_TITLE,
    BI_RGB,
    DIB_RGB_COLORS,
    DI_NORMAL,
    ERROR_CLASS_ALREADY_EXISTS,
    HBITMAP,
    HCURSOR,
    HGDIOBJ,
    HICON,
    HTTRANSPARENT,
    ICON_SMALL,
    ICON_SMALL2,
    ICON_BIG,
    IDC_ARROW,
    IMAGE_ICON,
    LR_LOADFROMFILE,
    LRESULT,
    SMART_PERFORMANCE_MODE,
    SM_CXCURSOR,
    SM_CYCURSOR,
    SM_CXICON,
    SM_CXSMICON,
    SM_CYICON,
    SM_CYSMICON,
    SPI_SETCURSORS,
    STANDARD_CURSOR_IDS,
    STARTUP_VALUE_NAME,
    SW_HIDE,
    SW_SHOWNOACTIVATE,
    ULW_ALPHA,
    AC_SRC_OVER,
    AC_SRC_ALPHA,
    WM_NCHITTEST,
    WM_SETICON,
    WNDPROC,
    WS_EX_LAYERED,
    WS_EX_NOACTIVATE,
    WS_EX_TOOLWINDOW,
    WS_EX_TOPMOST,
    WS_EX_TRANSPARENT,
    WS_MAXIMIZEBOX,
    WS_POPUP,
    _CURSOR_CAPTURE_API_READY,
)

from pig_pointer.utils import _startup_command

if TYPE_CHECKING:
    from PIL import Image, ImageDraw

# ---------------------------------------------------------------------------
# ctypes structures
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Overlay window procedure
# ---------------------------------------------------------------------------


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

# ---------------------------------------------------------------------------
# DPI / app identity helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# System tray / startup registry helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Windows icon loader
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Cursor capture & DIB drawing
# ---------------------------------------------------------------------------


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


def _capture_system_cursor() -> tuple["Image.Image", tuple[float, float]] | None:
    if sys.platform != "win32":
        return None
    try:
        _configure_cursor_capture_api()
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        from PIL import Image

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

        _SM_CXCURSOR = 13
        _SM_CYCURSOR = 14
        width = max(16, user32.GetSystemMetrics(_SM_CXCURSOR) or 32)
        height = max(16, user32.GetSystemMetrics(_SM_CYCURSOR) or 32)
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


# ---------------------------------------------------------------------------
# Cursor visibility guard
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# AlphaOverlay — transparent layered window
# ---------------------------------------------------------------------------


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
        # DIB cache: reuse GDI objects across frames to avoid per-frame allocation
        self._cached_width = 0
        self._cached_height = 0
        self._cached_memory_dc: wintypes.HDC | None = None
        self._cached_bitmap: HBITMAP | None = None
        self._cached_old_bitmap: HGDIOBJ | None = None
        self._cached_bits: wintypes.LPVOID | None = None

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

    def _free_dib(self) -> None:
        gdi32 = ctypes.windll.gdi32
        if self._cached_bitmap is not None and self._cached_memory_dc is not None and self._cached_old_bitmap is not None:
            gdi32.SelectObject(self._cached_memory_dc, self._cached_old_bitmap)
            gdi32.DeleteObject(self._cached_bitmap)
        if self._cached_memory_dc is not None:
            gdi32.DeleteDC(self._cached_memory_dc)
        self._cached_width = 0
        self._cached_height = 0
        self._cached_memory_dc = None
        self._cached_bitmap = None
        self._cached_old_bitmap = None
        self._cached_bits = None

    def destroy(self) -> None:
        self._free_dib()
        if self.hwnd:
            ctypes.windll.user32.DestroyWindow(self.hwnd)
            self.hwnd = None
        self.visible = False

    def update_pixels(self, bgra: bytes, width: int, height: int, x: int, y: int) -> None:
        if not self.hwnd:
            return
        if width <= 0 or height <= 0:
            return

        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        size_changed = width != self._cached_width or height != self._cached_height

        if size_changed:
            self._free_dib()
            bmi = BITMAPINFO()
            bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.bmiHeader.biWidth = width
            bmi.bmiHeader.biHeight = -height
            bmi.bmiHeader.biPlanes = 1
            bmi.bmiHeader.biBitCount = 32
            bmi.bmiHeader.biCompression = BI_RGB
            bmi.bmiHeader.biSizeImage = len(bgra)

            screen_dc = user32.GetDC(None)
            if not screen_dc:
                return
            memory_dc = gdi32.CreateCompatibleDC(screen_dc)
            if not memory_dc:
                user32.ReleaseDC(None, screen_dc)
                return
            bits = wintypes.LPVOID()
            bitmap = gdi32.CreateDIBSection(screen_dc, ctypes.byref(bmi), DIB_RGB_COLORS, ctypes.byref(bits), None, 0)
            if not bitmap:
                gdi32.DeleteDC(memory_dc)
                user32.ReleaseDC(None, screen_dc)
                return
            old_bitmap = gdi32.SelectObject(memory_dc, bitmap)
            user32.ReleaseDC(None, screen_dc)

            self._cached_width = width
            self._cached_height = height
            self._cached_memory_dc = memory_dc
            self._cached_bitmap = bitmap
            self._cached_old_bitmap = old_bitmap
            self._cached_bits = bits

            self._cached_bmi = bmi
        else:
            memory_dc = self._cached_memory_dc
            bits = self._cached_bits

        if bits:
            ctypes.memmove(bits, bgra, len(bgra))

        if memory_dc:
            destination = POINT(int(x), int(y))
            source = POINT(0, 0)
            size = SIZE(width, height)
            blend = BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)
            screen_dc = user32.GetDC(None)
            if screen_dc:
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
                user32.ReleaseDC(None, screen_dc)
        self.show()
