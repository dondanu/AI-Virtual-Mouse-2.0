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
    MOVE = "move"              # any open hand → cursor follows index tip
    LEFT_CLICK = "left_click"  # thumb + index pinch
    RIGHT_CLICK = "right_click"  # thumb + middle pinch
    SCROLL = "scroll"          # index + middle extended, ring + pinky curled
    PAUSE = "pause"            # closed fist (all tips near MCP)
    RESUME = "resume"          # open palm (all tips far from MCP)
    STEADY_AIM = "steady_aim"  # (reserved for gaming mode)
    RELOAD = "reload"          # (reserved for gaming mode)


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
        """Classify one frame. Returns the debounced gesture for this frame."""
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
            if not self._index_pinching(hand):
                self._pinch_left_down = False
            if not self._middle_pinching(hand):
                self._pinch_right_down = False

        self._set_candidate(raw)
        if raw in (GestureType.LEFT_CLICK, GestureType.RIGHT_CLICK):
            self._last_gesture = raw
        return self._last_gesture

    # ---- raw classification -------------------------------------------------

    def _classify_raw(self, hand: HandFrame) -> GestureType:
        """Classify hand gesture using tip-to-MCP distances (scale-invariant).

        Design principle: DEFAULT TO MOVE.
        The cursor follows the hand at all times unless a specific gesture
        (fist / pinch / open-palm / scroll) overrides it.

        Uses tip-to-MCP distance ratios (normalized by hand_size) which are
        invariant to camera distance — they work the same close-up and far away.

        Calibrated thresholds (tip_dist_to_MCP / hand_size):
          fist:      all 4 fingertip-MCP ratios < 0.4   → PAUSE
          open palm: all 4 fingertip-MCP ratios > 0.7   → RESUME
          scroll:    index+middle > 0.5, ring+pinky < 0.4
          else:      MOVE  (default — works for pointing, any open pose)
        """
        hs = max(hand.hand_size, 1e-6)

        # tip-to-MCP distance for each finger (index, middle, ring, pinky)
        # MCP landmarks: index=5, middle=9, ring=13, pinky=17
        tip_mcp_pairs = [(8, 5), (12, 9), (16, 13), (20, 17)]
        tm = [hand.dist(t, m) / hs for t, m in tip_mcp_pairs]
        idx_tm, mid_tm, ring_tm, pinky_tm = tm

        # ── Fist detection (MUST come before pinch) ──────────────────────────
        # In a real fist thumb+index are also very close together → would
        # falsely trigger pinch if we checked pinch first.
        # Fist: all 4 fingertips collapsed near their own MCP joints.
        if all(r < 0.4 for r in tm):
            return GestureType.PAUSE

        # ── Pinch detection ──────────────────────────────────────────────────
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

        # ── Open palm = resume ───────────────────────────────────────────────
        if all(r > 0.7 for r in tm):
            return GestureType.RESUME

        # ── Scroll: index + middle extended, ring + pinky curled ─────────────
        if idx_tm > 0.5 and mid_tm > 0.5 and ring_tm < 0.4 and pinky_tm < 0.4:
            return GestureType.SCROLL

        # ── DEFAULT: move cursor ─────────────────────────────────────────────
        # Any hand pose that isn't a fist/pinch/special gesture moves the cursor.
        # This includes: pointing (index up), relaxed open hand, any other pose.
        return GestureType.MOVE

    def pinch_active(self, hand: HandFrame) -> bool:
        """True when thumb is pinched against index or middle finger."""
        return self._index_pinching(hand) or self._middle_pinching(hand)

    def _index_pinching(self, hand: HandFrame) -> bool:
        ratio = hand.dist(4, 8) / max(hand.hand_size, 1e-6)
        s = self.settings
        threshold_adjust = max(0.0, (hand.hand_size - 0.2) * 0.1)
        on_thresh = s.pinch_on_threshold + threshold_adjust
        off_thresh = s.pinch_off_threshold + threshold_adjust
        if self._pinch_left_down:
            return ratio < off_thresh
        return ratio < on_thresh

    def _middle_pinching(self, hand: HandFrame) -> bool:
        ratio = hand.dist(4, 12) / max(hand.hand_size, 1e-6)
        s = self.settings
        threshold_adjust = max(0.0, (hand.hand_size - 0.2) * 0.1)
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
