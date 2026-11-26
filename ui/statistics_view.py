"""Statistics page: lifetime click/scroll/FPS counters with reset."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from src.engine import EngineStatus
from ui import theme

if TYPE_CHECKING:
    from ui.app import App


def _fmt_duration(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h {m:02d}m {s:02d}s" if h else f"{m}m {s:02d}s"


class StatisticsPage(tk.Frame):
    def __init__(self, parent: tk.Frame, app: App) -> None:
        super().__init__(parent, bg=theme.BG)
        self._app = app
        self._values: dict[str, tk.Label] = {}

        self.grid(row=0, column=0, sticky="nsew")

        header = tk.Frame(self, bg=theme.BG)
        header.pack(fill=tk.X, padx=24, pady=(20, 8))
        ttk.Label(header, text="Statistics", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Button(header, text="Reset statistics", style="Danger.TButton",
                   command=self._reset).pack(side=tk.RIGHT)

        grid = tk.Frame(self, bg=theme.BG)
        grid.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 20))
        for col in (0, 1, 2):
            grid.grid_columnconfigure(col, weight=1)

        cards = [
            ("Left clicks", "total_left_clicks"),
            ("Right clicks", "total_right_clicks"),
            ("Scroll ticks", "total_scroll_ticks"),
            ("Active time", "total_active_seconds"),
            ("Average FPS", "average_fps"),
        ]
        for i, (title, key) in enumerate(cards):
            card = theme.make_card(grid)
            card.grid(row=i // 3, column=i % 3, sticky="nsew", padx=6, pady=6)
            ttk.Label(card, text=title.upper(), style="Muted.TLabel"
                     ).pack(anchor="w", padx=16, pady=(16, 0))
            value = tk.Label(card, text="0", bg=theme.BG_PANEL, fg=theme.FG,
                             font=(theme.FONT_FAMILY, 22, "bold"))
            value.pack(anchor="w", padx=16, pady=(4, 18))
            self._values[key] = value

        self._tracking_card = theme.make_card(grid)
        self._tracking_card.grid(row=1, column=2, sticky="nsew", padx=6, pady=6)
        ttk.Label(self._tracking_card, text="HAND TRACKING", style="Muted.TLabel"
                 ).pack(anchor="w", padx=16, pady=(16, 0))
        self._tracking_value = tk.Label(
            self._tracking_card, text="Idle", bg=theme.BG_PANEL, fg=theme.FG_MUTED,
            font=(theme.FONT_FAMILY, 22, "bold"))
        self._tracking_value.pack(anchor="w", padx=16, pady=(4, 18))

        self._refresh()

    def _refresh(self) -> None:
        st = self._app.stats.stats
        self._values["total_left_clicks"].configure(text=str(st.total_left_clicks))
        self._values["total_right_clicks"].configure(text=str(st.total_right_clicks))
        self._values["total_scroll_ticks"].configure(text=str(st.total_scroll_ticks))
        self._values["total_active_seconds"].configure(
            text=_fmt_duration(st.total_active_seconds))
        self._values["average_fps"].configure(text=f"{st.average_fps:.1f}")

    def _reset(self) -> None:
        from src.statistics import Statistics
        self._app.stats.stats = Statistics()
        self._app.stats.save()
        self._refresh()

    def update_status(self, status: EngineStatus) -> None:
        self._tracking_value.configure(
            text="Active" if status.tracking else "Idle",
            fg=theme.ACCENT if status.tracking else theme.FG_MUTED)
        self._refresh()

    def on_show(self) -> None:
        self._refresh()
