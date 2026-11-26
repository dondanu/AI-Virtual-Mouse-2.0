"""Dashboard page: live preview, tracking status, FPS, gesture, control switch."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional, TYPE_CHECKING

import cv2
from PIL import Image, ImageTk

from config import APP_NAME
from src.engine import EngineStatus
from ui import theme

if TYPE_CHECKING:
    from ui.app import App

GESTURE_LABELS = {
    "none": "No gesture",
    "move": "Move cursor",
    "left_click": "Left click",
    "right_click": "Right click",
    "scroll": "Scrolling",
    "pause": "Paused (fist)",
    "resume": "Resumed (palm)",
    "steady_aim": "🎯 Steady Aim (3 fingers)",
    "reload": "🔄 Reload (4 fingers)",
}


class DashboardPage(tk.Frame):
    def __init__(self, parent: tk.Frame, app: App) -> None:
        super().__init__(parent, bg=theme.BG)
        self._app = app
        self._photo: Optional[ImageTk.PhotoImage] = None

        self.grid(row=0, column=0, sticky="nsew")
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        header = tk.Frame(self, bg=theme.BG)
        header.pack(fill=tk.X, padx=24, pady=(20, 8))
        ttk.Label(header, text="Dashboard", style="Title.TLabel"
                 ).pack(side=tk.LEFT)
        self._switch = theme.make_switch(header, False, self._on_toggle_control)
        self._switch.pack(side=tk.RIGHT)
        tk.Label(header, text="Mouse control", bg=theme.BG, fg=theme.FG_MUTED,
                 font=theme.F_BODY).pack(side=tk.RIGHT, padx=(0, 10))

        body = tk.Frame(self, bg=theme.BG)
        body.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 20))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        # Live preview card
        preview_card = theme.make_card(body)
        preview_card.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        self._preview = tk.Label(preview_card, bg="#000000")
        self._preview.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        self._preview.bind("<Configure>", self._keep_ratio)

        # Right status column
        right = tk.Frame(body, bg=theme.BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(5, weight=1)

        self._tracking_card = self._status_card(right, "Hand tracking")
        self._tracking_value = self._status_value(self._tracking_card, "Waiting...")
        self._fps_card = self._status_card(right, "FPS")
        self._fps_value = self._status_value(self._fps_card, "0.0")
        self._gesture_card = self._status_card(right, "Current gesture")
        self._gesture_value = self._status_value(self._gesture_card, "-")
        self._control_card = self._status_card(right, "Control state")
        self._control_value = self._status_value(self._control_card, "OFF")

        self._emergency = tk.Button(
            right, text="EMERGENCY STOP  (F10)", bg=theme.DANGER, fg="white",
            font=theme.F_BODY_BOLD, relief=tk.FLAT, bd=0, pady=10,
            activebackground="#e05555", cursor="hand2",
            command=self._app.engine.emergency_stop)
        self._emergency.pack(fill=tk.X, pady=(12, 0), ipady=2)

    # helpers ----------------------------------------------------------------

    def _status_card(self, parent: tk.Frame, title: str) -> tk.Frame:
        card = theme.make_card(parent)
        card.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(card, text=title.upper(), style="Muted.TLabel"
                 ).pack(anchor="w", padx=16, pady=(12, 0))
        return card

    def _status_value(self, card: tk.Frame, initial: str) -> tk.Label:
        lbl = tk.Label(card, text=initial, bg=theme.BG_PANEL, fg=theme.FG,
                       font=(theme.FONT_FAMILY, 16, "bold"))
        lbl.pack(anchor="w", padx=16, pady=(2, 14))
        return lbl

    # control -----------------------------------------------------------------

    def _on_toggle_control(self, enabled: bool) -> None:
        if self._app.engine.emergency_stopped:
            self._app.engine.reset_emergency()
        if enabled:
            self._app.engine.enable_control()
        else:
            self._app.engine.disable_control()
        self._control_value.configure(
            text="ON" if enabled else "OFF",
            fg=theme.ACCENT if enabled else theme.FG_MUTED)

    def set_control_switch(self, enabled: bool) -> None:
        self._switch.set(enabled)
        self._control_value.configure(
            text="ON" if enabled else "OFF",
            fg=theme.ACCENT if enabled else theme.FG_MUTED)

    # periodic updates ----------------------------------------------------------

    def update_status(self, status: EngineStatus) -> None:
        self._tracking_value.configure(
            text=("Tracking" if status.tracking else "No hand"),
            fg=theme.ACCENT if status.tracking else theme.WARNING)
        self._fps_value.configure(text=f"{status.fps:.1f}")
        self._gesture_value.configure(
            text=GESTURE_LABELS.get(status.gesture, status.gesture))
        if not self._app.engine.control_enabled or status.emergency_stopped:
            self._control_value.configure(
                text="EMERGENCY" if status.emergency_stopped else "OFF",
                fg=theme.DANGER if status.emergency_stopped else theme.FG_MUTED)
        self._draw_preview()

    def _draw_preview(self) -> None:
        frame = self._app.engine.get_overlay_frame()
        if frame is None:
            return
        label_w = max(self._preview.winfo_width(), 1)
        label_h = max(self._preview.winfo_height(), 1)
        frame = cv2.resize(frame, (label_w, label_h))
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        self._photo = ImageTk.PhotoImage(img)
        self._preview.configure(image=self._photo)

    def _keep_ratio(self, _event=None) -> None:
        pass
