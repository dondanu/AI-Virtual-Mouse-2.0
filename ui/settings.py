"""Settings page: sliders and controls for all user-adjustable options."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Dict, TYPE_CHECKING

from config import Settings
from ui import theme

if TYPE_CHECKING:
    from ui.app import App


class SettingsPage(tk.Frame):
    def __init__(self, parent: tk.Frame, app: App) -> None:
        super().__init__(parent, bg=theme.BG)
        self._app = app
        self._sliders: Dict[str, tk.Scale] = {}
        self._bools: Dict[str, tk.BooleanVar] = {}

        self.grid(row=0, column=0, sticky="nsew")

        header = tk.Frame(self, bg=theme.BG)
        header.pack(fill=tk.X, padx=24, pady=(20, 8))
        ttk.Label(header, text="Settings", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Button(header, text="Save settings", style="Accent.TButton",
                   command=self._save).pack(side=tk.RIGHT)

        canvas = tk.Canvas(self, bg=theme.BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        self._scroll_frame = tk.Frame(canvas, bg=theme.BG)
        self._scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self._scroll_frame, anchor="nw",
                             tags="inner")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(24, 0),
                    pady=(0, 20))
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 20), padx=(0, 8))

        s = app.settings

        cursor_card = self._card("Cursor control")
        self._slider(cursor_card, "Sensitivity", 0.5, 4.0, s.sensitivity,
                     "sensitivity", resolution=0.05)
        self._slider(cursor_card, "Smoothing strength (lower = smoother)",
                     0.05, 0.95, s.smoothing_alpha, "smoothing_alpha",
                     resolution=0.05)
        self._slider(cursor_card, "Dead zone (px)", 0, 30, s.dead_zone_px,
                     "dead_zone_px", resolution=1)

        gesture_card = self._card("Gesture thresholds")
        self._slider(gesture_card, "Pinch ON threshold", 0.05, 0.9,
                     s.pinch_on_threshold, "pinch_on_threshold", resolution=0.01)
        self._slider(gesture_card, "Pinch OFF threshold (hysteresis)", 0.07,
                     0.95, s.pinch_off_threshold, "pinch_off_threshold",
                     resolution=0.01)
        self._slider(gesture_card, "Click cooldown (s)", 0.1, 2.0,
                     s.click_cooldown_s, "click_cooldown_s", resolution=0.05)
        self._slider(gesture_card, "Scroll sensitivity (px per tick)", 5, 200,
                     s.scroll_jump_px, "scroll_jump_px", resolution=5)
        self._slider(gesture_card, "Scroll speed (wheel px per tick)", 2, 80,
                     s.scroll_speed_px, "scroll_speed_px", resolution=2)

        toggles_card = self._card("Enable gestures")
        self._toggle(toggles_card, "Cursor movement", s.enable_move, "enable_move")
        self._toggle(toggles_card, "Left click (thumb + index pinch)",
                     s.enable_left_click, "enable_left_click")
        self._toggle(toggles_card, "Right click (thumb + middle pinch)",
                     s.enable_right_click, "enable_right_click")
        self._toggle(toggles_card, "Vertical scrolling (two fingers)",
                     s.enable_scroll, "enable_scroll")

        camera_card = self._card("Camera")
        row = tk.Frame(camera_card, bg=theme.BG_PANEL)
        row.pack(fill=tk.X, padx=16, pady=(4, 12))
        ttk.Label(row, text="Camera index", style="TLabel"
                 ).pack(side=tk.LEFT)
        self._camera_spin = ttk.Spinbox(row, from_=0, to=8, width=6,
                                        values=[str(i) for i in range(9)])
        self._camera_spin.set(s.camera_index)
        self._camera_spin.pack(side=tk.RIGHT)

        res_row = tk.Frame(camera_card, bg=theme.BG_PANEL)
        res_row.pack(fill=tk.X, padx=16, pady=(0, 12))
        ttk.Label(res_row, text="Resolution", style="TLabel").pack(side=tk.LEFT)
        self._res_combo = ttk.Combobox(res_row, state="readonly", width=14,
                                       values=["640x480", "1280x720", "1920x1080"])
        self._res_combo.set(f"{s.camera_width}x{s.camera_height}")
        self._res_combo.pack(side=tk.RIGHT)

    # helpers ----------------------------------------------------------------

    def _card(self, title: str) -> tk.Frame:
        card = theme.make_card(self._scroll_frame)
        card.pack(fill=tk.X, pady=(0, 14), ipady=2)
        ttk.Label(card, text=title, style="H2.TLabel"
                 ).pack(anchor="w", padx=16, pady=(14, 6))
        return card

    def _slider(self, parent: tk.Frame, label: str, low: float, high: float,
                value: float, key: str, resolution: float) -> None:
        row = tk.Frame(parent, bg=theme.BG_PANEL)
        row.pack(fill=tk.X, padx=16, pady=4)
        ttk.Label(row, text=label, style="TLabel").pack(side=tk.TOP, anchor="w")
        scale = tk.Scale(row, from_=low, to=high, resolution=resolution,
                         orient=tk.HORIZONTAL, bg=theme.BG_PANEL,
                         fg=theme.FG, troughcolor=theme.BG_INPUT,
                         highlightthickness=0, bd=0, length=380)
        scale.set(value)
        scale.pack(fill=tk.X)
        self._sliders[key] = scale

    def _toggle(self, parent: tk.Frame, label: str, value: bool, key: str) -> None:
        var = tk.BooleanVar(value=value)
        cb = tk.Checkbutton(parent, text=label, variable=var,
                            bg=theme.BG_PANEL, fg=theme.FG,
                            activebackground=theme.BG_PANEL,
                            activeforeground=theme.FG, selectcolor=theme.BG_INPUT,
                            font=theme.F_BODY, relief=tk.FLAT, bd=0,
                            cursor="hand2")
        cb.pack(anchor="w", padx=16, pady=4)
        self._bools[key] = var

    def _on_mousewheel(self, event) -> None:
        # Only scroll when the settings page is visible.
        if not self.winfo_ismapped():
            return
        self._scroll_frame.master.yview_scroll(-event.delta // 120, "units")

    # persistence ----------------------------------------------------------------

    def _collect(self) -> Settings:
        s = self._app.settings
        for key, scale in self._sliders.items():
            setattr(s, key, scale.get())
        for key, var in self._bools.items():
            setattr(s, key, var.get())
        s.camera_index = int(self._camera_spin.get() or 0)
        w, h = self._res_combo.get().split("x")
        s.camera_width, s.camera_height = int(w), int(h)
        return s

    def _save(self) -> None:
        s = self._collect()
        self._app._store.save_settings(s)
        self._app.engine.apply_new_settings(s)
        messagebox.showinfo(
            "Settings saved",
            "Settings saved. Camera changes restart the preview automatically.")

    def on_show(self) -> None:
        pass

    def update_status(self, _status) -> None:
        pass
