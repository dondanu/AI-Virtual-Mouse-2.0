"""Shared dark theme constants and styled widget builders for the UI."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


# Palette: dark professional theme with a green accent (no purple hues).
BG = "#0f1419"          # app background
BG_PANEL = "#161d24"    # card / panel background
BG_SIDEBAR = "#0b0f13"  # sidebar background
BG_INPUT = "#1e2830"
BORDER = "#28323c"
FG = "#e6edf3"          # primary text
FG_MUTED = "#8b98a5"    # secondary text
ACCENT = "#2ea043"      # green accent
ACCENT_HOVER = "#3fbf54"
ACCENT_FG = "#ffffff"
DANGER = "#d64545"
WARNING = "#d69e2e"

FONT_FAMILY = "Segoe UI"
F_TITLE = (FONT_FAMILY, 20, "bold")
F_H2 = (FONT_FAMILY, 14, "bold")
F_BODY = (FONT_FAMILY, 10)
F_BODY_BOLD = (FONT_FAMILY, 10, "bold")
F_SMALL = (FONT_FAMILY, 9)
F_SIDEBAR = (FONT_FAMILY, 11)


def configure_root(root: tk.Tk) -> None:
    root.title("AI Virtual Mouse 2.0")
    root.configure(bg=BG)
    root.geometry("1180x720")
    root.minsize(980, 640)


def setup_styles() -> None:
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure("TFrame", background=BG)
    style.configure("Panel.TFrame", background=BG_PANEL)
    style.configure("Sidebar.TFrame", background=BG_SIDEBAR)
    style.configure("TLabel", background=BG_PANEL, foreground=FG, font=F_BODY)
    style.configure("Muted.TLabel", background=BG_PANEL, foreground=FG_MUTED,
                    font=F_SMALL)
    style.configure("Title.TLabel", background=BG, foreground=FG, font=F_TITLE)
    style.configure("H2.TLabel", background=BG_PANEL, foreground=FG, font=F_H2)
    style.configure("Sidebar.TLabel", background=BG_SIDEBAR, foreground=FG,
                    font=F_SIDEBAR)
    style.configure("Status.TLabel", background=BG_PANEL, foreground=FG_MUTED,
                    font=F_BODY_BOLD)
    # Switch-style toggle button states are handled by plain tk buttons.

    style.configure("Accent.TButton", background=ACCENT, foreground=ACCENT_FG,
                    font=F_BODY_BOLD, borderwidth=0, padding=(14, 8))
    style.map("Accent.TButton",
              background=[("active", ACCENT_HOVER), ("disabled", BORDER)],
              foreground=[("disabled", FG_MUTED)])
    style.configure("Danger.TButton", background=DANGER, foreground=ACCENT_FG,
                    font=F_BODY_BOLD, borderwidth=0, padding=(14, 8))
    style.map("Danger.TButton", background=[("active", "#e05555")])
    style.configure("Ghost.TButton", background=BG_INPUT, foreground=FG,
                    font=F_BODY_BOLD, borderwidth=0, padding=(14, 8))
    style.map("Ghost.TButton", background=[("active", BORDER)])

    style.configure("Horizontal.TScale", background=BG_PANEL, foreground=FG,
                    troughcolor=BG_INPUT, borderwidth=0)
    style.configure("TSpinbox", background=BG_INPUT, foreground=FG,
                    fieldbackground=BG_INPUT, borderwidth=0, arrowcolor=FG)
    style.configure("TCombobox", background=BG_INPUT, foreground=FG,
                    fieldbackground=BG_INPUT, arrowcolor=FG, borderwidth=0)


def make_card(parent: tk.Widget) -> tk.Frame:
    """A rounded-looking panel via flat frame + border."""
    card = tk.Frame(parent, bg=BG_PANEL, highlightbackground=BORDER,
                    highlightthickness=1)
    return card


def make_switch(parent: tk.Widget, initial: bool, command) -> tk.Canvas:
    """A pill-shaped ON/OFF toggle drawn on a canvas."""
    state = {"on": initial}

    canvas = tk.Canvas(parent, width=52, height=26, bg=BG_PANEL,
                       highlightthickness=0)
    def draw() -> None:
        canvas.delete("all")
        fill = ACCENT if state["on"] else BORDER
        canvas.create_oval(2, 2, 50, 24, fill=fill, outline="")
        cx = 38 if state["on"] else 14
        canvas.create_oval(cx - 8, 5, cx + 8, 21, fill="#ffffff", outline="")
        canvas.create_text(10, 13, text="ON" if state["on"] else "OFF",
                           anchor="w" if state["on"] else "e",
                           font=("Segoe UI", 7, "bold"),
                           fill="#0f1419" if state["on"] else "#8b98a5")
    def toggle(_event=None) -> None:
        state["on"] = not state["on"]
        draw()
        command(state["on"])
    canvas.bind("<Button-1>", toggle)
    draw()
    canvas.set = lambda v: (state.__setitem__("on", bool(v)), draw())  # type: ignore
    return canvas
