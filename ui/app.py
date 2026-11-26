"""Main application window with sidebar navigation and page container."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import Callable, Dict, Optional

from pynput import keyboard as pynput_kb

from config import APP_NAME, APP_VERSION, EMERGENCY_STOP_KEY, Settings, SettingsStore
from src.engine import VisionEngine
from src.mouse_output import mouse_output
from src.statistics import StatisticsTracker
from ui import theme
from ui.dashboard import DashboardPage
from ui.settings import SettingsPage
from ui.calibration_view import CalibrationPage
from ui.statistics_view import StatisticsPage


class App(tk.Tk):
    """Top-level window: sidebar + stacked pages + global emergency stop."""

    def __init__(self, store: SettingsStore) -> None:
        super().__init__()
        self._store = store
        self.settings: Settings = store.load_settings()
        self.stats = StatisticsTracker(store.stats_path)

        theme.configure_root(self)
        theme.setup_styles()

        import ctypes
        try:
            user32 = ctypes.windll.user32
            self._screen_w = user32.GetSystemMetrics(0)
            self._screen_h = user32.GetSystemMetrics(1)
        except Exception:
            self._screen_w = self.winfo_screenwidth()
            self._screen_h = self.winfo_screenheight()

        self.engine = VisionEngine(self.settings, self.stats,
                                   self._screen_w, self._screen_h,
                                   settings_store=store)

        self._pages: Dict[str, tk.Frame] = {}
        self._nav_buttons: Dict[str, tk.Button] = {}
        self._build_sidebar()
        self._container = tk.Frame(self, bg=theme.BG)
        self._container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_pages()
        self.show_page("Dashboard")

        self._install_emergency_stop()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        if not self.engine.start():
            messagebox.showerror(
                APP_NAME,
                "The webcam could not be started.\n\n"
                + (self.engine.get_status().last_error or "Unknown error.")
                + "\n\nYou can still explore the interface and adjust settings.",
            )
        self._poll_status()

    # ---- layout -------------------------------------------------------------

    def _build_sidebar(self) -> None:
        sidebar = tk.Frame(self, bg=theme.BG_SIDEBAR, width=210)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="AI Virtual Mouse", bg=theme.BG_SIDEBAR,
                 fg=theme.FG, font=(theme.FONT_FAMILY, 13, "bold")
                 ).pack(pady=(24, 2), anchor="w", padx=20)
        tk.Label(sidebar, text=f"Version {APP_VERSION}", bg=theme.BG_SIDEBAR,
                 fg=theme.FG_MUTED, font=theme.F_SMALL
                 ).pack(anchor="w", padx=20)

        tk.Frame(sidebar, bg=theme.BORDER, height=1).pack(fill=tk.X, pady=14)

        for name in ("Dashboard", "Calibration", "Settings", "Statistics"):
            btn = tk.Button(
                sidebar, text=name, anchor="w", padx=20, pady=10,
                bg=theme.BG_SIDEBAR, fg=theme.FG_MUTED,
                activebackground=theme.BG_INPUT, activeforeground=theme.FG,
                font=theme.F_SIDEBAR, relief=tk.FLAT, bd=0,
                cursor="hand2", command=lambda n=name: self.show_page(n),
            )
            btn.pack(fill=tk.X)
            self._nav_buttons[name] = btn

        footer = tk.Frame(sidebar, bg=theme.BG_SIDEBAR)
        footer.pack(side=tk.BOTTOM, fill=tk.X, pady=16)
        tk.Label(footer, text=f"Emergency stop: {EMERGENCY_STOP_KEY}",
                 bg=theme.BG_SIDEBAR, fg=theme.WARNING, font=theme.F_SMALL
                 ).pack(anchor="w", padx=20)
        self._stop_btn = tk.Button(
            footer, text="EMERGENCY STOP", bg=theme.DANGER, fg="white",
            font=theme.F_BODY_BOLD, relief=tk.FLAT, bd=0, pady=8,
            activebackground="#e05555", command=self.engine.emergency_stop,
        )
        self._stop_btn.pack(fill=tk.X, padx=16, pady=(6, 0))

    def _build_pages(self) -> None:
        pages = {
            "Dashboard": DashboardPage,
            "Settings": SettingsPage,
            "Calibration": CalibrationPage,
            "Statistics": StatisticsPage,
        }
        for name, cls in pages.items():
            page = cls(self._container, self)
            self._pages[name] = page

    def show_page(self, name: str) -> None:
        for n, btn in self._nav_buttons.items():
            active = n == name
            btn.configure(
                fg=theme.FG if active else theme.FG_MUTED,
                bg=theme.BG_INPUT if active else theme.BG_SIDEBAR,
            )
        page = self._pages[name]
        page.tkraise()
        if hasattr(page, "on_show"):
            page.on_show()

    # ---- emergency stop -------------------------------------------------------

    def _install_emergency_stop(self) -> None:
        def on_key(key) -> None:
            try:
                if key == pynput_kb.Key.f10:
                    self.after(0, self._on_emergency)
            except Exception:
                pass
        self._kb_listener = pynput_kb.Listener(on_press=on_key, daemon=True)
        self._kb_listener.start()
        self.bind_all(f"<{EMERGENCY_STOP_KEY}>",
                      lambda e: self._on_emergency())

    def _on_emergency(self) -> None:
        self.engine.emergency_stop()
        # reflect state immediately in the dashboard toggle
        dash = self._pages.get("Dashboard")
        if hasattr(dash, "set_control_switch"):
            dash.set_control_switch(False)
        self.engine.reset_emergency()

    # ---- periodic status polling ----------------------------------------------

    def _poll_status(self) -> None:
        if not self.winfo_exists():
            return
        status = self.engine.get_status()
        for page in self._pages.values():
            if hasattr(page, "update_status"):
                page.update_status(status)
        self.after(100, self._poll_status)

    # ---- shutdown --------------------------------------------------------------

    def _on_close(self) -> None:
        if messagebox.askokcancel(
                "Quit", "Quit AI Virtual Mouse? Mouse control will be released."):
            self.stats.save()
            self._store.save_settings(self.settings)
            self.engine.stop()
            mouse_output.release_all()
            self.destroy()
