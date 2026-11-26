"""Cursor control: maps gestures to mouse movement through calibration."""

from __future__ import annotations

from typing import Optional, Tuple

from config import Settings, map_camera_to_screen
from src.mouse_output import mouse_output
from src.smoothing import EMASmoother


class CursorController:
    """Converts the index fingertip position into smoothed cursor movement."""

    def __init__(self, settings: Settings, screen_w: int, screen_h: int) -> None:
        self._settings = settings
        self._screen_w = screen_w
        self._screen_h = screen_h
        self._smoother = EMASmoother(settings.smoothing_alpha)
        self._last_moved: Optional[Tuple[int, int]] = None

    def reset(self) -> None:
        """Forget smoothing state, e.g. when tracking resumes after a gap."""
        self._smoother.reset()
        self._last_moved = None

    def update(self, fingertip_norm: Tuple[float, float]) -> Optional[Tuple[int, int]]:
        """Feed a normalized fingertip position; returns the cursor position.

        Returns None when the movement was suppressed by the dead zone.
        """
        s = self._settings
        raw_x, raw_y = map_camera_to_screen(
            fingertip_norm[0], fingertip_norm[1], s.calibration,
            self._screen_w, self._screen_h, s.sensitivity,
        )
        sx, sy = self._smoother.update_with_dead_zone(
            float(raw_x), float(raw_y), s.dead_zone_px)
        target = (int(sx), int(sy))
        if target != self._last_moved:
            mouse_output.move(*target)
            self._last_moved = target
        return target
