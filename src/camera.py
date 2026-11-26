"""Camera capture pipeline running on a background thread.

Frames are captured continuously in a worker thread so the Tk UI never
blocks on the webcam. Consumers call :meth:`read` to fetch the newest
frame; nothing is written to disk and nothing leaves the machine.
"""

from __future__ import annotations

import threading
from typing import Optional, Tuple

import cv2
import numpy as np

from config import Settings


class Camera:
    """Threaded webcam capture with graceful error handling."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._cap: Optional[cv2.VideoCapture] = None
        self._lock = threading.Lock()
        self._frame: Optional[np.ndarray] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.last_error: str = ""

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> bool:
        """Open the webcam and start the capture thread.

        Returns False (and records ``last_error``) when the device cannot
        be opened, e.g. when no camera is connected.
        """
        if self._running:
            return True
        # CAP_DSHOW on Windows is fastest; fallback to default on other OS
        backend = cv2.CAP_DSHOW if hasattr(cv2, "CAP_DSHOW") else 0
        cap = cv2.VideoCapture(self._settings.camera_index, backend)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._settings.camera_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._settings.camera_height)
        cap.set(cv2.CAP_PROP_FPS, 30)                  # Request 30 fps
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)             # Only keep latest frame → less lag
        if not cap.isOpened():
            self.last_error = (
                "Could not open the webcam. Make sure a camera is connected "
                "and not used by another application."
            )
            cap.release()
            return False
        self._cap = cap
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop,
                                        daemon=True, name="camera-capture")
        self._thread.start()
        return True

    def stop(self) -> None:
        """Stop the capture thread and release the device."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        with self._lock:
            self._frame = None

    def read(self) -> Optional[np.ndarray]:
        """Return the newest BGR frame, or None when no frame is available."""
        with self._lock:
            return None if self._frame is None else self._frame.copy()

    def _capture_loop(self) -> None:
        while self._running:
            ok, frame = self._cap.read() if self._cap else (False, None)
            if not ok or frame is None:
                self.last_error = "Webcam frame capture failed; retrying."
                # Avoid a hot spin when the device stalls.
                self._running and cv2.waitKey(50)
                continue
            # Mirror horizontally so the preview behaves like a mirror,
            # which is what users expect from hand tracking.
            frame = cv2.flip(frame, 1)
            with self._lock:
                self._frame = frame

    def actual_resolution(self) -> Tuple[int, int]:
        if self._cap is not None and self._cap.isOpened():
            return (int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                    int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        return (self._settings.camera_width, self._settings.camera_height)
