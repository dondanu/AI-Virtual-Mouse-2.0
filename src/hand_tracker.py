"""Hand tracking with MediaPipe: wraps the detector and exposes landmarks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

import mediapipe as mp
import numpy as np

# MediaPipe hand landmark indices (21 landmarks per hand).
WRIST = 0
THUMB_TIP = 4
INDEX_MCP = 5
INDEX_PIP = 6
INDEX_TIP = 8
MIDDLE_MCP = 9
MIDDLE_PIP = 10
MIDDLE_TIP = 12
RING_MCP = 13
RING_TIP = 16
PINKY_MCP = 17
PINKY_TIP = 20


@dataclass
class HandFrame:
    """All information extracted from one hand in one camera frame.

    Landmark coordinates are normalized (0..1) relative to the frame.
    """

    # 21 (x, y) normalized landmark positions.
    landmarks: List[Tuple[float, float]]
    # Handedness as reported by MediaPipe ("Left"/"Right", camera-mirrored
    # labels are normalized to the user's physical hand elsewhere).
    label: str
    # Confusion-free grip metrics
    index_tip: Tuple[float, float]
    thumb_tip: Tuple[float, float]
    middle_tip: Tuple[float, float]
    # Hand size in normalized units: distance wrist -> middle MCP. Used to
    # make pinch thresholds scale-invariant to camera distance.
    hand_size: float

    def dist(self, a: int, b: int) -> float:
        """Euclidean distance between two landmarks."""
        (x1, y1), (x2, y2) = self.landmarks[a], self.landmarks[b]
        return math.hypot(x2 - x1, y2 - y1)

    def finger_extended(self, tip: int, pip: int, mcp: int) -> bool:
        """A finger counts as extended when its tip is far from the wrist
        relative to its base joints.

        Two independent checks (either one passing = extended):
          1. Distance ordering: tip farther from wrist than both pip and mcp.
          2. Span check: tip-to-MCP distance > 90% of hand_size (robust to
             camera angle — works even when the wrist ordering fails).
        """
        wx, wy = self.landmarks[WRIST]

        def d(idx: int) -> float:
            x, y = self.landmarks[idx]
            return math.hypot(x - wx, y - wy)

        # Check 1: tip must be farther from wrist than BOTH pip and mcp
        if d(tip) > d(pip) and d(tip) > d(mcp) * 1.1:
            return True

        # Check 2: direct tip-to-MCP span (angle-independent)
        tx, ty = self.landmarks[tip]
        mx, my = self.landmarks[mcp]
        if math.hypot(tx - mx, ty - my) > self.hand_size * 0.9:
            return True

        return False

    def fingers_extended(self) -> List[bool]:
        """Extended state of [thumb, index, middle, ring, pinky]."""
        return [
            self.dist(THUMB_TIP, WRIST) > self.dist(2, WRIST) * 1.05,
            self.finger_extended(INDEX_TIP, INDEX_PIP, INDEX_MCP),
            self.finger_extended(MIDDLE_TIP, MIDDLE_PIP, MIDDLE_MCP),
            self.finger_extended(RING_TIP, 14, RING_MCP),
            self.finger_extended(PINKY_TIP, 18, PINKY_MCP),
        ]


class HandTracker:
    """Detects up to ``max_hands`` hands per frame using MediaPipe Hands."""

    def __init__(self, max_hands: int = 2, detection_confidence: float = 0.5,
                 tracking_confidence: float = 0.5) -> None:
        self._hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=max_hands,
            model_complexity=0,  # 0 = Lite model (faster for gaming)
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence,
        )
        self._draw = mp.solutions.drawing_utils
        self._draw_style = mp.solutions.drawing_styles

    def close(self) -> None:
        self._hands.close()

    def process(self, frame_bgr: np.ndarray) -> List[HandFrame]:
        """Run detection on a BGR frame; return one HandFrame per detected hand."""
        rgb = frame_bgr[:, :, ::-1]
        result = self._hands.process(rgb)
        out: List[HandFrame] = []
        if not result.multi_hand_landmarks:
            return out
        labels = result.multi_handedness or []
        for i, lm_set in enumerate(result.multi_hand_landmarks):
            pts = [(p.x, p.y) for p in lm_set.landmark]
            label = "Unknown"
            if i < len(labels):
                label = labels[i].classification[0].label
            # MediaPipe labels assume a mirrored (selfie) image; the preview
            # is mirrored, so flip the reported label to the user's real hand.
            if label == "Left":
                label = "Right"
            elif label == "Right":
                label = "Left"
            hand = HandFrame(
                landmarks=pts,
                label=label,
                index_tip=pts[INDEX_TIP],
                thumb_tip=pts[THUMB_TIP],
                middle_tip=pts[MIDDLE_TIP],
                hand_size=self._hand_size(pts),
            )
            out.append(hand)
        return out

    @staticmethod
    def _hand_size(pts: List[Tuple[float, float]]) -> float:
        (wx, wy), (mx, my) = pts[WRIST], pts[MIDDLE_MCP]
        return math.hypot(mx - wx, my - wy)

    def draw(self, frame_bgr: np.ndarray, hands: List[HandFrame]) -> np.ndarray:
        """Draw the hand skeleton onto a copy of the frame for the preview."""
        return frame_bgr  # drawing happens in the camera pipeline for efficiency
