"""Application-wide configuration and persisted settings for AI Virtual Mouse 2.0.

Settings are stored as JSON in a platform-appropriate user directory so the
application survives restarts. All values have sane defaults so the app runs
with no configuration file present.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


APP_NAME = "AI Virtual Mouse 2.0"
APP_VERSION = "2.0.0"

# Emergency stop: pressing this combination anywhere in the app instantly
# disables mouse control and releases all held mouse buttons.
EMERGENCY_STOP_KEY = "F10"


def default_settings_dir() -> Path:
    """Return the directory where settings/statistics are persisted."""
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "ai-virtual-mouse"


@dataclass
class CalibrationArea:
    """The active hand-movement area expressed in normalized camera space (0..1)."""

    x_min: float = 0.15
    y_min: float = 0.20
    x_max: float = 0.85
    y_max: float = 0.80

    def contains(self, nx: float, ny: float) -> bool:
        """Return True if a normalized camera point lies inside the area."""
        return self.x_min <= nx <= self.x_max and self.y_min <= ny <= self.y_max

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CalibrationArea":
        try:
            return cls(
                x_min=float(data["x_min"]),
                y_min=float(data["y_min"]),
                x_max=float(data["x_max"]),
                y_max=float(data["y_max"]),
            )
        except (KeyError, TypeError, ValueError):
            return cls()


@dataclass
class Settings:
    """All user-adjustable settings."""

    # Camera - Optimized for gaming (lower resolution = higher FPS)
    camera_index: int = 0
    camera_width: int = 640       # Reduced from 1280 for faster processing
    camera_height: int = 480      # Reduced from 720 for faster processing

    # Cursor control - Gaming optimized settings
    sensitivity: float = 2.8          # Increased from 1.6 for faster aiming
    smoothing_alpha: float = 0.35     # Balanced: responsive but not jittery
    dead_zone_px: float = 3.0         # Ignore micro-tremors below 3px

    # Gesture thresholds (ratios of hand size, robust to camera distance)
    pinch_on_threshold: float = 0.28  # pinch distance < this -> pinching
    pinch_off_threshold: float = 0.40 # release distance > this -> pinch ended (hysteresis)
    scroll_jump_px: int = 60          # pixels of cursor travel per scroll step
    scroll_speed_px: int = 14         # pixels of wheel input per frame per step
    click_cooldown_s: float = 0.25    # Reduced from 0.45 for faster repeated shots

    # Gesture toggles
    enable_move: bool = True
    enable_left_click: bool = True
    enable_right_click: bool = True
    enable_scroll: bool = True

    calibration: CalibrationArea = field(default_factory=CalibrationArea)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Settings":
        s = cls()
        if not isinstance(data, dict):
            return s
        int_keys = {"camera_index", "camera_width", "camera_height",
                    "scroll_jump_px", "scroll_speed_px"}
        for key, value in data.items():
            if key == "calibration":
                s.calibration = CalibrationArea.from_dict(value)
            elif hasattr(s, key) and key != "calibration":
                try:
                    if key in int_keys:
                        setattr(s, key, int(value))
                    else:
                        setattr(s, key, float(value)) if key in {
                            "sensitivity", "smoothing_alpha", "dead_zone_px",
                            "pinch_on_threshold", "pinch_off_threshold",
                            "click_cooldown_s"} else None
                except (TypeError, ValueError):
                    continue
        # Boolean keys need exact bool handling
        for key in ("enable_move", "enable_left_click", "enable_right_click",
                    "enable_scroll"):
            if key in data:
                setattr(s, key, bool(data[key]))
        # Clamp numerical settings into valid ranges
        s.sensitivity = min(4.0, max(0.5, s.sensitivity))
        s.smoothing_alpha = min(0.95, max(0.05, s.smoothing_alpha))
        s.pinch_on_threshold = min(0.9, max(0.05, s.pinch_on_threshold))
        s.pinch_off_threshold = max(s.pinch_on_threshold + 0.02, s.pinch_off_threshold)
        return s


class SettingsStore:
    """Loads and saves :class:`Settings` as JSON on disk."""

    def __init__(self, directory: Optional[Path] = None) -> None:
        self._dir = Path(directory) if directory else default_settings_dir()
        self._settings_path = self._dir / "settings.json"
        self._stats_path = self._dir / "statistics.json"

    @property
    def settings_path(self) -> Path:
        return self._settings_path

    @property
    def stats_path(self) -> Path:
        return self._stats_path

    def load_settings(self) -> Settings:
        try:
            raw = json.loads(self._settings_path.read_text(encoding="utf-8"))
            return Settings.from_dict(raw)
        except (OSError, json.JSONDecodeError):
            return Settings()

    def save_settings(self, settings: Settings) -> None:
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            self._settings_path.write_text(
                json.dumps(settings.to_dict(), indent=2), encoding="utf-8"
            )
        except OSError:
            # Non-fatal: the app still works this session without persistence.
            pass


def clamp(value: float, low: float, high: float) -> float:
    """Clamp *value* into the closed interval [low, high]."""
    return max(low, min(high, value))


def map_camera_to_screen(
    nx: float,
    ny: float,
    area: CalibrationArea,
    screen_w: int,
    screen_h: int,
    sensitivity: float = 1.0,
) -> Tuple[int, int]:
    """Map a normalized camera point through the calibration area to screen px.

    ``nx``/``ny`` are in 0..1 camera space. Positions outside the calibration
    area are clamped to the screen edges, which keeps the cursor inside the
    display at all times.
    """
    span_x = max(area.x_max - area.x_min, 1e-6)
    span_y = max(area.y_max - area.y_min, 1e-6)
    rel_x = clamp((nx - area.x_min) / span_x, 0.0, 1.0)
    rel_y = clamp((ny - area.y_min) / span_y, 0.0, 1.0)
    center_x = screen_w / 2.0
    center_y = screen_h / 2.0
    sx = clamp(center_x + (rel_x - 0.5) * screen_w * sensitivity, 0, screen_w - 1)
    sy = clamp(center_y + (rel_y - 0.5) * screen_h * sensitivity, 0, screen_h - 1)
    return round(sx), round(sy)
