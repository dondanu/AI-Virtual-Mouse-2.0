"""Statistics tracking with optional JSON persistence."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Statistics:
    total_left_clicks: int = 0
    total_right_clicks: int = 0
    total_scroll_ticks: int = 0
    total_active_seconds: float = 0.0
    fps_samples: int = 0
    fps_sum: float = 0.0

    @property
    def average_fps(self) -> float:
        return self.fps_sum / self.fps_samples if self.fps_samples else 0.0

    def record_frame(self, fps: float) -> None:
        self.fps_samples += 1
        self.fps_sum += fps

    def add_active_time(self, seconds: float) -> None:
        self.total_active_seconds += seconds


class StatisticsTracker:
    """Thread-safe statistics collector; persistence is written on demand."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.stats = Statistics()
        self._path = path
        self._load()

    def _load(self) -> None:
        if self._path is None:
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            for key, value in data.items():
                if hasattr(self.stats, key):
                    setattr(self.stats, key, type(getattr(self.stats, key))(value))
        except (OSError, json.JSONDecodeError, ValueError, TypeError):
            pass

    def save(self) -> None:
        if self._path is None:
            return
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(asdict(self.stats), indent=2), encoding="utf-8")
        except OSError:
            pass

    # ---- mutation helpers ----------------------------------------------------

    def record_click(self, button: str) -> None:
        if button == "left":
            self.stats.total_left_clicks += 1
        elif button == "right":
            self.stats.total_right_clicks += 1

    def record_scroll(self, ticks: int) -> None:
        self.stats.total_scroll_ticks += abs(ticks)
