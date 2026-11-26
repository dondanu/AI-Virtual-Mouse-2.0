"""Cursor control: maps gestures to mouse movement through calibration."""

from __future__ import annotations

import math
from typing import Optional, Tuple

from config import Settings, map_camera_to_screen
from src.mouse_output import mouse_output
from src.smoothing import EMASmoother

# If the raw fingertip jumps more than this fraction of the screen in one
# frame, it is almost certainly a tracking glitch — discard it.
_MAX_JUMP_RATIO = 0.25   # 25% of screen width/height per frame

# Minimum pixel distance the cursor must move before we actually update the OS.
# This prevents the ±1px integer rounding oscillation that causes blinking.
_MIN_MOVE_PX = 2


class CursorController:
    """Converts the index fingertip position into smoothed cursor movement."""

    def __init__(self, settings: Settings, screen_w: int, screen_h: int) -> None:
        self._settings = settings
        self._screen_w = screen_w
        self._screen_h = screen_h
        self._smoother = EMASmoother(settings.smoothing_alpha)
        self._last_moved: Optional[Tuple[int, int]] = None
        self._last_norm: Optional[Tuple[float, float]] = None   # for jump detection

    def reset(self) -> None:
        """Forget smoothing state, e.g. when tracking resumes after a gap."""
        self._smoother.reset()
        self._last_moved = None
        self._last_norm = None

    def update(self, fingertip_norm: Tuple[float, float]) -> Optional[Tuple[int, int]]:
        """Feed a normalized fingertip position; returns the cursor position.

        Returns None when the movement was suppressed by the dead zone or
        rejected as a tracking glitch (outlier jump).
        """
        nx, ny = fingertip_norm

        # Outlier rejection: skip frames where the finger teleports
        if self._last_norm is not None:
            dx = abs(nx - self._last_norm[0])
            dy = abs(ny - self._last_norm[1])
            if dx > _MAX_JUMP_RATIO or dy > _MAX_JUMP_RATIO:
                # Glitch frame — keep the last cursor position, update nothing
                return self._last_moved
        self._last_norm = (nx, ny)

        s = self._settings
        raw_x, raw_y = map_camera_to_screen(
            nx, ny, s.calibration,
            self._screen_w, self._screen_h, s.sensitivity,
        )
        sx, sy = self._smoother.update_with_dead_zone(
            float(raw_x), float(raw_y), s.dead_zone_px)
        target = (int(sx), int(sy))
        if target != self._last_moved:
            # Only actually move the OS cursor when we travel >= _MIN_MOVE_PX.
            # This eliminates the ±1px integer-rounding oscillation ("blinking").
            if self._last_moved is not None:
                lx, ly = self._last_moved
                if math.hypot(target[0] - lx, target[1] - ly) < _MIN_MOVE_PX:
                    return self._last_moved
            mouse_output.move(*target)
            self._last_moved = target
        return target
