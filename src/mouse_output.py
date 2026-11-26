"""Mouse output abstraction built on pynput.

pynput is used instead of PyAutoGUI because it is thread-safe, supports
smooth wheel scrolling, and does not require a display restart on Windows.
All public methods are safe to call from the vision worker thread.
"""

from __future__ import annotations

import sys
from typing import List, Optional

from pynput.mouse import Button, Controller as MouseController


class MouseOutput:
    """Thin wrapper around the OS mouse with emergency-release support."""

    def __init__(self) -> None:
        self._mouse = MouseController()
        self._pressed: List[Button] = []

    # ---- movement -------------------------------------------------------

    def position(self) -> tuple[int, int]:
        x, y = self._mouse.position
        return int(x), int(y)

    def move(self, x: int, y: int) -> None:
        self._mouse.position = (x, y)

    # ---- clicks -----------------------------------------------------------

    def press(self, button: Button) -> None:
        if button not in self._pressed:
            self._pressed.append(button)
            self._mouse.press(button)

    def release(self, button: Button) -> None:
        if button in self._pressed:
            self._pressed.remove(button)
            self._mouse.release(button)

    def click(self, button: Button, times: int = 1) -> None:
        self._mouse.click(button, times)

    # ---- scroll ------------------------------------------------------------

    def scroll(self, dx: int, dy: int) -> None:
        self._mouse.scroll(dx, dy)

    # ---- safety ------------------------------------------------------------

    def release_all(self) -> None:
        """Force-release every mouse button this app may have pressed.

        Called when tracking is lost, on emergency stop, and at shutdown so
        the OS is never left with a stuck mouse button.
        """
        for button in list(self._pressed):
            try:
                self._mouse.release(button)
            except Exception:
                pass
        self._pressed.clear()


# Shared singleton so every controller talks to the same physical mouse and
# release_all() can clear anything any controller pressed.
mouse_output = MouseOutput()
