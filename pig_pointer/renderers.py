# -*- coding: utf-8 -*-
"""Image renderers for the default pig GIF and custom user assets."""

from __future__ import annotations

import math
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pig_pointer.constants import (
    CUSTOM_ATTACH_AUTO,
    CUSTOM_ATTACH_FIXED,
    CUSTOM_ATTACH_MODES,
    CUSTOM_CONNECTION_CHAIN,
    DEFAULT_PIG_CUSTOM_ID,
    PERFORMANCE_PROFILES,
    PerformanceProfile,
    ROPE_COLORS,
)
from pig_pointer.utils import _clamp, _clamp_int, _is_hex_color

if TYPE_CHECKING:
    import tkinter as tk

try:
    import numpy as np
except Exception:
    np = None

try:
    from PIL import Image, ImageDraw, ImageSequence, ImageTk
except Exception as exc:
    import tkinter.messagebox

    tkinter.messagebox.showerror("缺少依赖", f"需要安装 Pillow 才能播放 GIF：\n{exc}")
    raise

# ---------------------------------------------------------------------------
# Resampling filter (BILINEAR is fast enough for cartoon assets)
# ---------------------------------------------------------------------------


def _resample_filter() -> int:
    return getattr(Image, "Resampling", Image).BILINEAR


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


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
    source_width: int = 0
    source_height: int = 0
    trimmed_width: int = 0
    trimmed_height: int = 0
    frame_count: int = 1
    file_size: int = 0
    estimated_pixels: int = 0
    is_animated: bool = False

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
        frame_count = _clamp_int(data.get("frame_count"), 1, 20_000, 1)
        is_animated_value = data.get("is_animated")
        is_animated = is_animated_value if isinstance(is_animated_value, bool) else frame_count > 1 or str(path).lower().endswith(".gif")
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
            source_width=_clamp_int(data.get("source_width"), 0, 100_000),
            source_height=_clamp_int(data.get("source_height"), 0, 100_000),
            trimmed_width=_clamp_int(data.get("trimmed_width"), 0, 100_000),
            trimmed_height=_clamp_int(data.get("trimmed_height"), 0, 100_000),
            frame_count=frame_count,
            file_size=_clamp_int(data.get("file_size"), 0, 2_000_000_000),
            estimated_pixels=_clamp_int(data.get("estimated_pixels"), 0, 20_000_000_000),
            is_animated=is_animated,
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
            "source_width": self.source_width,
            "source_height": self.source_height,
            "trimmed_width": self.trimmed_width,
            "trimmed_height": self.trimmed_height,
            "frame_count": self.frame_count,
            "file_size": self.file_size,
            "estimated_pixels": self.estimated_pixels,
            "is_animated": self.is_animated,
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


# ---------------------------------------------------------------------------
# GifRenderer — default pig GIF
# ---------------------------------------------------------------------------


class GifRenderer:
    # Cache of reusable rotation temp canvases keyed by (canvas_w, canvas_h)
    _rotate_temp_canvases: dict[tuple[int, int], Image.Image] = {}

    def __init__(self, gif_path: Path, tk_master: tk.Misc) -> None:
        self.gif_path = gif_path
        self.tk_master = tk_master
        self.frames: list[Image.Image] = []
        self.durations: list[int] = []
        self.body_joints: list[tuple[float, float]] = []
        self.base_size = (1, 1)
        self._cache: OrderedDict[tuple[int, int, int], tuple[Image.Image, tuple[float, float], bytes]] = OrderedDict()
        self._photo_cache: OrderedDict[tuple[int, int, int], tuple[ImageTk.PhotoImage, tuple[float, float]]] = OrderedDict()
        self.cache_limit = PERFORMANCE_PROFILES["普通"].texture_cache_limit
        self._load_gif()

    @property
    def frame_count(self) -> int:
        return len(self.frames)

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
            self.frames.append(body_frames[index])
            self.body_joints.append(body_joints[index])
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
    def _is_rope_pixel(red: int, green: int, blue: int, alpha: int) -> bool:
        return (
            alpha > 24
            and 55 <= red <= 170
            and 25 <= green <= 125
            and 8 <= blue <= 105
            and red > green > blue
        )

    @staticmethod
    def _find_top_rope_joint(frame: Image.Image) -> tuple[float, float]:
        pixels = frame.load()
        w, h = frame.size
        for y in range(min(120, h)):
            row_alphas = [pixels[x, y][3] for x in range(w)]
            non_zero = [x for x, a in enumerate(row_alphas) if a > 0]
            if non_zero:
                return (float(sum(non_zero) / len(non_zero)), float(y))
        return (float(w / 2), 0.0)

    def _erase_upper_rope(self, frame: Image.Image) -> tuple[Image.Image, tuple[float, float]]:
        image = frame.copy()
        pixels = image.load()
        width, height = image.size
        centers: list[float] = []
        attach_y = 122
        for y in range(min(height, 150)):
            rope_xs = []
            for x in range(width):
                red, green, blue, alpha = pixels[x, y]
                if self._is_rope_pixel(red, green, blue, alpha):
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
                    r, g, b, a = pixels[x, y]
                    if a > 0:
                        pixels[x, y] = (r, g, b, 0)
            attach_joint = (float(center_x), float(attach_y))
        else:
            attach_joint = self._find_top_rope_joint(frame)

        for y in range(min(height, max(0, attach_y))):
            rope_xs = []
            for x in range(width):
                red, green, blue, alpha = pixels[x, y]
                if self._is_rope_pixel(red, green, blue, alpha):
                    rope_xs.append(x)
            if rope_xs and (len(rope_xs) <= 18 or y < 122):
                for x in range(max(0, min(rope_xs) - 3), min(width, max(rope_xs) + 4)):
                    r, g, b, a = pixels[x, y]
                    if a > 0:
                        pixels[x, y] = (r, g, b, 0)
        for y in range(min(height, 120)):
            for x in range(width):
                r, g, b, a = pixels[x, y]
                if a <= 18:
                    pixels[x, y] = (r, g, b, 0)
        return image, attach_joint

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

    @staticmethod
    def _rotate_about_joint(
        image: Image.Image, joint: tuple[float, float], angle: int
    ) -> tuple[Image.Image, tuple[float, float]]:
        # Fast path: no rotation needed
        if angle == 0:
            return image, joint

        w, h = image.size
        pad = int(max(w, h) * 1.8)
        canvas_w = max(pad, w + 80)
        canvas_h = max(pad, h + 120)
        pivot = (canvas_w // 2, int(canvas_h * 0.24))

        key = (canvas_w, canvas_h)
        temp = GifRenderer._rotate_temp_canvases.get(key)
        if temp is None:
            if len(GifRenderer._rotate_temp_canvases) >= 4:
                GifRenderer._rotate_temp_canvases.clear()
            temp = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
            GifRenderer._rotate_temp_canvases[key] = temp
        else:
            temp.paste((0, 0, 0, 0), (0, 0, canvas_w, canvas_h))
        paste_xy = (int(round(pivot[0] - joint[0])), int(round(pivot[1] - joint[1])))
        temp.alpha_composite(image, paste_xy)

        rotated = temp.rotate(
            angle,
            resample=getattr(Image, "Resampling", Image).BILINEAR,
            center=pivot,
            fillcolor=(0, 0, 0, 0),
        )
        bbox = rotated.getbbox()
        if bbox is None:
            return image, joint
        cropped = rotated.crop(bbox)
        new_joint = (pivot[0] - bbox[0], pivot[1] - bbox[1])
        return cropped, new_joint

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


# ---------------------------------------------------------------------------
# CustomAssetRenderer — user-uploaded images / GIFs
# ---------------------------------------------------------------------------


class CustomAssetRenderer:
    def __init__(self, asset_path: Path, tk_master: tk.Misc) -> None:
        self.asset_path = asset_path
        self.tk_master = tk_master
        self.frames: list[Image.Image] = []
        self.durations: list[int] = []
        self.joints: list[tuple[float, float]] = []
        self.base_size = (1, 1)
        self.source_size = (1, 1)
        self.source_frame_count = 1
        self.file_size = 0
        self.estimated_pixels = 1
        self._cache: OrderedDict[tuple[object, ...], tuple[Image.Image, tuple[float, float], bytes]] = OrderedDict()
        self._photo_cache: OrderedDict[tuple[object, ...], tuple[ImageTk.PhotoImage, tuple[float, float]]] = OrderedDict()
        self.cache_limit = 160
        self._load()

    def _load(self) -> None:
        source = Image.open(self.asset_path)
        self.source_size = source.size
        self.source_frame_count = max(1, int(getattr(source, "n_frames", 1) or 1))
        try:
            self.file_size = self.asset_path.stat().st_size
        except OSError:
            self.file_size = 0
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
        self.estimated_pixels = sum(w * h for w, h in [f.size for f in self.frames])

    @staticmethod
    def _find_attach_joint(frame: Image.Image) -> tuple[float, float]:
        pixels = frame.load()
        w, h = frame.size
        threshold = 24
        for y in range(h):
            non_zero = [x for x in range(w) if pixels[x, y][3] > threshold]
            if non_zero and len(non_zero) <= max(2, w // 8):
                return (float(sum(non_zero) / len(non_zero)), float(y))
            if non_zero and y >= max(8, h // 16):
                continue
        for y in range(h):
            non_zero = [x for x in range(w) if pixels[x, y][3] > threshold]
            if non_zero:
                return (float(sum(non_zero) / len(non_zero)), float(y))
        return (float(w / 2), 0.0)

    def _joint_for_frame(
        self, frame_index: int, attach_mode: str, attach_x: float, attach_y: float
    ) -> tuple[float, float]:
        if attach_mode == CUSTOM_ATTACH_FIXED:
            frame_w, frame_h = self.frames[frame_index % len(self.frames)].size
            return (frame_w * attach_x / 100.0, frame_h * attach_y / 100.0)
        return self.joints[frame_index % len(self.joints)]

    def clear_cache(self) -> None:
        self._cache.clear()
        self._photo_cache.clear()

    def frame_count(self, reverse_loop: bool = True) -> int:
        n = len(self.frames)
        if reverse_loop and n > 2:
            return n * 2 - 2
        return n

    def _resolve_frame_index(self, frame_index: int, reverse_loop: bool) -> int:
        n = len(self.frames)
        if n <= 1:
            return 0
        if not reverse_loop or n <= 2:
            return frame_index % n
        total = n * 2 - 2
        idx = frame_index % total
        if idx >= n:
            idx = total - idx
        return idx

    def duration(self, frame_index: int, reverse_loop: bool) -> int:
        resolved = self._resolve_frame_index(frame_index, reverse_loop)
        return self.durations[resolved % len(self.durations)]

    def render_asset(
        self,
        frame_index: int,
        display_height: int,
        angle: float,
        angle_step: int = 2,
        attach_mode: str = CUSTOM_ATTACH_AUTO,
        attach_x: float = 50.0,
        attach_y: float = 0.0,
        reverse_loop: bool = True,
    ) -> tuple[Image.Image, tuple[float, float], bytes] | None:
        if not self.frames:
            return None
        display_height = max(36, min(320, int(display_height)))
        angle_step = max(1, int(angle_step))
        angle_key = int(round(angle / angle_step) * angle_step)
        resolved_index = self._resolve_frame_index(frame_index, reverse_loop)
        attach_key = (attach_mode, round(attach_x, 1), round(attach_y, 1))
        key = (resolved_index, display_height, angle_key, attach_key)
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
        angle_step: int = 2,
        attach_mode: str = CUSTOM_ATTACH_AUTO,
        attach_x: float = 50.0,
        attach_y: float = 0.0,
        reverse_loop: bool = True,
    ) -> tuple[ImageTk.PhotoImage, tuple[float, float]] | None:
        if not self.frames:
            return None
        display_height = max(36, min(320, int(display_height)))
        angle_key = int(round(angle / 2.0) * 2)
        resolved_index = self._resolve_frame_index(frame_index, reverse_loop)
        attach_key = (attach_mode, round(attach_x, 1), round(attach_y, 1))
        key = (resolved_index, display_height, angle_key, attach_key)
        cached = self._photo_cache.get(key)
        if cached is not None:
            self._photo_cache.move_to_end(key)
            return cached

        result_asset = self.render_asset(frame_index, display_height, angle_key, angle_step, attach_mode, attach_x, attach_y, reverse_loop)
        if result_asset is None:
            return None
        image, joint, _bgra = result_asset
        photo = ImageTk.PhotoImage(image, master=self.tk_master)
        result = (photo, joint)
        self._photo_cache[key] = result
        while len(self._photo_cache) > 30:
            self._photo_cache.popitem(last=False)
        return result
