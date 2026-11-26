"""Application entry point for AI Virtual Mouse 2.0."""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running as a script (python main.py) and as a PyInstaller bundle.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import APP_NAME, SettingsStore  # noqa: E402
from ui.app import App  # noqa: E402


def main() -> int:
    store = SettingsStore()
    app = App(store)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
