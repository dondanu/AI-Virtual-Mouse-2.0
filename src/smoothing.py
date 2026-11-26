"""Exponential Moving Average smoothing for cursor coordinates."""

from __future__ import annotations

import math
from typing import Optional, Tuple


class EMASmoother:
    """Smooths a 2D coordinate stream with an Exponential Moving Average.

    ``alpha`` is the weight of the newest sample: 1.0 = no smoothing
    (instant follow), lower values produce heavier smoothing but more lag.

    Adaptive mode: when the hand moves fast, alpha increases so the cursor
    keeps up. When the hand is nearly still, alpha decreases to suppress jitter.
    This gives a mouse-like feel — fast when you move fast, stable when still.
    """

    def __init__(self, alpha: float = 0.35) -> None:
        self.alpha = min(1.0, max(0.01, alpha))
        self._state: Optional[Tuple[float, float]] = None
        self._prev_raw: Optional[Tuple[float, float]] = None

    def reset(self) -> None:
        """Forget all history so the next sample becomes the new baseline."""
        self._state = None
        self._prev_raw = None

    @property
    def has_value(self) -> bool:
        return self._state is not None

    def update(self, x: float, y: float) -> Tuple[float, float]:
        """Feed a raw sample and return the smoothed coordinate.

        Uses adaptive alpha: fast movement → higher alpha (more responsive),
        slow/still movement → lower alpha (less jitter).
        """
        if self._state is None:
            self._state = (x, y)
            self._prev_raw = (x, y)
            return self._state

        # Compute speed of raw input (pixels moved since last frame)
        px, py = self._prev_raw or (x, y)
        speed = math.hypot(x - px, y - py)
        self._prev_raw = (x, y)

        # Adaptive alpha: fast = more responsive, slow = more stable
        # speed < 3px  → use 60% of base alpha (very smooth, no jitter)
        # speed 3-20px → linearly ramp up
        # speed > 20px → use 1.4x base alpha capped at 0.95 (fast tracking)
        base = self.alpha
        if speed < 3:
            adaptive_alpha = base * 0.6
        elif speed > 20:
            adaptive_alpha = min(0.95, base * 1.4)
        else:
            t = (speed - 3) / 17.0  # 0..1
            adaptive_alpha = base * (0.6 + t * 0.8)

        a = adaptive_alpha
        self._state = (
            self._state[0] * (1 - a) + x * a,
            self._state[1] * (1 - a) + y * a,
        )
        return self._state

    def update_with_dead_zone(
        self, x: float, y: float, dead_zone_px: float
    ) -> Tuple[float, float]:
        """Like :meth:`update` but ignores micro-jitter below ``dead_zone_px``.

        The returned value is the smoothed position; when the raw sample is
        within the dead zone of the current state the state is left unchanged.
        """
        if self._state is not None:
            dx = x - self._state[0]
            dy = y - self._state[1]
            if (dx * dx + dy * dy) < dead_zone_px * dead_zone_px:
                return self._state
        return self.update(x, y)

    @property
    def value(self) -> Optional[Tuple[float, float]]:
        return self._state
