"""Gesture recognition, pinch detection, and click cooldown tests."""

from __future__ import annotations

from src.gesture_detector import GestureDetector, GestureType
from tests.conftest import make_hand


def pinch_hand(pinch_ratio: float, hand_size: float = 0.2):
    """Hand with thumb and index separated by pinch_ratio * hand_size."""
    # pinch_ratio is the desired ratio of distance/hand_size
    # So the absolute distance is pinch_ratio * hand_size
    pinch_distance = pinch_ratio * hand_size
    y = 0.40
    thumb = (0.50 - pinch_distance / 2, y)
    index = (0.50 + pinch_distance / 2, y)
    # Don't set middle=index - let it default to curled for proper pinch detection
    return make_hand(thumb=thumb, index=index, hand_size=hand_size)


def open_hand():
    return make_hand(
        thumb=(0.30, 0.60), index=(0.45, 0.35), middle=(0.50, 0.32),
        ring=(0.55, 0.33), pinky=(0.60, 0.36))


def fist_hand():
    return make_hand(
        thumb=(0.48, 0.55), index=(0.50, 0.52), middle=(0.51, 0.52),
        ring=(0.52, 0.53), pinky=(0.53, 0.54))


def pointing_hand():
    return make_hand(
        thumb=(0.40, 0.55), index=(0.50, 0.30), middle=(0.52, 0.50),
        ring=(0.54, 0.50), pinky=(0.56, 0.50))


class TestPinchDetection:

    def test_pinch_engages_below_on_threshold(self, settings):
        gd = GestureDetector(settings)
        close = pinch_hand(settings.pinch_on_threshold * 0.5)
        assert gd._classify_raw(close) is GestureType.LEFT_CLICK

    def test_pinch_hysteresis_holds_until_off_threshold(self, settings):
        gd = GestureDetector(settings)
        gd._pinch_left_down = True
        mid = pinch_hand((settings.pinch_on_threshold
                          + settings.pinch_off_threshold) / 2)
        assert gd._index_pinching(mid) is True
        far = pinch_hand(settings.pinch_off_threshold * 2)
        assert gd._index_pinching(far) is False

    def test_pinch_scales_with_hand_size(self, settings):
        gd = GestureDetector(settings)
        close_far = pinch_hand(0.30, hand_size=0.6)
        assert gd._classify_raw(close_far) is GestureType.LEFT_CLICK


class TestGestures:

    def test_fist_is_pause(self, settings):
        gd = GestureDetector(settings)
        assert gd._classify_raw(fist_hand()) is GestureType.PAUSE

    def test_open_palm_is_resume(self, settings):
        gd = GestureDetector(settings)
        assert gd._classify_raw(open_hand()) is GestureType.RESUME

    def test_pointing_is_move(self, settings):
        gd = GestureDetector(settings)
        assert gd._classify_raw(pointing_hand()) is GestureType.MOVE

    def test_no_hand_resets_state(self, settings):
        gd = GestureDetector(settings)
        gd.recognize(make_hand())
        gd.recognize(None)
        assert gd._pinch_left_down is False
        assert gd._last_gesture is GestureType.NONE


class TestClickCooldown:

    def test_second_click_within_cooldown_suppressed(self, settings):
        gd = GestureDetector(settings, debounce_frames=1)
        t = 100.0
        h = pinch_hand(settings.pinch_on_threshold * 0.5)
        assert gd.recognize(h, now=t) is GestureType.LEFT_CLICK
        assert gd.recognize(h, now=t + 0.1) is not GestureType.LEFT_CLICK

    def test_click_after_cooldown_fires_again(self, settings):
        gd = GestureDetector(settings, debounce_frames=1)
        t = 100.0
        h = pinch_hand(settings.pinch_on_threshold * 0.5)
        gd.recognize(h, now=t)
        gd.recognize(make_hand(), now=t + 0.05)  # release
        assert gd.recognize(h, now=t + settings.click_cooldown_s + 0.01) \
            is GestureType.LEFT_CLICK

    def test_right_click_emits_once(self, settings):
        gd = GestureDetector(settings, debounce_frames=1)
        h = make_hand(thumb=(0.50, 0.50), index=(0.60, 0.40),
                      middle=(0.50, 0.40), hand_size=0.2)
        t = 50.0
        first = gd.recognize(h, now=t)
        second = gd.recognize(h, now=t + 0.1)
        assert first is GestureType.RIGHT_CLICK
        assert second is not GestureType.RIGHT_CLICK
