# -*- coding: utf-8 -*-
from __future__ import annotations

import ctypes
import math
import random
import sys
import time
import tkinter as tk
from collections import OrderedDict
from ctypes import wintypes
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Callable

try:
    import numpy as np
except Exception:  # pragma: no cover - NumPy is an optional speed path
    np = None

try:
    from PIL import Image, ImageChops, ImageDraw, ImageSequence, ImageTk
except Exception as exc:  # pragma: no cover - shown only on machines without Pillow
    messagebox.showerror("缺少依赖", f"需要安装 Pillow 才能播放 GIF：\n{exc}")
    raise


APP_TITLE = "猪猪指针"
GIF_NAME = "pig_pointer.gif"
ICON_NAME = "pig_pointer.ico"

WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WS_POPUP = 0x80000000
SW_HIDE = 0
SW_SHOWNOACTIVATE = 4
ULW_ALPHA = 0x00000002
AC_SRC_OVER = 0
AC_SRC_ALPHA = 1
BI_RGB = 0
DIB_RGB_COLORS = 0
WM_NCHITTEST = 0x0084
HTTRANSPARENT = -1
ERROR_CLASS_ALREADY_EXISTS = 1410
WM_NULL = 0x0000
WM_USER = 0x0400
WM_LBUTTONUP = 0x0202
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONUP = 0x0205
WM_CONTEXTMENU = 0x007B
WM_TRAYICON = WM_USER + 23
NIM_ADD = 0x00000000
NIM_DELETE = 0x00000002
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004
IMAGE_ICON = 1
LR_LOADFROMFILE = 0x00000010
LR_DEFAULTSIZE = 0x00000040
SM_CXSMICON = 49
SM_CYSMICON = 50
MF_STRING = 0x00000000
MF_SEPARATOR = 0x00000800
TPM_RIGHTBUTTON = 0x00000002
TPM_RETURNCMD = 0x00000100
TRAY_UID = 1
ID_TRAY_SHOW = 1001
ID_TRAY_TOGGLE = 1002
ID_TRAY_EXIT = 1003


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


LRESULT = ctypes.c_ssize_t
HCURSOR = getattr(wintypes, "HCURSOR", wintypes.HANDLE)
UINT_PTR = getattr(wintypes, "UINT_PTR", wintypes.WPARAM)
WNDPROC = ctypes.WINFUNCTYPE(
    LRESULT,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
)


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


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
        ("hIcon", wintypes.HICON),
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
        gdi32.CreateDIBSection.restype = wintypes.HBITMAP
        gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
        gdi32.SelectObject.restype = wintypes.HGDIOBJ
        gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
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

    def update_image(self, image: Image.Image, x: int, y: int) -> None:
        bgra = GifRenderer.to_premultiplied_bgra(image)
        self.update_pixels(bgra, image.width, image.height, x, y)


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", ctypes.c_wchar * 128),
    ]


class SystemTrayIcon:
    _api_ready = False
    _set_window_long_ptr = None

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
        self.hwnd = wintypes.HWND(root.winfo_id())
        self.hicon: int | None = None
        self.visible = False
        self._old_wndproc: int | None = None
        self._wndproc_ref = WNDPROC(self._window_proc)

        if sys.platform == "win32":
            self._configure_api()
            self._subclass_window()

    @classmethod
    def _configure_api(cls) -> None:
        if cls._api_ready:
            return

        user32 = ctypes.windll.user32
        shell32 = ctypes.windll.shell32

        shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]
        shell32.Shell_NotifyIconW.restype = wintypes.BOOL

        user32.LoadImageW.argtypes = [
            wintypes.HINSTANCE,
            wintypes.LPCWSTR,
            wintypes.UINT,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.UINT,
        ]
        user32.LoadImageW.restype = wintypes.HANDLE
        user32.DestroyIcon.argtypes = [wintypes.HICON]
        user32.DestroyIcon.restype = wintypes.BOOL
        user32.GetSystemMetrics.argtypes = [ctypes.c_int]
        user32.GetSystemMetrics.restype = ctypes.c_int
        user32.CallWindowProcW.argtypes = [
            ctypes.c_void_p,
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        user32.CallWindowProcW.restype = LRESULT
        user32.CreatePopupMenu.argtypes = []
        user32.CreatePopupMenu.restype = wintypes.HMENU
        user32.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT, UINT_PTR, wintypes.LPCWSTR]
        user32.AppendMenuW.restype = wintypes.BOOL
        user32.TrackPopupMenu.argtypes = [
            wintypes.HMENU,
            wintypes.UINT,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.HWND,
            wintypes.LPVOID,
        ]
        user32.TrackPopupMenu.restype = wintypes.UINT
        user32.DestroyMenu.argtypes = [wintypes.HMENU]
        user32.DestroyMenu.restype = wintypes.BOOL
        user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
        user32.GetCursorPos.restype = wintypes.BOOL
        user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        user32.SetForegroundWindow.restype = wintypes.BOOL
        user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user32.PostMessageW.restype = wintypes.BOOL

        if ctypes.sizeof(ctypes.c_void_p) == 8:
            cls._set_window_long_ptr = user32.SetWindowLongPtrW
        else:
            cls._set_window_long_ptr = user32.SetWindowLongW
        cls._set_window_long_ptr.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        cls._set_window_long_ptr.restype = ctypes.c_void_p

        cls._api_ready = True

    def _subclass_window(self) -> None:
        if self._old_wndproc is not None or self._set_window_long_ptr is None:
            return
        new_wndproc = ctypes.cast(self._wndproc_ref, ctypes.c_void_p)
        self._old_wndproc = self._set_window_long_ptr(self.hwnd, -4, new_wndproc)

    def _window_proc(
        self,
        hwnd: wintypes.HWND,
        msg: wintypes.UINT,
        wparam: wintypes.WPARAM,
        lparam: wintypes.LPARAM,
    ) -> int:
        if msg == WM_TRAYICON and int(wparam) == TRAY_UID:
            event = int(lparam) & 0xFFFF
            if event in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
                self.root.after(0, self.on_show)
                return 0
            if event in (WM_RBUTTONUP, WM_CONTEXTMENU):
                self.root.after(0, self._show_menu)
                return 0

        if self._old_wndproc:
            return ctypes.windll.user32.CallWindowProcW(
                self._old_wndproc,
                hwnd,
                msg,
                wparam,
                lparam,
            )
        return ctypes.windll.user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _load_icon(self) -> int | None:
        if not self.icon_path.exists():
            return None
        user32 = ctypes.windll.user32
        width = user32.GetSystemMetrics(SM_CXSMICON) or 16
        height = user32.GetSystemMetrics(SM_CYSMICON) or 16
        hicon = user32.LoadImageW(None, str(self.icon_path), IMAGE_ICON, width, height, LR_LOADFROMFILE)
        if not hicon:
            hicon = user32.LoadImageW(None, str(self.icon_path), IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE)
        return int(hicon) if hicon else None

    def _notify_data(self) -> NOTIFYICONDATAW:
        data = NOTIFYICONDATAW()
        data.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        data.hWnd = self.hwnd
        data.uID = TRAY_UID
        data.uFlags = NIF_MESSAGE | NIF_TIP
        data.uCallbackMessage = WM_TRAYICON
        data.szTip = APP_TITLE[:127]
        if self.hicon:
            data.uFlags |= NIF_ICON
            data.hIcon = self.hicon
        return data

    def show(self) -> None:
        if sys.platform != "win32" or self.visible:
            return
        if self.hicon is None:
            self.hicon = self._load_icon()
        data = self._notify_data()
        if ctypes.windll.shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(data)):
            self.visible = True

    def hide(self) -> None:
        if sys.platform != "win32" or not self.visible:
            return
        data = NOTIFYICONDATAW()
        data.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        data.hWnd = self.hwnd
        data.uID = TRAY_UID
        ctypes.windll.shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(data))
        self.visible = False

    def destroy(self) -> None:
        self.hide()
        if self._old_wndproc is not None and self._set_window_long_ptr is not None:
            try:
                self._set_window_long_ptr(self.hwnd, -4, ctypes.c_void_p(self._old_wndproc))
            except Exception:
                pass
            self._old_wndproc = None
        if self.hicon:
            ctypes.windll.user32.DestroyIcon(self.hicon)
            self.hicon = None

    def _show_menu(self) -> None:
        if not self.visible:
            return
        user32 = ctypes.windll.user32
        menu = user32.CreatePopupMenu()
        if not menu:
            return
        try:
            user32.AppendMenuW(menu, MF_STRING, ID_TRAY_SHOW, "打开面板")
            toggle_text = "关闭小猪" if self.is_running() else "启动小猪"
            user32.AppendMenuW(menu, MF_STRING, ID_TRAY_TOGGLE, toggle_text)
            user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
            user32.AppendMenuW(menu, MF_STRING, ID_TRAY_EXIT, "退出软件")
            point = POINT()
            user32.GetCursorPos(ctypes.byref(point))
            user32.SetForegroundWindow(self.hwnd)
            command = user32.TrackPopupMenu(
                menu,
                TPM_RIGHTBUTTON | TPM_RETURNCMD,
                point.x,
                point.y,
                0,
                self.hwnd,
                None,
            )
            user32.PostMessageW(self.hwnd, WM_NULL, 0, 0)
        finally:
            user32.DestroyMenu(menu)

        if command:
            self.root.after(0, self._dispatch_command, int(command))

    def _dispatch_command(self, command: int) -> None:
        if command == ID_TRAY_SHOW:
            self.on_show()
        elif command == ID_TRAY_TOGGLE:
            self.on_toggle()
        elif command == ID_TRAY_EXIT:
            self.on_exit()


def _resample_filter() -> int:
    return getattr(Image, "Resampling", Image).LANCZOS


class GifRenderer:
    def __init__(self, gif_path: Path, tk_master: tk.Misc) -> None:
        self.gif_path = gif_path
        self.tk_master = tk_master
        self.frames: list[Image.Image] = []
        self.durations: list[int] = []
        self.frame_joints: list[tuple[float, float]] = []
        self.body_joints: list[tuple[float, float]] = []
        self.base_size = (1, 1)
        self._cache: OrderedDict[
            tuple[int, int, int],
            tuple[Image.Image, tuple[float, float], bytes],
        ] = OrderedDict()
        self._photo_cache: OrderedDict[tuple[int, int, int], tuple[ImageTk.PhotoImage, tuple[float, float]]] = OrderedDict()
        self._load_gif()

    def _load_gif(self) -> None:
        source = Image.open(self.gif_path)
        raw_frames = [frame.convert("RGBA") for frame in ImageSequence.Iterator(source)]
        if not raw_frames:
            raise ValueError("GIF 中没有可播放的帧")

        crop_box = self._union_bbox(raw_frames)
        source_frames = [frame.crop(crop_box) for frame in raw_frames]
        source_joints = [self._find_top_rope_joint(frame) for frame in source_frames]
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
        self.frame_joints = []
        self.durations = []
        for index, frame in enumerate(source_frames):
            joint = source_joints[index]
            body_frame = body_frames[index]
            body_joint = body_joints[index]

            self.frames.append(body_frame)
            self.frame_joints.append(joint)
            self.body_joints.append(body_joint)
            self.durations.append(source_durations[index])

        forward_frames = self.frames
        forward_joints = self.frame_joints
        forward_body_joints = self.body_joints
        forward_durations = self.durations
        self.frames = forward_frames + forward_frames[-2::-1]
        self.frame_joints = forward_joints + forward_joints[-2::-1]
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

    @classmethod
    def _find_body_rope_joint(cls, frame: Image.Image, fallback: tuple[float, float]) -> tuple[float, float]:
        pixels = frame.load()
        start_y = max(80, int(fallback[1]) + 70)
        end_y = min(frame.height, start_y + 90)
        for y in range(start_y, end_y):
            xs = []
            for x in range(frame.width):
                red, green, blue, alpha = pixels[x, y]
                if cls._is_rope_pixel(red, green, blue, alpha):
                    xs.append(x)
            if xs:
                return (sum(xs) / len(xs), float(y))
        return fallback

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
        self, frame_index: int, display_height: int, angle: float
    ) -> tuple[Image.Image, tuple[float, float], bytes]:
        display_height = max(36, min(320, int(display_height)))
        angle_key = int(round(angle / 2.0) * 2)
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
        while len(self._cache) > 520:
            self._cache.popitem(last=False)
        return result

    def render_pil(self, frame_index: int, display_height: int, angle: float) -> tuple[Image.Image, tuple[float, float]]:
        image, joint, _bgra = self.render_asset(frame_index, display_height, angle)
        return image, joint

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


class PigPointerApp:
    def __init__(self, root: tk.Tk, gif_path: Path) -> None:
        self.root = root
        self.app_dir = gif_path.parent
        self.renderer = GifRenderer(gif_path, root)

        self.running = False
        self.overlay: AlphaOverlay | None = None
        self.tray_icon: SystemTrayIcon | None = None
        self.preview_photo: ImageTk.PhotoImage | None = None
        self.preview_last_time = 0.0
        self.overlay_last_draw_time = 0.0

        self.size_var = tk.DoubleVar(value=150)
        self.prob_var = tk.DoubleVar(value=15)
        self.anchor_x_var = tk.DoubleVar(value=24)
        self.anchor_y_var = tk.DoubleVar(value=30)
        self.anim_speed_var = tk.DoubleVar(value=1.6)
        self.trigger_interval_var = tk.DoubleVar(value=4.0)
        self.weight_var = tk.DoubleVar(value=70)
        self.background_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="准备就绪")
        self.size_text = tk.StringVar()
        self.prob_text = tk.StringVar()
        self.anchor_x_text = tk.StringVar()
        self.anchor_y_text = tk.StringVar()
        self.anim_speed_text = tk.StringVar()
        self.trigger_interval_text = tk.StringVar()
        self.weight_text = tk.StringVar()
        self.rope_length_var = tk.DoubleVar(value=72)
        self.rope_length_text = tk.StringVar()

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
        self.root.resizable(False, True)
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

        ttk.Label(outer, text=APP_TITLE, style="Title.TLabel").pack(anchor="w")
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
        ).pack(anchor="w", pady=(0, 14))

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

        self._add_slider(outer, "GIF 大小", self.size_var, 70, 260, self.size_text)
        self._add_slider(outer, "绳子长度", self.rope_length_var, 36, 160, self.rope_length_text)
        self._add_slider(outer, "重量感", self.weight_var, 0, 100, self.weight_text)
        self._add_slider(outer, "动画触发概率", self.prob_var, 0, 100, self.prob_text)
        self._add_slider(outer, "动画播放速度", self.anim_speed_var, 0.5, 3.0, self.anim_speed_text)
        self._add_slider(outer, "触发间隔", self.trigger_interval_var, 1.0, 20.0, self.trigger_interval_text)
        self._add_slider(outer, "绑定点横向", self.anchor_x_var, -30, 80, self.anchor_x_text)
        self._add_slider(outer, "绑定点纵向", self.anchor_y_var, -20, 90, self.anchor_y_text)

        ttk.Separator(outer).pack(fill="x", pady=(14, 10))
        status_row = ttk.Frame(outer)
        status_row.pack(fill="x")
        ttk.Label(status_row, textvariable=self.status_var, style="Status.TLabel").pack(side="left")
        ttk.Button(status_row, text="退出软件", command=self.quit_app).pack(side="right")

        self._update_buttons()

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
            command=lambda _value: self._sync_slider_labels(),
        ).pack(fill="x")

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

    def _sync_slider_labels(self) -> None:
        self.size_text.set(f"{int(self.size_var.get())} px")
        self.prob_text.set(f"{int(self.prob_var.get())}%")
        self.anchor_x_text.set(f"{int(self.anchor_x_var.get()):+d} px")
        self.anchor_y_text.set(f"{int(self.anchor_y_var.get()):+d} px")
        self.rope_length_text.set(f"{int(self.rope_length_var.get())} px")
        self.weight_text.set(f"{int(self.weight_var.get())}%")
        self.anim_speed_text.set(f"{self.anim_speed_var.get():.1f}x")
        self.trigger_interval_text.set(f"{self.trigger_interval_var.get():.0f} s")

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
        for angle in range(-44, 45, 4):
            self.renderer.render_asset(0, size, angle)

    def _update_buttons(self) -> None:
        self.start_button.state(["disabled"] if self.running else ["!disabled"])
        self.stop_button.state(["!disabled"] if self.running else ["disabled"])
        self.hide_button.state(["!disabled"] if self.running else ["disabled"])
        self.status_var.set("运行中：小猪正在跟随鼠标" if self.running else "已关闭：可随时重新启动")

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
        self.animation_active = True
        self.frame_index = 0
        self.frame_time_ms = 0.0
        self.trigger_timer = 0.0

    def start_pet(self) -> None:
        if self.running:
            return
        self.running = True
        self._prewarm_current_static_angles()
        self._place_physics_at_cursor()
        self._update_buttons()

    def stop_pet(self) -> None:
        if not self.running:
            return
        self.running = False
        if self.overlay is not None:
            self.overlay.hide()
        self.rope_vel_x = self.rope_vel_y = 0.0
        self.pig_vel_x = self.pig_vel_y = 0.0
        self.pig_angular_velocity = 0.0
        self.animation_active = False
        self.frame_index = 0
        self.frame_time_ms = 0.0
        self._update_buttons()

    def hide_to_background(self) -> None:
        if not self.running:
            return
        self.background_var.set(True)
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
        if self.tray_icon is not None:
            self.tray_icon.destroy()
            self.tray_icon = None
        if self.overlay is not None:
            self.overlay.destroy()
            self.overlay = None
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

    def _place_physics_at_cursor(self) -> None:
        anchor_x, anchor_y = self._cursor_anchor()
        rope_length = self._rope_length()
        self.rope_end_x = anchor_x
        self.rope_end_y = anchor_y + rope_length
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

    def _cursor_anchor(self) -> tuple[float, float]:
        pointer_x, pointer_y = self.root.winfo_pointerxy()
        return (pointer_x + self.anchor_x_var.get(), pointer_y + self.anchor_y_var.get())

    def _rest_length(self) -> float:
        return max(38.0, self.size_var.get() * 0.43)

    def _rope_length(self) -> float:
        return max(20.0, self.rope_length_var.get())

    def _weight_factor(self) -> float:
        return max(0.0, min(1.0, self.weight_var.get() / 100.0))

    def _tick(self) -> None:
        now = time.perf_counter()
        dt = min(0.018, max(0.001, now - self.last_tick))
        self.last_tick = now

        self._advance_animation(dt)
        if not self.running and now - self.last_prewarm_time >= 0.025:
            self._prewarm_one_asset()
            self.last_prewarm_time = now
        if now - self.preview_last_time >= 1 / 20:
            self._draw_preview(now)
            self.preview_last_time = now
        if self.running:
            self._update_physics(dt)
            if now - self.overlay_last_draw_time >= 1 / 60:
                self._draw_overlay()
                self.overlay_last_draw_time = now

        self.root.after(5, self._tick)

    def _advance_animation(self, dt: float) -> None:
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

    def _update_physics(self, dt: float) -> None:
        if not self.initialized_physics:
            self._place_physics_at_cursor()

        anchor_x, anchor_y = self._cursor_anchor()
        last_x, last_y = self.last_anchor
        cursor_vx = (anchor_x - last_x) / dt
        cursor_vy = (anchor_y - last_y) / dt
        self.last_anchor = (anchor_x, anchor_y)
        self.last_cursor_velocity = (cursor_vx, cursor_vy)

        rope_length = self._rope_length()
        weight = self._weight_factor()
        dx = self.rope_end_x - anchor_x
        dy = self.rope_end_y - anchor_y
        distance = max(1.0, math.hypot(dx, dy))
        nx = dx / distance
        ny = dy / distance

        tangent_x = -ny
        tangent_y = nx
        tangent_velocity = self.rope_vel_x * tangent_x + self.rope_vel_y * tangent_y
        anchor_tangent_velocity = cursor_vx * tangent_x + cursor_vy * tangent_y

        rope_damping = 10.5 - 6.2 * weight
        cursor_coupling = 0.44 + 0.34 * weight
        gravity_strength = 1080.0 + 620.0 * weight
        tangential_force = -rope_damping * (tangent_velocity - anchor_tangent_velocity * cursor_coupling)
        gravity_force = gravity_strength * tangent_y

        self.rope_vel_x += (tangential_force + gravity_force) * tangent_x * dt
        self.rope_vel_y += (tangential_force + gravity_force) * tangent_y * dt
        max_rope_speed = 1400.0 + 700.0 * weight
        rope_speed = math.hypot(self.rope_vel_x, self.rope_vel_y)
        if rope_speed > max_rope_speed:
            scale = max_rope_speed / rope_speed
            self.rope_vel_x *= scale
            self.rope_vel_y *= scale
        self.rope_end_x += self.rope_vel_x * dt
        self.rope_end_y += self.rope_vel_y * dt

        dx = self.rope_end_x - anchor_x
        dy = self.rope_end_y - anchor_y
        distance = max(1.0, math.hypot(dx, dy))
        self.rope_end_x = anchor_x + dx / distance * rope_length
        self.rope_end_y = anchor_y + dy / distance * rope_length

        radial_velocity = self.rope_vel_x * (dx / distance) + self.rope_vel_y * (dy / distance)
        self.rope_vel_x -= radial_velocity * (dx / distance)
        self.rope_vel_y -= radial_velocity * (dy / distance)

        self.pig_x = self.rope_end_x
        self.pig_y = self.rope_end_y
        self.pig_vel_x = self.rope_vel_x
        self.pig_vel_y = self.rope_vel_y

        target_angle = max(
            -48.0,
            min(48.0, self.rope_vel_x * (0.026 + 0.024 * weight) + cursor_vx * (0.003 + 0.006 * weight)),
        )
        target_angle = math.radians(target_angle)
        rotation_spring = 28.0 - 11.0 * weight
        rotation_damping = 9.5 - 5.5 * weight
        self.pig_angular_velocity += (target_angle - self.pig_angle) * rotation_spring * dt
        self.pig_angular_velocity *= max(0.0, 1.0 - rotation_damping * dt)
        self.pig_angle += self.pig_angular_velocity * dt

    def _draw_overlay(self) -> None:
        if self.overlay is None:
            return
        display_height = int(self.size_var.get())
        angle = math.degrees(self.pig_angle)
        image, joint, _bgra = self.renderer.render_asset(self.frame_index, display_height, angle)
        anchor_x, anchor_y = self.last_anchor
        image_x = self.pig_x - joint[0]
        image_y = self.pig_y - joint[1]

        margin = max(18, int(display_height * 0.2))
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
        draw.line(points, fill=(116, 77, 45, 245), width=max(2, int(display_height * 0.028)), joint="curve")
        composite.alpha_composite(image, (int(round(image_x - left)), int(round(image_y - top))))
        bgra = GifRenderer.to_premultiplied_bgra(composite)
        self.overlay.update_pixels(bgra, composite.width, composite.height, left, top)

    def _draw_preview(self, now: float) -> None:
        width = int(self.preview["width"])
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
        self.preview.itemconfigure(self.preview_image, image=photo)


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
