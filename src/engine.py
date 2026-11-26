"""Vision engine: the threaded orchestrator connecting camera, tracking,
gestures, and mouse output. All OpenCV/MediaPipe work happens here so the
Tkinter UI thread stays responsive.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

import mediapipe as mp
from pynput.mouse import Button

from config import APP_NAME, EMERGENCY_STOP_KEY, Settings
from src.calibration import CalibrationSession, CalibrationStep
from src.camera import Camera
from src.click_controller import ClickController
from src.cursor_controller import CursorController
from src.gesture_detector import GestureType, GestureDetector
from src.hand_tracker import HandTracker
from src.mouse_output import mouse_output
from src.scroll_controller import ScrollController
from src.statistics import StatisticsTracker


@dataclass
class EngineStatus:
    """A snapshot of engine state, safe to hand to the UI thread."""

    tracking: bool = False
    hands_detected: int = 0
    fps: float = 0.0
    gesture: str = "none"
    control_enabled: bool = False
    emergency_stopped: bool = False
    calibration_step: str = "idle"
    calibration_countdown: float = 0.0
    last_error: str = ""


class VisionEngine:
    """Runs the full detect -> classify -> act loop on a background thread."""

    def __init__(self, settings: Settings, stats: StatisticsTracker,
                 screen_w: int, screen_h: int, settings_store=None) -> None:
        self._settings = settings
        self._stats = stats
        self._store_ref = settings_store
        self._screen_w = screen_w
        self._screen_h = screen_h

        self.camera = Camera(settings)
        self._tracker: Optional[HandTracker] = None
        self._gestures = GestureDetector(settings)
        self._cursor = CursorController(settings, screen_w, screen_h)
        self._clicks = ClickController()
        self._scroll = ScrollController()
        self._calibration = CalibrationSession()
        self._calibrating_during_scroll = False

        self.control_enabled = False
        self.emergency_stopped = False
        self.status = EngineStatus()
        self._status_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._latest_overlay: Optional[np.ndarray] = None
        self._overlay_lock = threading.Lock()

    # ---- lifecycle -------------------------------------------------------

    def start(self) -> bool:
        if not self.camera.start():
            with self._status_lock:
                self.status.last_error = self.camera.last_error
            return False
        self._tracker = HandTracker(max_hands=2)
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True,
                                        name="vision-engine")
        self._thread.start()
        return True

    def stop(self) -> None:
        """Shut down cleanly; never leaves a mouse button pressed."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None
        mouse_output.release_all()
        self.camera.stop()
        if self._tracker is not None:
            self._tracker.close()
            self._tracker = None

    # ---- control surface (called from UI thread) ---------------------------

    def enable_control(self) -> None:
        if self.emergency_stopped:
            return
        self.control_enabled = True
        self._clicks.enable()
        self._cursor.reset()

    def disable_control(self) -> None:
        self.control_enabled = False
        self._clicks.disable()
        mouse_output.release_all()

    def emergency_stop(self) -> None:
        """Instantly kill all control; requires an explicit reset to resume."""
        self.emergency_stopped = True
        self.control_enabled = False
        self._clicks.disable()
        mouse_output.release_all()

    def reset_emergency(self) -> None:
        self.emergency_stopped = False

    def start_calibration(self) -> None:
        self._calibration.start()

    def cancel_calibration(self) -> None:
        self._calibration.cancel()

    def apply_new_settings(self, settings: Settings) -> None:
        """Hot-apply settings; camera resolution changes need a restart."""
        needs_camera_restart = (
            settings.camera_index != self._settings.camera_index
            or settings.camera_width != self._settings.camera_width
            or settings.camera_height != self._settings.camera_height
        )
        old_calibration = self._settings.calibration
        self._settings = settings
        self._gestures.settings = settings
        self._cursor._settings = settings
        self._cursor._smoother.alpha = settings.smoothing_alpha
        self._cursor._screen_w, self._cursor._screen_h = self._screen_w, self._screen_h
        self._scroll.configure(settings.scroll_jump_px / 100.0,
                               settings.scroll_speed_px / 100.0)
        if needs_camera_restart and self.camera.is_running:
            self.camera.stop()
            self.camera = Camera(settings)
            self.camera.start()

    def set_screen_size(self, w: int, h: int) -> None:
        self._screen_w, self._screen_h = w, h
        self._cursor._screen_w, self._cursor._screen_h = w, h

    def get_status(self) -> EngineStatus:
        with self._status_lock:
            return EngineStatus(**vars(self.status))

    def get_overlay_frame(self) -> Optional[np.ndarray]:
        """Latest annotated preview frame (BGR) for the UI, or None."""
        with self._overlay_lock:
            if self._latest_overlay is None:
                return None
            return self._latest_overlay.copy()

    # ---- the vision loop ----------------------------------------------------

    def _loop(self) -> None:
        last_frame_time = time.monotonic()
        fps = 0.0
        mp_draw = mp.solutions.drawing_utils
        mp_styles = mp.solutions.drawing_styles

        while not self._stop_event.is_set():
            frame = self.camera.read()
            if frame is None:
                time.sleep(0.02)
                continue

            now = time.monotonic()
            dt = now - last_frame_time
            last_frame_time = now
            fps = fps * 0.9 + (1.0 / dt) * 0.1 if dt > 0 else fps

            assert self._tracker is not None
            hands = self._tracker.process(frame)
            annotated = frame.copy()

            gesture = GestureType.NONE
            if hands:
                primary = hands[0]
                # Draw skeleton using the landmarks we still hold in `frame`.
                self._draw_skeleton(annotated, primary)
                gesture = self._gestures.recognize(primary, now)
                self._act_on_gesture(gesture, primary, dt)
                if self._calibration.active:
                    area = self._calibration.update(
                        self._gestures.pinch_active(primary),
                        primary.index_tip,
                    )
                    if area is not None:
                        self._settings.calibration = area
                        self._store_ref.save_settings(self._settings)
            else:
                self._gestures.recognize(None, now)
                if self.control_enabled:
                    # Tracking lost: release held buttons but keep control ON
                    # so the user does not need to re-enable after a brief occlusion.
                    mouse_output.release_all()

            self._calibration.tick(dt)
            self._render_overlay(annotated, hands, gesture)

            with self._status_lock:
                self.status = EngineStatus(
                    tracking=bool(hands),
                    hands_detected=len(hands),
                    fps=fps,
                    gesture=gesture.value,
                    control_enabled=self.control_enabled,
                    emergency_stopped=self.emergency_stopped,
                    calibration_step=self._calibration.step.value,
                    calibration_countdown=self._calibration.remaining(),
                    last_error=self.camera.last_error,
                )
            self._stats.stats.record_frame(fps)
            if self.control_enabled:
                self._stats.stats.add_active_time(dt)

        mouse_output.release_all()

    def _draw_skeleton(self, frame: np.ndarray, hand) -> None:
        """Draw landmarks + connections for the detected hand."""
        h, w = frame.shape[:2]
        pts = [(int(p[0] * w), int(p[1] * h)) for p in hand.landmarks]
        connections = mp.solutions.hands.HAND_CONNECTIONS
        for a, b in connections:
            cv2.line(frame, pts[a], pts[b], (80, 220, 100), 2, cv2.LINE_AA)
        for p in pts:
            cv2.circle(frame, p, 4, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(frame, pts[8], 7, (0, 140, 255), -1, cv2.LINE_AA)

    def _act_on_gesture(self, gesture: GestureType, hand, dt: float) -> None:
        s = self._settings
        if not self.control_enabled:
            return
        fingertip = hand.index_tip

        if gesture is GestureType.MOVE and s.enable_move:
            self._scroll.reset()
            self._cursor.update(fingertip)
        elif gesture is GestureType.LEFT_CLICK and s.enable_left_click:
            if self._clicks.click(Button.left):
                self._stats.record_click("left")
        elif gesture is GestureType.RIGHT_CLICK and s.enable_right_click:
            if self._clicks.click(Button.right):
                self._stats.record_click("right")
        elif gesture is GestureType.SCROLL and s.enable_scroll:
            ticks = self._scroll.update(fingertip)
            if ticks:
                self._stats.record_scroll(ticks)

    def _render_overlay(self, frame: np.ndarray, hands, gesture: GestureType) -> None:
        """Draw HUD text: status, gesture, calibration guide."""
        h, w = frame.shape[:2]
        color = (80, 220, 100) if self.control_enabled else (60, 60, 240)
        state = "CONTROL ON" if self.control_enabled else "CONTROL OFF"
        if self.emergency_stopped:
            state = f"EMERGENCY STOP ({EMERGENCY_STOP_KEY} to reset)"
            color = (0, 0, 255)
        cv2.putText(frame, f"{APP_NAME}  |  {state}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)

        if self._calibration.active:
            step = ("Pinch at TOP-LEFT corner"
                    if self._calibration.step is CalibrationStep.WAIT_TOP_LEFT
                    else "Pinch at BOTTOM-RIGHT corner")
            cv2.putText(frame, f"{step}  ({self._calibration.remaining():.0f}s)",
                        (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (0, 200, 255), 2, cv2.LINE_AA)

        cv2.putText(frame, f"Gesture: {gesture.value}", (10, h - 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
        with self._overlay_lock:
            self._latest_overlay = frame
