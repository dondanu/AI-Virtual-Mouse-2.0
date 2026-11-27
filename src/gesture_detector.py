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
        extended = hand.fingers_extended()
        thumb_up, index_up, middle_up, ring_up, pinky_up = extended
        n_extended = sum(extended)

        # Fist check first: if no fingers are extended, it's a fist regardless of distances
        if n_extended == 0:
            return GestureType.PAUSE

        # Check for pinches - pinch detection doesn't require finger to be "extended"
        # since pinching brings the tip close to thumb, which may curl the finger slightly
        index_pinching = self._index_pinching(hand)
        middle_pinching = self._middle_pinching(hand)
        
        # Distinguish fist from pinch: in a fist, ALL fingertips are close to thumb
        # In a pinch, only ONE finger is close. Check if at least 3 fingers are close to thumb.
        if index_pinching or middle_pinching:
            # Count how many fingertips are close to thumb
            thumb_index_ratio = hand.dist(4, 8) / max(hand.hand_size, 1e-6)
            thumb_middle_ratio = hand.dist(4, 12) / max(hand.hand_size, 1e-6)
            thumb_ring_ratio = hand.dist(4, 16) / max(hand.hand_size, 1e-6)
            thumb_pinky_ratio = hand.dist(4, 20) / max(hand.hand_size, 1e-6)
            
            # Count fingers close to thumb (within tight threshold for fist detection)
            close_threshold = 0.4  # tighter threshold to detect actual fist
            close_count = sum([
                thumb_index_ratio < close_threshold,
                thumb_middle_ratio < close_threshold,
                thumb_ring_ratio < close_threshold,
                thumb_pinky_ratio < close_threshold
            ])
            
            # If 3+ fingers are bunched with thumb, it's a fist, not a pinch
            if close_count >= 3:
                return GestureType.PAUSE
        
        # If both are pinching, prefer the one that's closer (smaller ratio)
        if index_pinching and middle_pinching:
            index_ratio = hand.dist(4, 8) / max(hand.hand_size, 1e-6)
            middle_ratio = hand.dist(4, 12) / max(hand.hand_size, 1e-6)
            if index_ratio < middle_ratio:
                middle_pinching = False
            else:
                index_pinching = False
        
        if index_pinching:
            return GestureType.LEFT_CLICK
        if middle_pinching:
            return GestureType.RIGHT_CLICK

        if n_extended >= 5:
            return GestureType.RESUME
        
        # Gaming gestures: 4 fingers for reload, 3 fingers for steady aim
        if n_extended == 4 and not thumb_up:
            # Four fingers up (no thumb) = RELOAD
            return GestureType.RELOAD
        
        if n_extended == 3 and index_up and middle_up and ring_up and not pinky_up:
            # Three fingers up (index + middle + ring) = STEADY_AIM mode
            return GestureType.STEADY_AIM
        
        # Partial fist: only thumb extended (or nothing). But if INDEX is up,
        # it's a pointing gesture — must NOT be treated as pause.
        if n_extended <= 1 and not index_up:
            return GestureType.PAUSE
        
        # Scroll gesture: both index and middle extended, no pinch
        if index_up and middle_up and not ring_up and not pinky_up:
            return GestureType.SCROLL
        if index_up:
            return GestureType.MOVE
        return GestureType.NONE

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
