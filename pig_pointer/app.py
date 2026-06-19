# -*- coding: utf-8 -*-
"""Main application class — PigPointerApp and entry point."""

from __future__ import annotations

import json
import math
import os
import random
import shutil
import sys
import time
import tkinter as tk
import uuid
from collections import OrderedDict
from ctypes import wintypes
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk
from typing import Callable

from pig_pointer.constants import (
    APP_TITLE,
    CUSTOM_ASSETS_DIR_NAME,
    CUSTOM_ASSET_SUFFIXES,
    CUSTOM_ATTACH_AUTO,
    CUSTOM_ATTACH_FIXED,
    CUSTOM_ATTACH_MODES,
    CUSTOM_CONNECTION_CHAIN,
    CUSTOM_CONNECTION_MODES,
    CUSTOM_CONNECTION_MOUSE,
    CUSTOM_RESOURCE_PRESETS,
    DEFAULT_CUSTOM_ASSET_SETTINGS,
    DEFAULT_GLOBAL_SETTINGS,
    DEFAULT_PIG_CUSTOM_ID,
    GIF_NAME,
    ICON_NAME,
    ICON_BIG,
    ICON_SMALL,
    ICON_SMALL2,
    GWL_STYLE,
    PERFORMANCE_PROFILES,
    PerformanceProfile,
    ROPE_COLORS,
    SETTINGS_VERSION,
    SMART_PERFORMANCE_MODE,
    SM_CXICON,
    SM_CXSMICON,
    SM_CYICON,
    SM_CYSMICON,
    WS_MAXIMIZEBOX,
    WM_SETICON,
)
from pig_pointer.renderers import (
    CustomAssetConfig,
    CustomAssetRenderer,
    CustomItemState,
    CustomRenderedItem,
    GifRenderer,
    _resample_filter,
)
from pig_pointer.tray import SystemTrayIcon
from pig_pointer.utils import (
    _clamp,
    _clamp_int,
    _default_assets_dir,
    _is_hex_color,
    _load_settings_file,
    _normalize_performance_mode,
    _performance_profile,
    _resource_path,
    _safe_asset_name,
    _settings_path,
    _unique_asset_path,
)
from pig_pointer.win32 import (
    AlphaOverlay,
    CursorVisibilityGuard,
    POINT,
    _capture_system_cursor,
    _enable_dpi_awareness,
    _is_startup_enabled,
    _load_windows_icon,
    _set_startup_enabled,
    _set_windows_app_id,
)

try:
    import numpy as np
except Exception:
    np = None

try:
    from PIL import Image, ImageDraw, ImageTk
except Exception as exc:
    messagebox.showerror("缺少依赖", f"需要安装 Pillow 才能播放 GIF：\n{exc}")
    raise
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
        self.custom_animation_controls: list[tk.Widget] = []
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
        self.last_overlay_draw_time = 0.0
        self.overlay_dirty = True
        self.composite_canvas: Image.Image | None = None
        self._last_draw_sig: object | None = None
        self._bgra_buffer: np.ndarray | None = None
        self._bgra_buffer_shape: tuple[int, int] | None = None
        self.average_draw_ms = 0.0
        self.last_draw_ms = 0.0
        self.average_physics_ms = 0.0
        self.last_physics_ms = 0.0
        self.average_collision_ms = 0.0
        self.last_collision_ms = 0.0
        self.collision_accumulator = 0.0
        self.custom_prewarm_jobs: list[tuple[str, int, int, int]] = []
        self.custom_prewarm_signature: tuple[object, ...] | None = None
        self.last_custom_prewarm_time = 0.0
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
        for mode in ("高性能", "普通", SMART_PERFORMANCE_MODE):
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
    ) -> ttk.Scale:
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(8, 0))
        ttk.Label(row, text=title).pack(side="left")
        ttk.Label(row, textvariable=label_var, foreground="#6c625c").pack(side="right")
        change_command = command or self._on_custom_item_setting_changed
        scale = ttk.Scale(
            parent,
            variable=variable,
            from_=minimum,
            to=maximum,
            command=lambda _value: change_command(),
        )
        scale.pack(fill="x")
        return scale

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
        self.custom_anim_speed_scale = self._add_custom_slider(
            self.custom_editor,
            "动画播放速度",
            self.custom_item_anim_speed_var,
            0.2,
            4.0,
            self.custom_item_anim_speed_text,
        )
        self.custom_probability_scale = self._add_custom_slider(
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
        self.custom_always_animate_check = ttk.Checkbutton(
            self.custom_editor,
            text="动画连续播放",
            variable=self.custom_item_always_animate_var,
            command=self._on_custom_item_setting_changed,
        )
        self.custom_always_animate_check.pack(anchor="w", pady=(8, 0))
        self.custom_reverse_loop_check = ttk.Checkbutton(
            self.custom_editor,
            text="动画往返循环",
            variable=self.custom_item_reverse_loop_var,
            command=self._on_custom_item_setting_changed,
        )
        self.custom_reverse_loop_check.pack(anchor="w", pady=(4, 0))
        self.custom_animation_controls = [
            self.custom_anim_speed_scale,
            self.custom_probability_scale,
            self.custom_always_animate_check,
            self.custom_reverse_loop_check,
        ]
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
        if not isinstance(value, str):
            return default
        normalized_value = _normalize_performance_mode(value)
        return normalized_value if normalized_value in PERFORMANCE_PROFILES else default

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
            self._refresh_custom_asset_stats(asset)
            assets.append(asset)
        return assets

    def _refresh_custom_asset_stats(self, asset: CustomAssetConfig, renderer: CustomAssetRenderer | None = None) -> None:
        path = Path(asset.path).expanduser()
        if not path.exists():
            return
        if renderer is not None:
            asset.source_width = int(renderer.source_size[0])
            asset.source_height = int(renderer.source_size[1])
            asset.trimmed_width = int(renderer.base_size[0])
            asset.trimmed_height = int(renderer.base_size[1])
            asset.frame_count = int(max(1, renderer.source_frame_count))
            asset.file_size = int(renderer.file_size)
            asset.estimated_pixels = int(renderer.estimated_pixels)
            asset.is_animated = asset.frame_count > 1
            return
        try:
            with Image.open(path) as source:
                source_width, source_height = source.size
                frame_count = max(1, int(getattr(source, "n_frames", 1) or 1))
            file_size = path.stat().st_size
        except Exception:
            return

        if renderer is not None and renderer.base_size != (1, 1):
            trimmed_width, trimmed_height = renderer.base_size
            frame_count = max(frame_count, len(renderer.frames))
        else:
            trimmed_width = asset.trimmed_width or source_width
            trimmed_height = asset.trimmed_height or source_height

        asset.source_width = int(source_width)
        asset.source_height = int(source_height)
        asset.trimmed_width = int(trimmed_width)
        asset.trimmed_height = int(trimmed_height)
        asset.frame_count = int(frame_count)
        asset.file_size = int(file_size)
        asset.estimated_pixels = int(max(1, trimmed_width) * max(1, trimmed_height) * max(1, frame_count))
        asset.is_animated = asset.frame_count > 1

    def _on_setting_changed(self) -> None:
        self._sync_slider_labels()
        self._schedule_save_settings()

    def _schedule_save_settings(self) -> None:
        self.overlay_dirty = True
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
        assets_by_id = {asset.asset_id: asset for asset in self._custom_asset_choices()}
        for asset_id, renderer in self.custom_renderers.items():
            asset = assets_by_id.get(asset_id)
            if asset is not None:
                renderer.cache_limit = self._custom_renderer_cache_limit(asset)

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
        self._sync_custom_animation_controls()
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
            is_animated=True,
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

    @staticmethod
    def _custom_asset_is_animated(asset: CustomAssetConfig) -> bool:
        return asset.asset_id == DEFAULT_PIG_CUSTOM_ID or asset.is_animated or asset.frame_count > 1

    def _selected_custom_assets_have_animation(self) -> bool:
        return any(self._custom_asset_is_animated(asset) for asset in self._selected_custom_assets())

    def _sync_custom_animation_controls(self) -> None:
        enabled = self._selected_custom_assets_have_animation()
        state = ["!disabled"] if enabled else ["disabled"]
        for control in self.custom_animation_controls:
            try:
                control.state(state)
            except tk.TclError:
                pass

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

    @staticmethod
    def _custom_asset_detail_text(asset: CustomAssetConfig) -> str:
        if asset.asset_id == DEFAULT_PIG_CUSTOM_ID or asset.source_width <= 0 or asset.source_height <= 0:
            return ""
        kind = "动画" if asset.is_animated else "图片"
        frame_text = f"，{asset.frame_count}帧" if asset.frame_count > 1 else ""
        return f"（{kind} {asset.source_width}x{asset.source_height}{frame_text}）"

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
            detail = self._custom_asset_detail_text(asset)
            self.custom_listbox.insert(tk.END, f"{index + 1}. [{marker}] {asset.name}{detail}{missing}")
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
                base += " 提醒：" + "；".join(notes[:3]) + "。"
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

        frame_counts: list[int] = []
        total_estimated_pixels = 0
        large_sources = 0
        long_gifs = 0
        heavy_always_animate = 0
        for asset in active_assets:
            if asset.asset_id == DEFAULT_PIG_CUSTOM_ID:
                frame_count = self.renderer.frame_count
                estimated_pixels = self.renderer.base_size[0] * self.renderer.base_size[1] * max(1, frame_count)
                source_width, source_height = self.renderer.base_size
                file_size = _resource_path(GIF_NAME).stat().st_size if _resource_path(GIF_NAME).exists() else 0
            else:
                if asset.source_width <= 0 or asset.frame_count <= 0:
                    self._refresh_custom_asset_stats(asset)
                frame_count = max(1, asset.frame_count)
                source_width, source_height = asset.source_width, asset.source_height
                estimated_pixels = asset.estimated_pixels or source_width * source_height * frame_count
                file_size = asset.file_size
            frame_counts.append(frame_count)
            total_estimated_pixels += estimated_pixels
            if max(source_width, source_height) >= 1200 or file_size >= 18 * 1024 * 1024:
                large_sources += 1
            if frame_count >= 120:
                long_gifs += 1
            if asset.always_animate and frame_count >= 50:
                heavy_always_animate += 1
        total_frames = sum(frame_counts)
        gif_count = sum(1 for count in frame_counts if count > 1)
        if total_estimated_pixels >= 80_000_000:
            notes.append("素材帧像素量很高，建议换小一点的动画素材")
        elif total_estimated_pixels >= 36_000_000:
            notes.append("素材帧像素量偏高，智能性能更合适")
        if large_sources:
            notes.append("有大尺寸或大文件素材，建议先缩小")
        if long_gifs:
            notes.append("存在长动画，连续播放会增加缓存压力")
        if heavy_always_animate >= 2:
            notes.append("多个长动画连续播放，建议暂停一部分")
        if total_frames >= 180:
            notes.append("动画帧数多，缓存占用会增加")
        elif gif_count >= 4:
            notes.append("动画素材较多，触发过密会显得卡")

        if self.custom_collision_var.get():
            collision_pairs = active_count * (active_count - 1) // 2
            if collision_pairs >= 45:
                notes.append("碰撞对象多，已用分桶优化，关闭仍会更省")
            elif collision_pairs >= 21:
                notes.append("碰撞对象较多，分桶会减少无效检查")
        elif active_count >= 2:
            notes.append("资源碰撞已关闭，会更省但可能互相穿过")

        high_probability = sum(
            1
            for asset, frame_count in zip(active_assets, frame_counts)
            if asset.probability >= 60 and frame_count > 1
        )
        if high_probability >= 3:
            notes.append("多个动画触发概率很高，建议拉开触发间隔")
        return notes

    @staticmethod
    def _custom_import_notes(assets: list[CustomAssetConfig]) -> list[str]:
        notes: list[str] = []
        heavy_assets = [asset for asset in assets if asset.estimated_pixels >= 40_000_000]
        long_gifs = [asset for asset in assets if asset.frame_count >= 120]
        large_files = [asset for asset in assets if asset.file_size >= 18 * 1024 * 1024]
        large_dimensions = [asset for asset in assets if max(asset.source_width, asset.source_height) >= 1200]
        if heavy_assets:
            notes.append(f"{len(heavy_assets)} 个素材帧像素量较高，建议降低尺寸或帧数")
        if long_gifs:
            notes.append(f"{len(long_gifs)} 个动画素材帧数较多，连续播放时更吃缓存")
        if large_files:
            notes.append(f"{len(large_files)} 个素材文件较大，加载和备份会更慢")
        if large_dimensions:
            notes.append(f"{len(large_dimensions)} 个素材源尺寸较大，显示前会有额外缩放开销")
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
            target.collision_radius = _clamp(self.custom_item_collision_var.get(), 8, 180, 46)
            target.weight = _clamp(self.custom_item_weight_var.get(), 0, 100, 70)
            if self._custom_asset_is_animated(target):
                target.anim_speed = _clamp(self.custom_item_anim_speed_var.get(), 0.2, 4.0, 1.0)
                target.probability = _clamp(self.custom_item_probability_var.get(), 0, 100, 10)
                target.reverse_loop = self.custom_item_reverse_loop_var.get()
                target.always_animate = self.custom_item_always_animate_var.get()
            else:
                target.always_animate = False
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
                self._refresh_custom_asset_stats(asset)
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
        added_assets: list[CustomAssetConfig] = []
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
            temp_asset = CustomAssetConfig(
                asset_id=asset_id,
                name=source.name,
                path=str(target),
                size=float(self.size_var.get()),
                rope_length=float(self.rope_length_var.get()),
                probability=float(self.prob_var.get()),
                anim_speed=float(self.anim_speed_var.get()),
                weight=float(self.weight_var.get()),
                rope_width=float(self.rope_width_var.get()),
                always_animate=False,
            )
            self._refresh_custom_asset_stats(temp_asset, renderer)
            temp_asset.always_animate = temp_asset.is_animated
            self.custom_renderers[asset_id] = renderer
            self.custom_assets.append(temp_asset)
            added_assets.append(temp_asset)
            self.custom_selected_id.set(asset_id)
            self.custom_selected_ids = {asset_id}
            added += 1
        if skipped and not added:
            messagebox.showinfo("没有添加素材", "请选择 gif、png、jpg、jpeg、webp 或 bmp 文件。")
        import_notes = self._custom_import_notes(added_assets)
        if import_notes:
            messagebox.showinfo("素材预处理完成", "已完成素材预处理：\n" + "\n".join(f"- {note}" for note in import_notes), parent=self.root)
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

    def _custom_asset_frame_count_hint(self, asset: CustomAssetConfig) -> int:
        if not self._custom_asset_is_animated(asset):
            return 1
        if asset.asset_id == DEFAULT_PIG_CUSTOM_ID:
            return self.renderer.frame_count
        frame_count = max(1, asset.frame_count)
        if asset.reverse_loop and frame_count > 2:
            return frame_count * 2 - 2
        return frame_count

    def _prepare_custom_prewarm_jobs(self, force: bool = False) -> None:
        active_assets = self._active_custom_assets()
        profile = self._current_performance_profile()
        signature = tuple(
            (
                asset.asset_id,
                int(asset.size),
                self._custom_asset_frame_count_hint(asset),
                asset.reverse_loop,
                asset.attach_mode,
                round(asset.attach_x, 1),
                round(asset.attach_y, 1),
                profile.angle_step,
            )
            for asset in active_assets
            if self._custom_asset_frame_count_hint(asset) > 1
        )
        if not force and signature == self.custom_prewarm_signature:
            return
        self.custom_prewarm_signature = signature
        jobs: list[tuple[str, int, int, int]] = []
        for asset in active_assets:
            frame_count = self._custom_asset_frame_count_hint(asset)
            if frame_count <= 1:
                continue
            size = int(asset.size)
            angles = (0, -12, 12)
            first_frames = list(range(min(frame_count, 12)))
            sample_step = max(1, frame_count // 12)
            sampled_frames = list(range(0, frame_count, sample_step))[:12]
            frames = list(dict.fromkeys(first_frames + sampled_frames))
            for frame in frames:
                for angle in angles:
                    jobs.append((asset.asset_id, frame, size, angle))
        self.custom_prewarm_jobs = jobs

    def _prewarm_one_custom_asset(self) -> bool:
        while self.custom_prewarm_jobs:
            asset_id, frame, size, angle = self.custom_prewarm_jobs.pop(0)
            asset = next((item for item in self._active_custom_assets() if item.asset_id == asset_id), None)
            if asset is None:
                continue
            rendered = self._render_custom_asset(asset, frame, size, angle, self._current_performance_profile().angle_step)
            return rendered is not None
        return False

    def _maybe_prewarm_custom_assets(self, now: float, profile: PerformanceProfile, motion_active: bool) -> None:
        if not self.custom_mode_var.get() or now - self.last_custom_prewarm_time < 0.025:
            return
        self._prepare_custom_prewarm_jobs()
        if not self.custom_prewarm_jobs:
            return
        if self.running and (motion_active or self.average_draw_ms >= 10.0 or self.average_physics_ms >= 6.0):
            return
        self._prewarm_one_custom_asset()
        self.last_custom_prewarm_time = now

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
            self._prepare_custom_prewarm_jobs(force=True)
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
        self.last_overlay_draw_time = 0.0
        self.overlay_dirty = True
        self._prewarm_current_static_angles()
        if self.custom_mode_var.get():
            self._prepare_custom_prewarm_jobs(force=True)
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
        self.last_overlay_draw_time = 0.0
        self.overlay_dirty = True
        self.collision_accumulator = 0.0
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

        # Ensure the window is initialized before setting icons
        try:
            window.update_idletasks()
        except Exception:
            pass

        # Method 1: Tk iconbitmap (most reliable for .ico on Windows)
        try:
            window.iconbitmap(default=str(icon_path))
        except tk.TclError:
            pass

        # Method 2: PIL-based iconphoto (better HiDPI support)
        try:
            icon_source = Image.open(icon_path)
            source_sizes = sorted(icon_source.ico.sizes()) if icon_source.format == "ICO" else [icon_source.size]
            photos: list[ImageTk.PhotoImage] = []
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

        # Method 3: Win32 native WM_SETICON
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
        self.collision_accumulator = 0.0
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

    def _animation_signature(self) -> tuple[object, ...]:
        if self.custom_mode_var.get():
            signature: list[object] = []
            for asset in self._active_custom_assets():
                state = self.custom_states.get(asset.asset_id)
                if state is None:
                    signature.append((asset.asset_id, 0, False))
                else:
                    signature.append((asset.asset_id, state.frame_index, state.animation_active))
            return tuple(signature)
        return (self.frame_index, self.animation_active)

    def _has_active_animation(self) -> bool:
        if self.custom_mode_var.get():
            return any(state.animation_active for state in self.custom_states.values())
        return self.animation_active

    def _physics_activity_score(self, cursor_speed: float) -> float:
        score = cursor_speed
        if self.custom_mode_var.get():
            for state in self.custom_states.values():
                score = max(score, math.hypot(state.vx, state.vy), abs(state.angular_velocity) * 60.0)
            return score
        return max(score, math.hypot(self.rope_vel_x, self.rope_vel_y), abs(self.pig_angular_velocity) * 60.0)

    def _smart_motion_active(self, cursor_speed: float) -> bool:
        return self._physics_activity_score(cursor_speed) > 8.0

    @staticmethod
    def _should_draw_overlay(
        profile: PerformanceProfile,
        motion_active: bool,
        animation_changed: bool,
        overlay_dirty: bool,
        last_draw_time: float,
    ) -> bool:
        if not profile.adaptive:
            return True
        return last_draw_time <= 0.0 or overlay_dirty or motion_active or animation_changed

    def _tick_fps(self, profile: PerformanceProfile, motion_active: bool, animation_active: bool) -> int:
        if not profile.adaptive:
            return profile.target_fps
        if motion_active:
            if self.average_draw_ms >= 20.0:
                return min(profile.target_fps, 30)
            if self.average_draw_ms >= 14.0:
                return min(profile.target_fps, 45)
            return profile.target_fps
        if animation_active:
            return profile.animation_fps
        return profile.idle_fps

    @staticmethod
    def _preview_fps(profile: PerformanceProfile) -> int:
        return 12 if profile.adaptive else 20

    def _record_frame_cost(self, name: str, start_time: float) -> None:
        elapsed_ms = max(0.0, (time.perf_counter() - start_time) * 1000.0)
        if name == "draw":
            self.last_draw_ms = elapsed_ms
            self.average_draw_ms = elapsed_ms if self.average_draw_ms <= 0 else self.average_draw_ms * 0.85 + elapsed_ms * 0.15
        elif name == "physics":
            self.last_physics_ms = elapsed_ms
            self.average_physics_ms = elapsed_ms if self.average_physics_ms <= 0 else self.average_physics_ms * 0.85 + elapsed_ms * 0.15
        elif name == "collision":
            self.last_collision_ms = elapsed_ms
            self.average_collision_ms = elapsed_ms if self.average_collision_ms <= 0 else self.average_collision_ms * 0.85 + elapsed_ms * 0.15

    def _tick(self) -> None:
        now = time.perf_counter()
        profile = self._current_performance_profile()
        max_dt = 1 / max(30, profile.target_fps)
        dt = min(max_dt * 1.8, max(0.001, now - self.last_tick))
        self.last_tick = now

        if self.tray_icon is not None:
            self.tray_icon.process_pending_actions()
        animation_changed = self._advance_animation(dt)
        if not self.running and now - self.last_prewarm_time >= 0.025 and profile.texture_cache_limit > 180:
            self._prewarm_one_asset()
            self.last_prewarm_time = now
        if now - self.preview_last_time >= 1 / self._preview_fps(profile):
            self._draw_preview(now)
            self.preview_last_time = now
        motion_active = False
        animation_active = self._has_active_animation()
        if self.running:
            physics_start = time.perf_counter()
            cursor_speed = self._update_physics(dt)
            self._record_frame_cost("physics", physics_start)
            motion_active = self._smart_motion_active(cursor_speed) if profile.adaptive else True
            if self._should_draw_overlay(profile, motion_active, animation_changed, self.overlay_dirty, self.last_overlay_draw_time):
                draw_start = time.perf_counter()
                self._draw_overlay()
                self._record_frame_cost("draw", draw_start)
                self.last_overlay_draw_time = now
                self.overlay_dirty = False
        self._maybe_prewarm_custom_assets(now, profile, motion_active)

        tick_fps = self._tick_fps(profile, motion_active, animation_active)
        target_frame_time = 1000.0 / max(1, tick_fps)
        elapsed_ms = (time.perf_counter() - now) * 1000.0
        delay = max(1, int(target_frame_time - elapsed_ms)) if self.running else 12
        self.root.after(delay, self._tick)

    def _advance_animation(self, dt: float) -> bool:
        """Advance animation timers, return True if animation state changed."""
        if self.custom_mode_var.get():
            return self._advance_custom_animations(dt)
        old_frame = self.frame_index
        old_active = self.animation_active
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
            return old_active != self.animation_active or old_frame != self.frame_index

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
        return old_active != self.animation_active or old_frame != self.frame_index

    def _advance_custom_animations(self, dt: float) -> bool:
        """Advance custom asset animations, return True if any state changed."""
        changed = False
        for asset in self._active_custom_assets():
            state = self.custom_states.setdefault(asset.asset_id, CustomItemState())
            old_frame = state.frame_index
            old_active = state.animation_active
            if not self._custom_asset_is_animated(asset):
                state.animation_active = False
                state.frame_index = 0
                state.frame_time_ms = 0.0
                state.trigger_timer = 0.0
            else:
                frame_count = self._custom_asset_frame_count(asset)
                if frame_count <= 1 or (asset.probability <= 0 and not asset.always_animate):
                    state.animation_active = False
                    state.frame_index = 0
                    state.frame_time_ms = 0.0
                    state.trigger_timer = 0.0
                elif asset.always_animate:
                    state.animation_active = True
                    state.trigger_timer = 0.0
                elif not state.animation_active:
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
                else:
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
            if old_frame != state.frame_index or old_active != state.animation_active:
                changed = True
        return changed

    def _update_physics(self, dt: float) -> float:
        if not self.initialized_physics:
            self._place_physics_at_cursor()

        anchor_x, anchor_y = self._cursor_anchor()
        last_x, last_y = self.last_anchor
        cursor_vx = (anchor_x - last_x) / dt
        cursor_vy = (anchor_y - last_y) / dt
        cursor_speed = math.hypot(cursor_vx, cursor_vy)
        self.last_anchor = (anchor_x, anchor_y)
        self.last_cursor_velocity = (cursor_vx, cursor_vy)
        if self.custom_mode_var.get():
            self._update_custom_physics(dt, anchor_x, anchor_y, cursor_vx, cursor_vy)
            return cursor_speed

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
        return cursor_speed

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

        should_collide, collision_dt = self._custom_collision_step(active_assets, dt)
        if should_collide:
            self._resolve_custom_collisions(active_assets, collision_dt)

    def _custom_collision_step(self, active_assets: list[CustomAssetConfig], dt: float) -> tuple[bool, float]:
        if not self.custom_collision_var.get() or len(active_assets) < 2:
            self.collision_accumulator = 0.0
            return False, dt
        active_count = len(active_assets)
        profile = self._current_performance_profile()
        if active_count >= 16:
            interval = 1 / 20
        elif active_count >= 9 or profile.adaptive:
            interval = 1 / 30
        else:
            return True, dt
        self.collision_accumulator += dt
        if self.collision_accumulator < interval:
            return False, dt
        collision_dt = min(self.collision_accumulator, interval * 2.0)
        self.collision_accumulator = 0.0
        return True, collision_dt

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
        collision_start = time.perf_counter()
        indexed_items: list[tuple[int, CustomAssetConfig, CustomItemState]] = []
        for index, asset in enumerate(active_assets):
            state = self.custom_states.get(asset.asset_id)
            if state is not None:
                indexed_items.append((index, asset, state))
        for _first_index, first, first_state, _second_index, second, second_state in self._custom_collision_pairs(indexed_items):
            self._resolve_custom_collision_pair(first, first_state, second, second_state, dt)
        self._record_frame_cost("collision", collision_start)

    @staticmethod
    def _custom_collision_pairs(
        indexed_items: list[tuple[int, CustomAssetConfig, CustomItemState]]
    ) -> list[tuple[int, CustomAssetConfig, CustomItemState, int, CustomAssetConfig, CustomItemState]]:
        if len(indexed_items) < 9:
            return [
                (*first, *second)
                for first_offset, first in enumerate(indexed_items)
                for second in indexed_items[first_offset + 1 :]
            ]

        max_radius = max((asset.collision_radius for _index, asset, _state in indexed_items), default=24.0)
        cell_size = max(32.0, max_radius * 2.0)
        buckets: dict[tuple[int, int], list[tuple[int, CustomAssetConfig, CustomItemState]]] = {}
        for item in indexed_items:
            _index, _asset, state = item
            cell = (math.floor(state.x / cell_size), math.floor(state.y / cell_size))
            buckets.setdefault(cell, []).append(item)

        pairs: list[tuple[int, CustomAssetConfig, CustomItemState, int, CustomAssetConfig, CustomItemState]] = []
        seen: set[tuple[int, int]] = set()
        for (cell_x, cell_y), bucket_items in buckets.items():
            nearby: list[tuple[int, CustomAssetConfig, CustomItemState]] = []
            for offset_x in (-1, 0, 1):
                for offset_y in (-1, 0, 1):
                    nearby.extend(buckets.get((cell_x + offset_x, cell_y + offset_y), ()))
            for first in bucket_items:
                first_index = first[0]
                for second in nearby:
                    second_index = second[0]
                    if second_index <= first_index:
                        continue
                    pair_key = (first_index, second_index)
                    if pair_key in seen:
                        continue
                    seen.add(pair_key)
                    pairs.append((*first, *second))
        max_pairs = max(36, len(indexed_items) * 5)
        if len(pairs) > max_pairs:
            return PigPointerApp._nearest_custom_collision_pairs(pairs, max_neighbors=5)
        return pairs

    @staticmethod
    def _nearest_custom_collision_pairs(
        pairs: list[tuple[int, CustomAssetConfig, CustomItemState, int, CustomAssetConfig, CustomItemState]],
        max_neighbors: int,
    ) -> list[tuple[int, CustomAssetConfig, CustomItemState, int, CustomAssetConfig, CustomItemState]]:
        scored_pairs: list[tuple[float, tuple[int, CustomAssetConfig, CustomItemState, int, CustomAssetConfig, CustomItemState]]] = []
        for pair in pairs:
            _first_index, _first, first_state, _second_index, _second, second_state = pair
            dx = second_state.x - first_state.x
            dy = second_state.y - first_state.y
            scored_pairs.append((dx * dx + dy * dy, pair))
        scored_pairs.sort(key=lambda item: item[0])

        neighbor_counts: dict[int, int] = {}
        selected: list[tuple[int, CustomAssetConfig, CustomItemState, int, CustomAssetConfig, CustomItemState]] = []
        for _distance, pair in scored_pairs:
            first_index = pair[0]
            second_index = pair[3]
            if neighbor_counts.get(first_index, 0) >= max_neighbors or neighbor_counts.get(second_index, 0) >= max_neighbors:
                continue
            selected.append(pair)
            neighbor_counts[first_index] = neighbor_counts.get(first_index, 0) + 1
            neighbor_counts[second_index] = neighbor_counts.get(second_index, 0) + 1
        return selected

    @staticmethod
    def _resolve_custom_collision_pair(
        first: CustomAssetConfig,
        first_state: CustomItemState,
        second: CustomAssetConfig,
        second_state: CustomItemState,
        dt: float,
    ) -> None:
        dx = second_state.x - first_state.x
        dy = second_state.y - first_state.y
        distance = math.hypot(dx, dy)
        minimum = max(2.0, first.collision_radius + second.collision_radius)
        if distance >= minimum:
            return
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

    def _transparent_composite_canvas(self, width: int, height: int) -> Image.Image:
        width = max(1, int(width))
        height = max(1, int(height))
        if self.composite_canvas is None or self.composite_canvas.size != (width, height):
            self.composite_canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        else:
            self.composite_canvas.paste((0, 0, 0, 0), (0, 0, width, height))
        return self.composite_canvas

    def _premultiplied_bgra(self, image: Image.Image) -> bytes:
        """Convert RGBA PIL Image to premultiplied BGRA bytes, reusing a buffer."""
        rgba = image.convert("RGBA")
        h, w = rgba.height, rgba.width
        if np is None:
            return GifRenderer.to_premultiplied_bgra(image)
        if self._bgra_buffer is None or (w, h) != self._bgra_buffer_shape:
            self._bgra_buffer = np.zeros((h, w, 4), dtype=np.uint8)
            self._bgra_buffer_shape = (w, h)
        data = np.asarray(rgba, dtype=np.uint16)
        ch_a = data[:, :, 3]
        buf = self._bgra_buffer
        buf[:, :, 0] = (data[:, :, 2] * ch_a // 255).astype(np.uint8)  # B
        buf[:, :, 1] = (data[:, :, 1] * ch_a // 255).astype(np.uint8)  # G
        buf[:, :, 2] = (data[:, :, 0] * ch_a // 255).astype(np.uint8)  # R
        buf[:, :, 3] = ch_a.astype(np.uint8)                           # A
        return buf.tobytes()

    # ---------------------------------------------------------------------------
    # Drawing helpers
    # ---------------------------------------------------------------------------

    @staticmethod
    def _rope_bezier_points(
        ax: float, ay: float, bx: float, by: float,
        sag: float, vx: float, vx_factor: float,
        rope_length: float, left: float, top: float,
    ) -> list[tuple[float, float]]:
        """Return quadratic Bezier control points for a rope from (ax,ay) to (bx,by)."""
        cx = (ax + bx) / 2 - left + vx * vx_factor
        cy = (ay + by) / 2 - top + sag
        segments = max(4, min(18, int(rope_length / 8)))
        pts = [(0.0, 0.0)] * segments
        for step in range(segments):
            t = step / max(1, segments - 1)
            inv = 1.0 - t
            pts[step] = (
                inv * inv * (ax - left) + 2 * inv * t * cx + t * t * (bx - left),
                inv * inv * (ay - top) + 2 * inv * t * cy + t * t * (by - top),
            )
        return pts

    def _draw_single_rope(
        self, draw: ImageDraw.ImageDraw,
        ax: float, ay: float, bx: float, by: float,
        sag: float, vx: float, vx_factor: float,
        rope_length: float, rope_width: int,
        color: tuple[int, int, int, int],
        left: float, top: float,
    ) -> None:
        """Draw one rope on the given canvas draw surface."""
        pts = self._rope_bezier_points(ax, ay, bx, by, sag, vx, vx_factor, rope_length, left, top)
        draw.line(pts, fill=color, width=max(1, rope_width), joint="curve")

    @staticmethod
    def _union_bounds(
        items: list[tuple[float, float, float, float]],
        margin: float,
    ) -> tuple[int, int, int, int]:
        """Compute (left, top, right, bottom) inclusive bounds from (x1,y1,x2,y2) rects."""
        xs = []
        ys = []
        for x1, y1, x2, y2 in items:
            xs.extend([x1, x2])
            ys.extend([y1, y2])
        return (
            math.floor(min(xs) - margin),
            math.floor(min(ys) - margin),
            math.ceil(max(xs) + margin),
            math.ceil(max(ys) + margin),
        )

    # ---------------------------------------------------------------------------
    # Overlay drawing
    # ---------------------------------------------------------------------------

    def _draw_overlay(self) -> None:
        if self.overlay is None:
            return
        if self.custom_mode_var.get():
            self._draw_custom_overlay()
            return

        # Build a signature of inputs; skip the rest if nothing changed
        anchor_x, anchor_y = self._cursor_anchor()
        angle = math.degrees(self.pig_angle)
        abs_binding = self.absolute_binding_var.get()
        sig = (
            self.frame_index,
            int(round(angle / 2.0)),
            round(self.rope_end_x, 1),
            round(self.rope_end_y, 1),
            round(anchor_x, 1),
            round(anchor_y, 1),
            int(self.size_var.get()),
            int(self.rope_width_var.get()),
            abs_binding,
        )
        if sig == self._last_draw_sig and not self.overlay_dirty:
            return
        self._last_draw_sig = sig

        display_height = int(self.size_var.get())
        image, joint, _bgra = self.renderer.render_asset(self.frame_index, display_height, angle)
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
        rects: list[tuple[float, float, float, float]] = [
            (anchor_x, anchor_y, anchor_x, anchor_y),
            (self.rope_end_x, self.rope_end_y, self.rope_end_x, self.rope_end_y),
            (image_x, image_y, image_x + image.width, image_y + image.height),
        ]
        if absolute_binding and cursor_asset is not None:
            cim, chot = cursor_asset
            cl, ct = pointer_x - chot[0], pointer_y - chot[1]
            rects.append((cl, ct, cl + cim.width, ct + cim.height))
        elif absolute_binding:
            cursor_points = self._cursor_polygon(pointer_x, pointer_y)
            cursor_outline = self._cursor_outline(cursor_points)
            all_pts = cursor_points + cursor_outline
            rects.append((min(p[0] for p in all_pts), min(p[1] for p in all_pts),
                          max(p[0] for p in all_pts), max(p[1] for p in all_pts)))
        left, top, right, bottom = self._union_bounds(rects, margin)
        canvas_w = max(16, right - left)
        canvas_h = max(16, bottom - top)

        composite = self._transparent_composite_canvas(canvas_w, canvas_h)
        draw = ImageDraw.Draw(composite)
        weight = self._weight_factor()
        rope_length = self._rope_length()
        sag = min(48.0, rope_length * (0.16 + 0.15 * weight) + abs(self.rope_vel_x) * (0.004 + 0.005 * weight))
        self._draw_single_rope(
            draw,
            anchor_x, anchor_y, self.rope_end_x, self.rope_end_y,
            sag, self.rope_vel_x, 0.018,
            rope_length, int(round(self.rope_width_var.get())),
            (116, 77, 45, 245),
            left, top,
        )
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
        bgra = self._premultiplied_bgra(composite)
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

        # Build signature from physics states before expensive rendering
        profile = self._current_performance_profile()
        abs_binding = self.absolute_binding_var.get()
        items_sig = []
        for asset in active_assets:
            state = self.custom_states.get(asset.asset_id)
            if state is None:
                continue
            items_sig.append((
                asset.asset_id,
                round(state.x, 1),
                round(state.y, 1),
                int(round(math.degrees(state.angle) / max(1, profile.angle_step))),
                state.frame_index if state.animation_active else 0,
                int(asset.size),
            ))
        sig = (tuple(items_sig), abs_binding)
        if sig == self._last_draw_sig and not self.overlay_dirty:
            return
        self._last_draw_sig = sig

        rendered_items: list[CustomRenderedItem] = []
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
        rects: list[tuple[float, float, float, float]] = []
        for item in rendered_items:
            s = item.state
            rects.append((s.anchor_x, s.anchor_y, s.anchor_x, s.anchor_y))
            rects.append((s.x, s.y, s.x + item.image.width, s.y + item.image.height))
        if absolute_binding and cursor_asset is not None:
            cim, chot = cursor_asset
            cl = pointer_x - chot[0]
            ct = pointer_y - chot[1]
            rects.append((cl, ct, cl + cim.width, ct + cim.height))
        elif absolute_binding:
            cursor_points = self._cursor_polygon(pointer_x, pointer_y)
            cursor_outline = self._cursor_outline(cursor_points)
            all_pts = cursor_points + cursor_outline
            rects.append((min(p[0] for p in all_pts), min(p[1] for p in all_pts),
                          max(p[0] for p in all_pts), max(p[1] for p in all_pts)))

        left, top, right, bottom = self._union_bounds(rects, margin)
        canvas_w = max(16, right - left)
        canvas_h = max(16, bottom - top)
        composite = self._transparent_composite_canvas(canvas_w, canvas_h)
        draw = ImageDraw.Draw(composite)

        for item in rendered_items:
            state = item.state
            config = item.config
            weight = max(0.0, min(1.0, config.weight / 100.0))
            sag = min(54.0, config.rope_length * (0.12 + 0.18 * weight) + abs(state.vx) * (0.003 + 0.004 * weight))
            self._draw_single_rope(
                draw,
                state.anchor_x, state.anchor_y, state.x, state.y,
                sag, state.vx, 0.014,
                config.rope_length, max(1, int(round(config.rope_width))),
                self._custom_rope_rgba(config),
                left, top,
            )

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

        bgra = self._premultiplied_bgra(composite)
        self.overlay.update_pixels(bgra, composite.width, composite.height, left, top)

    def _custom_asset_frame_count(self, asset: CustomAssetConfig) -> int:
        if asset.asset_id == DEFAULT_PIG_CUSTOM_ID:
            return self.renderer.frame_count
        if not self._custom_asset_is_animated(asset):
            return 1
        renderer = self._custom_renderer(asset)
        return renderer.frame_count(asset.reverse_loop) if renderer is not None else 1

    def _custom_asset_duration(self, asset: CustomAssetConfig, frame_index: int) -> int:
        if asset.asset_id == DEFAULT_PIG_CUSTOM_ID:
            return self.renderer.durations[frame_index % self.renderer.frame_count]
        if not self._custom_asset_is_animated(asset):
            return 40
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
            composite = self._transparent_composite_canvas(cursor_image.width + margin * 2, cursor_image.height + margin * 2)
            composite.alpha_composite(cursor_image, (margin, margin))
        else:
            cursor_points = self._cursor_polygon(pointer_x, pointer_y)
            cursor_outline = self._cursor_outline(cursor_points)
            xs = [point[0] for point in cursor_points + cursor_outline]
            ys = [point[1] for point in cursor_points + cursor_outline]
            left = int(math.floor(min(xs) - margin))
            top = int(math.floor(min(ys) - margin))
            composite = self._transparent_composite_canvas(
                int(math.ceil(max(xs) - min(xs) + margin * 2)),
                int(math.ceil(max(ys) - min(ys) + margin * 2)),
            )
            draw = ImageDraw.Draw(composite)
            self._draw_cursor_on_pil(draw, cursor_points, cursor_outline, left, top)
        bgra = self._premultiplied_bgra(composite)
        self.overlay.update_pixels(bgra, composite.width, composite.height, left, top)

    def _custom_renderer_cache_limit(self, asset: CustomAssetConfig) -> int:
        profile_limit = self._current_performance_profile().texture_cache_limit
        base = max(32, profile_limit // max(2, len(self.custom_assets) or 2))
        if not self._custom_asset_is_animated(asset):
            return base
        state = self.custom_states.get(asset.asset_id)
        is_priority = (
            asset.always_animate
            or asset.asset_id == self.custom_selected_id.get()
            or (state is not None and state.animation_active)
        )
        if is_priority:
            return min(profile_limit, max(base * 2, base + 72))
        return min(profile_limit, max(base + 32, int(base * 1.4)))

    def _custom_renderer(self, asset: CustomAssetConfig) -> CustomAssetRenderer | None:
        renderer = self.custom_renderers.get(asset.asset_id)
        if renderer is not None:
            renderer.cache_limit = self._custom_renderer_cache_limit(asset)
            return renderer
        path = Path(asset.path)
        if not path.exists():
            return None
        try:
            renderer = CustomAssetRenderer(path, self.root)
        except Exception:
            return None
        self._refresh_custom_asset_stats(asset, renderer)
        renderer.cache_limit = self._custom_renderer_cache_limit(asset)
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
