"""Click controller: emits single left/right clicks with safety gating."""

from __future__ import annotations

import time

from pynput.mouse import Button

from src.mouse_output import mouse_output


class ClickController:
    """Executes clicks only while control is enabled and after a cooldown.

    A burst guard prevents a click within the first 1.5 s after control is
    enabled, so re-enabling tracking never produces accidental clicks.
    """

    STARTUP_GUARD_S = 1.5

    def __init__(self) -> None:
        self._enabled_at: float = 0.0
        self.enabled: bool = False

    def enable(self) -> None:
        self.enabled = True
        self._enabled_at = time.monotonic()

    def disable(self) -> None:
        self.enabled = False
        mouse_output.release_all()

    def click(self, button: Button) -> bool:
        """Perform a click; returns False when suppressed by safety rules."""
        if not self.enabled:
            return False
        if (time.monotonic() - self._enabled_at) < self.STARTUP_GUARD_S:
            return False
        mouse_output.click(button)
        return True
