"""Cursor mapping, EMA smoothing, calibration, and scroll tests."""

from __future__ import annotations

import pytest

from config import CalibrationArea, map_camera_to_screen
from src.calibration import CalibrationSession
from src.smoothing import EMASmoother


class TestCoordinateMapping:

    def test_center_maps_to_center(self):
        area = CalibrationArea()
        x, y = map_camera_to_screen(0.5, 0.5, area, 1920, 1080)
        assert x == 960 and y == 540

    def test_calibration_corners_map_to_screen_edges(self):
        area = CalibrationArea(0.2, 0.2, 0.8, 0.8)
        assert map_camera_to_screen(0.2, 0.2, area, 1000, 800) == (0, 0)
        assert map_camera_to_screen(0.8, 0.8, area, 1000, 800) == (999, 799)

    def test_outside_area_clamped(self):
        area = CalibrationArea(0.2, 0.2, 0.8, 0.8)
        assert map_camera_to_screen(-1.0, -1.0, area, 1000, 800) == (0, 0)
        assert map_camera_to_screen(2.0, 2.0, area, 1000, 800) == (999, 799)

    def test_never_leaves_screen(self):
        area = CalibrationArea()
        for nx in (-5.0, 0.0, 0.3, 0.7, 5.0):
            for ny in (-5.0, 0.0, 0.5, 1.0, 5.0):
                x, y = map_camera_to_screen(nx, ny, area, 1920, 1080,
                                            sensitivity=4.0)
                assert 0 <= x < 1920
                assert 0 <= y < 1080

    def test_sensitivity_scales_travel(self):
        area = CalibrationArea(0.25, 0.25, 0.75, 0.75)
        x1, _ = map_camera_to_screen(0.6, 0.5, area, 1000, 1000, sensitivity=1.0)
        x2, _ = map_camera_to_screen(0.6, 0.5, area, 1000, 1000, sensitivity=2.0)
        assert abs(x2 - 500) > abs(x1 - 500)


class TestSmoothing:

    def test_first_sample_passthrough(self):
        s = EMASmoother(alpha=0.5)
        assert s.update(100, 200) == (100.0, 200.0)

    def test_ema_converges_toward_new_samples(self):
        s = EMASmoother(alpha=0.5)
        s.update(0, 0)
        for _ in range(50):
            x, y = s.update(100, 100)
        assert 99 < x <= 100 and 99 < y <= 100

    def test_lower_alpha_is_laggier(self):
        fast = EMASmoother(alpha=0.9)
        slow = EMASmoother(alpha=0.1)
        for _ in range(3):
            a = fast.update(0, 0)[0]
            b = slow.update(0, 0)[0]
        fast.update(100, 100); slow.update(100, 100)
        a = fast.update(100, 100)[0]
        b = slow.update(100, 100)[0]
        assert a > b  # fast smoothing is closer to the target

    def test_dead_zone_suppresses_jitter(self):
        s = EMASmoother(alpha=1.0)
        s.update(500, 500)
        out = s.update_with_dead_zone(503, 501, dead_zone_px=5)
        assert out == (500.0, 500.0)

    def test_dead_zone_passes_large_moves(self):
        s = EMASmoother(alpha=1.0)
        s.update(500, 500)
        out = s.update_with_dead_zone(540, 500, dead_zone_px=5)
        assert out == (540.0, 500.0)

    def test_reset_clears_state(self):
        s = EMASmoother()
        s.update(10, 10)
        s.reset()
        assert s.value is None
        assert s.update(50, 50) == (50.0, 50.0)


class TestCalibration:

    def test_two_point_calibration_builds_area(self):
        session = CalibrationSession(timeout_s=10)
        session.start()
        assert session.update(False, (0.3, 0.3)) is None
        assert session.update(True, (0.2, 0.2)) is None        # top-left
        assert session.update(False, (0.7, 0.7)) is None
        area = session.update(True, (0.8, 0.8))                 # bottom-right
        assert area is not None
        assert area.x_min == 0.2 and area.x_max == 0.8

    def test_swapped_corners_normalized(self):
        session = CalibrationSession()
        session.start()
        session.update(True, (0.8, 0.8))
        area = session.update(True, (0.2, 0.2))
        assert area is not None
        assert area.x_min < area.x_max and area.y_min < area.y_max

    def test_degenerate_area_rejected(self):
        session = CalibrationSession()
        session.start()
        session.update(True, (0.5, 0.5))
        assert session.update(True, (0.51, 0.5)) is None
        assert session.step.value == "wait_top_left"

    def test_timeout_cancels(self):
        session = CalibrationSession(timeout_s=5)
        session.start()
        session.tick(6.0)
        assert not session.active


class TestScrollController:
    def test_scroll_accumulates_ticks(self, stub_mouse):
        from src.scroll_controller import ScrollController
        ctrl = ScrollController(jump_px=0.1, tick_px=0.01)
        ctrl.update((0.5, 0.5))
        ticks = ctrl.update((0.5, 0.2))  # moved up 0.3
        assert ticks > 0
        assert stub_mouse.scroll.called
