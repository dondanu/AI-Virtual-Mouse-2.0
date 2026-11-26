"""Scroll controller: converts two-finger vertical travel into wheel input."""

from __future__ import annotations

from typing import Optional

from src.mouse_output import mouse_output


class ScrollController:
    """Accumulates fingertip travel and emits scroll wheel events.

    A small threshold accumulates travel in normalized units so scrolling
    speed is independent of resolution; each ``scroll_jump_px`` of virtual
    travel produces one wheel tick.
    """

    def __init__(self, jump_px: float = 0.06, tick_px: float = 0.01) -> None:
        self._jump = max(0.005, jump_px)
        self._tick = max(0.001, tick_px)
        self._accumulator = 0.0
        self._last_pos: Optional[tuple[float, float]] = None

    def configure(self, jump_px: float, tick_px: float) -> None:
        self._jump = max(0.005, jump_px)
        self._tick = max(0.001, tick_px)

    def reset(self) -> None:
        self._accumulator = 0.0
        self._last_pos = None

    def update(self, fingertip_norm: tuple[float, float]) -> int:
        """Feed fingertip position; returns the number of wheel ticks emitted.

        Positive ticks scroll up, negative ticks scroll down.
        """
        if self._last_pos is not None:
            dy = self._last_pos[1] - fingertip_norm[1]
            self._accumulator += dy * (self._jump / self._tick)
        self._last_pos = fingertip_norm

        ticks = int(self._accumulator / self._tick)
        if ticks != 0:
            self._accumulator -= ticks * self._tick
            mouse_output.scroll(0, ticks)
        return ticks
