"""Gesture recognition with hysteresis, debounce, and click cooldowns."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from config import Settings
from src.hand_tracker import HandFrame


class GestureType(Enum):
    NONE = "none"
    MOVE = "move"              # index pointing
    LEFT_CLICK = "left_click"  # thumb + index pinch
    RIGHT_CLICK = "right_click"  # thumb + middle pinch
    SCROLL = "scroll"          # index + middle extended, moving vertically
    PAUSE = "pause"            # closed fist
    RESUME = "resume"          # open palm
    STEADY_AIM = "steady_aim"  # three fingers up (index + middle + ring) - slow precision mode
    RELOAD = "reload"          # four fingers up (index + middle + ring + pinky)


@dataclass
class GestureDetector:
    """Stateful gesture recognizer for the primary (first detected) hand.

    Implements:
      * pinch hysteresis (separate on/off thresholds),
      * a click cooldown so one pinch yields exactly one click,
      * gesture debouncing so PAUSE/RESUME require a few stable frames.
    """

    settings: Settings
    debounce_frames: int = 2

    _pinch_left_down: bool = field(default=False, init=False)
    _pinch_right_down: bool = field(default=False, init=False)
    _last_click_time: float = field(default=0.0, init=False)
    _stable_gesture: GestureType = field(default=GestureType.NONE, init=False)
    _candidate: GestureType = field(default=GestureType.NONE, init=False)
    _candidate_count: int = field(default=0, init=False)
    _last_gesture: GestureType = field(default=GestureType.NONE, init=False)

    def cooldown_elapsed(self, now: Optional[float] = None) -> bool:
        now = time.monotonic() if now is None else now
        return (now - self._last_click_time) >= self.settings.click_cooldown_s

    def _register_click(self, now: Optional[float] = None) -> bool:
        """Consume the cooldown if available; return True if click may fire."""
        now = time.monotonic() if now is None else now
        if not self.cooldown_elapsed(now):
            return False
        self._last_click_time = now
        return True

    def recognize(self, hand: Optional[HandFrame],
                  now: Optional[float] = None) -> GestureType:
        """Classify one frame. Returns the debounced gesture for this frame.

        Pinch events are edge-triggered: LEFT_CLICK / RIGHT_CLICK are emitted
        exactly once per pinch, gated by the cooldown.
        """
        if hand is None:
            self._pinch_left_down = False
            self._pinch_right_down = False
            self._set_candidate(GestureType.NONE)
            return self._last_gesture

        raw = self._classify_raw(hand)

        if raw in (GestureType.LEFT_CLICK, GestureType.RIGHT_CLICK):
            pinch_flag = "_pinch_left_down" if raw is GestureType.LEFT_CLICK \
                else "_pinch_right_down"
            already_down = getattr(self, pinch_flag)
            if already_down or not self._register_click(now):
                raw = GestureType.MOVE if raw is GestureType.LEFT_CLICK \
                    else GestureType.NONE
            setattr(self, pinch_flag, True)
        else:
            # Finger configuration left the pinch zones: reset edges.
            if not self._index_pinching(hand):
                self._pinch_left_down = False
            if not self._middle_pinching(hand):
                self._pinch_right_down = False

        self._set_candidate(raw)
        if raw in (GestureType.LEFT_CLICK, GestureType.RIGHT_CLICK):
            # Clicks are edge-triggered single-frame events (the pinch edge +
            # cooldown already prevent doubles); publish without debouncing,
            # otherwise the gesture never survives the debounce window.
            self._last_gesture = raw
        return self._last_gesture

    # ---- raw classification -------------------------------------------------

    def _classify_raw(self, hand: HandFrame) -> GestureType:
        """Classify hand gesture.

        Design principle: DEFAULT TO MOVE.
        The cursor follows the hand at all times unless a specific gesture
        (pinch / fist / open-palm) overrides it.  This is the most reliable
        strategy when finger-extension detection can be noisy.
        """
        import math as _math
        from src.hand_tracker import WRIST

        hs = max(hand.hand_size, 1e-6)
        wx, wy = hand.landmarks[WRIST]

        def d_wrist(idx: int) -> float:
            x, y = hand.landmarks[idx]
            return _math.hypot(x - wx, y - wy)

        tips = [8, 12, 16, 20]   # index, middle, ring, pinky tips
        tip_ratios = [d_wrist(t) / hs for t in tips]

        # ── Pinch detection ─────────────────────────────────────────────────
        index_pinching = self._index_pinching(hand)
        middle_pinching = self._middle_pinching(hand)

        if index_pinching and middle_pinching:
            if hand.dist(4, 8) < hand.dist(4, 12):
                middle_pinching = False
            else:
                index_pinching = False

        if index_pinching:
            return GestureType.LEFT_CLICK
        if middle_pinching:
            return GestureType.RIGHT_CLICK

        # ── Fist detection ───────────────────────────────────────────────────
        # In a fist ALL 4 fingertips collapse close to the wrist (ratio < 0.85).
        # Pointing index: index tip is far (~1.86), others ~0.7 → fist_count = 3, NOT 4.
        # Requires exactly 4 to avoid false positives on pointing gestures.
        fist_count = sum(r < 0.85 for r in tip_ratios)
        if fist_count == 4:
            return GestureType.PAUSE

        # ── Open palm = resume ───────────────────────────────────────────────
        if all(r > 1.5 for r in tip_ratios):
            return GestureType.RESUME

        # ── Scroll: index + middle far from wrist, ring + pinky close ───────
        idx_r, mid_r, ring_r, pinky_r = tip_ratios
        if idx_r > 1.4 and mid_r > 1.4 and ring_r < 0.9 and pinky_r < 0.9:
            return GestureType.SCROLL

        # ── DEFAULT: move cursor ─────────────────────────────────────────────
        # Any hand that isn't a fist/pinch/special gesture just moves.
        return GestureType.MOVE

    def pinch_active(self, hand: HandFrame) -> bool:
        """True when thumb is pinched against index or middle finger."""
        return self._index_pinching(hand) or self._middle_pinching(hand)

    def _index_pinching(self, hand: HandFrame) -> bool:
        ratio = hand.dist(4, 8) / max(hand.hand_size, 1e-6)
        s = self.settings
        # For larger hands (further from camera), allow slightly looser threshold
        # This accounts for increased measurement noise with distance
        threshold_adjust = max(0.0, (hand.hand_size - 0.2) * 0.1)
        on_thresh = s.pinch_on_threshold + threshold_adjust
        off_thresh = s.pinch_off_threshold + threshold_adjust
        if self._pinch_left_down:
            return ratio < off_thresh
        return ratio < on_thresh

    def _middle_pinching(self, hand: HandFrame) -> bool:
        ratio = hand.dist(4, 12) / max(hand.hand_size, 1e-6)
        s = self.settings
        # For larger hands (further from camera), allow slightly looser threshold
        # This accounts for increased measurement noise with distance
        threshold_adjust = max(0.0, (hand.hand_size - 0.2) * 0.1)
        # Right-click (thumb + middle) uses a significantly more lenient threshold
        # since middle finger is typically less flexible than index
        on_thresh = (s.pinch_on_threshold + 0.23) + threshold_adjust
        off_thresh = (s.pinch_off_threshold + 0.23) + threshold_adjust
        if self._pinch_right_down:
            return ratio < off_thresh
        return ratio < on_thresh

    # ---- debouncing ----------------------------------------------------------

    def _set_candidate(self, g: GestureType) -> None:
        if g is self._candidate:
            self._candidate_count += 1
        else:
            self._candidate = g
            self._candidate_count = 1
        if self._candidate_count >= self.debounce_frames:
            self._last_gesture = g
