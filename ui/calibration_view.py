"""Calibration page: guides the user through defining the active area."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional, TYPE_CHECKING

from config import CalibrationArea
from src.engine import EngineStatus
from ui import theme

if TYPE_CHECKING:
    from ui.app import App


class CalibrationPage(tk.Frame):
    def __init__(self, parent: tk.Frame, app: App) -> None:
        super().__init__(parent, bg=theme.BG)
        self._app = app
        self._photo = None

        self.grid(row=0, column=0, sticky="nsew")

        header = tk.Frame(self, bg=theme.BG)
        header.pack(fill=tk.X, padx=24, pady=(20, 8))
        ttk.Label(header, text="Calibration", style="Title.TLabel").pack(side=tk.LEFT)

        body = tk.Frame(self, bg=theme.BG)
        body.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 20))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        preview_card = theme.make_card(body)
        preview_card.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        self._preview = tk.Label(preview_card, bg="#000000")
        self._preview.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        panel = tk.Frame(body, bg=theme.BG)
        panel.grid(row=0, column=1, sticky="nsew")

        card = theme.make_card(panel)
        card.pack(fill=tk.X)
        ttk.Label(card, text="How it works", style="H2.TLabel"
                 ).pack(anchor="w", padx=16, pady=(14, 6))
        instructions = (
            "1. Hold your hand in front of the camera.\n"
            "2. Point your index finger to the TOP-LEFT of the area\n"
            "    you want to use, then pinch thumb + index.\n"
            "3. Point to the BOTTOM-RIGHT and pinch again.\n\n"
            "The rectangle between the two points becomes your\n"
            "active area and is mapped to the full screen."
        )
        ttk.Label(card, text=instructions, style="TLabel", justify=tk.LEFT
                 ).pack(anchor="w", padx=16, pady=(0, 8))

        self._status_label = tk.Label(panel, text="Idle", bg=theme.BG,
                                      fg=theme.FG_MUTED, font=theme.F_H2)
        self._status_label.pack(anchor="w", pady=(16, 6))

        btns = tk.Frame(panel, bg=theme.BG)
        btns.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(btns, text="Start calibration", style="Accent.TButton",
                   command=self._start).pack(side=tk.LEFT)
        ttk.Button(btns, text="Cancel", style="Ghost.TButton",
                   command=self._cancel).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(btns, text="Reset to default", style="Ghost.TButton",
                   command=self._reset).pack(side=tk.LEFT, padx=(8, 0))

        self._current_card = theme.make_card(panel)
        self._current_card.pack(fill=tk.X, pady=(16, 0))
        ttk.Label(self._current_card, text="Current active area", style="H2.TLabel"
                 ).pack(anchor="w", padx=16, pady=(12, 4))
        self._area_label = tk.Label(self._current_card, text="", bg=theme.BG_PANEL,
                                    fg=theme.FG, font=theme.F_BODY,
                                    justify=tk.LEFT)
        self._area_label.pack(anchor="w", padx=16, pady=(0, 12))
        self._refresh_area_label()

    # actions ---------------------------------------------------------------

    def _start(self) -> None:
        if self._app.engine.emergency_stopped:
            self._app.engine.reset_emergency()
        self._app.engine.start_calibration()

    def _cancel(self) -> None:
        self._app.engine.cancel_calibration()
        self._status_label.configure(text="Cancelled", fg=theme.FG_MUTED)

    def _reset(self) -> None:
        self._app.settings.calibration = CalibrationArea()
        self._app._store.save_settings(self._app.settings)
        self._refresh_area_label()
        self._status_label.configure(text="Reset to default area",
                                     fg=theme.FG_MUTED)

    def _refresh_area_label(self) -> None:
        a: CalibrationArea = self._app.settings.calibration
        self._area_label.configure(
            text=(f"x: {a.x_min:.2f} .. {a.x_max:.2f}\n"
                  f"y: {a.y_min:.2f} .. {a.y_max:.2f}"))

    # live updates -----------------------------------------------------------

    def update_status(self, status: EngineStatus) -> None:
        step_text = {
            "idle": "Idle",
            "wait_top_left": "Pinch at TOP-LEFT corner",
            "wait_bottom_right": "Pinch at BOTTOM-RIGHT corner",
            "done": "Calibration complete",
        }.get(status.calibration_step, status.calibration_step)
        text = step_text
        if status.calibration_step.startswith("wait_"):
            text += f"  ({status.calibration_countdown:.0f}s)"
        fg = theme.ACCENT if status.calibration_step == "done" else (
            theme.WARNING if status.calibration_step.startswith("wait_")
            else theme.FG_MUTED)
        self._status_label.configure(text=text, fg=fg)

        engine = self._app.engine
        if engine._calibration.step.value == "done":
            area = engine._settings.calibration
            self._refresh_area_label()

        frame = engine.get_overlay_frame()
        if frame is not None:
            import cv2
            from PIL import Image, ImageTk
            h = max(self._preview.winfo_height(), 1)
            w = max(self._preview.winfo_width(), 1)
            frame = cv2.resize(frame, (w, h))
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self._photo = ImageTk.PhotoImage(Image.fromarray(rgb))
            self._preview.configure(image=self._photo)

    def on_show(self) -> None:
        self._refresh_area_label()
