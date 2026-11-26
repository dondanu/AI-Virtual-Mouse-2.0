"""Calibration state machine for defining the active hand-movement area.

Calibration walks the user through two poses: move the pinch tip to the
TOP-LEFT of the desired area and confirm, then to the BOTTOM-RIGHT and
confirm. The two points define a rectangle in normalized camera space.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional, Tuple

from config import CalibrationArea


class CalibrationStep(Enum):
    IDLE = "idle"
    WAIT_TOP_LEFT = "wait_top_left"
    WAIT_BOTTOM_RIGHT = "wait_bottom_right"
    DONE = "done"


class CalibrationSession:
    """Interactive two-point calibration driven by pinch gestures."""

    def __init__(self, timeout_s: float = 8.0) -> None:
        self.timeout_s = timeout_s
        self.step = CalibrationStep.IDLE
        self.top_left: Optional[Tuple[float, float]] = None
        self.bottom_right: Optional[Tuple[float, float]] = None
        self._pinch_was_down = False
        self._timer = 0.0

    def start(self) -> None:
        """Begin a new calibration session."""
        self.step = CalibrationStep.WAIT_TOP_LEFT
        self.top_left = None
        self.bottom_right = None
        self._pinch_was_down = False
        self._timer = 0.0

    def cancel(self) -> None:
        self.step = CalibrationStep.IDLE
        self.top_left = None
        self.bottom_right = None

    @property
    def active(self) -> bool:
        return self.step in (CalibrationStep.WAIT_TOP_LEFT,
                             CalibrationStep.WAIT_BOTTOM_RIGHT)

    def tick(self, dt: float) -> None:
        """Advance the timeout timer; call once per frame with delta seconds."""
        if self.active:
            self._timer += dt
            if self._timer >= self.timeout_s:
                self.cancel()

    def remaining(self) -> float:
        return max(0.0, self.timeout_s - self._timer)

    def update(
        self, pinch_down: bool, fingertip: Optional[Tuple[float, float]]
    ) -> Optional[CalibrationArea]:
        """Feed one frame of pinch state + normalized fingertip position.

        A fresh pinch (rising edge) captures the current point. Returns the
        finished :class:`CalibrationArea` once both corners are captured,
        otherwise ``None``.
        """
        if not self.active:
            return None
        result: Optional[CalibrationArea] = None
        edge_detected = False
        if pinch_down and not self._pinch_was_down and fingertip is not None:
            edge_detected = True
            if self.step is CalibrationStep.WAIT_TOP_LEFT:
                self.top_left = fingertip
                self.step = CalibrationStep.WAIT_BOTTOM_RIGHT
                self._timer = 0.0
                # Don't update _pinch_was_down to allow immediate second pinch
            elif self.step is CalibrationStep.WAIT_BOTTOM_RIGHT:
                self.bottom_right = fingertip
                tl, br = self.top_left, self.bottom_right
                assert tl is not None and br is not None
                area = CalibrationArea(
                    x_min=min(tl[0], br[0]),
                    y_min=min(tl[1], br[1]),
                    x_max=max(tl[0], br[0]),
                    y_max=max(tl[1], br[1]),
                )
                # Guard against a degenerate one-dimensional area
                if area.x_max - area.x_min < 0.05 or area.y_max - area.y_min < 0.05:
                    self.step = CalibrationStep.WAIT_TOP_LEFT
                    self.top_left = None
                    self.bottom_right = None
                    self._timer = 0.0
                else:
                    self.step = CalibrationStep.DONE
                    result = area
        # Only update pinch state if we didn't just capture a point (to allow consecutive pinches)
        if not edge_detected:
            self._pinch_was_down = pinch_down
        return result
