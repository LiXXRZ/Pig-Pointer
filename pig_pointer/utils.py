# -*- coding: utf-8 -*-
"""General-purpose utility functions (platform-independent)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from pig_pointer.constants import (
    CUSTOM_ASSETS_DIR_NAME,
    PERFORMANCE_MODE_ALIASES,
    PERFORMANCE_PROFILES,
    PerformanceProfile,
    SETTINGS_FILE_NAME,
    SETTINGS_VERSION,
)

# ---------------------------------------------------------------------------
# Value clamping / validation
# ---------------------------------------------------------------------------


def _clamp(value: object, minimum: float, maximum: float, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def _clamp_int(value: object, minimum: int, maximum: int, default: int = 0) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def _is_hex_color(value: str) -> bool:
    if len(value) != 7 or not value.startswith("#"):
        return False
    return all(char in "0123456789abcdefABCDEF" for char in value[1:])


# ---------------------------------------------------------------------------
# Performance mode helpers
# ---------------------------------------------------------------------------


def _normalize_performance_mode(mode: str) -> str:
    return PERFORMANCE_MODE_ALIASES.get(mode, mode)


def _performance_profile(mode: str) -> PerformanceProfile:
    normalized_mode = _normalize_performance_mode(mode)
    return PERFORMANCE_PROFILES.get(normalized_mode, PERFORMANCE_PROFILES["普通"])


# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------


def _resource_path(name: str) -> Path:
    base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base_dir / name


def _settings_path() -> Path:
    if sys.platform == "win32":
        base_dir = os.environ.get("APPDATA")
        if base_dir:
            return Path(base_dir) / "PigPointer" / SETTINGS_FILE_NAME
    return Path.home() / ".pig_pointer" / SETTINGS_FILE_NAME


def _default_assets_dir() -> Path:
    return _settings_path().parent / CUSTOM_ASSETS_DIR_NAME


# ---------------------------------------------------------------------------
# Startup command (used by win32 registry helpers)
# ---------------------------------------------------------------------------


def _startup_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable).resolve()}"'
    return f'"{Path(sys.executable).resolve()}" "{Path(sys.argv[0]).resolve()}"'


# ---------------------------------------------------------------------------
# Asset name sanitisation
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Settings file I/O
# ---------------------------------------------------------------------------


def _load_settings_file() -> dict[str, object]:
    path = _settings_path()
    if not path.exists():
        return {}
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {}
        return data
    except (json.JSONDecodeError, OSError):
        return {}
