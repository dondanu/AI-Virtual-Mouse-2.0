"""Shared test fixtures and synthetic hand builders.

Tests never touch a real webcam or the real mouse: the mouse singleton's
methods are replaced with recording stubs so gesture logic can be
exercised deterministically.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import Settings  # noqa: E402
from src.hand_tracker import HandFrame  # noqa: E402


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def stub_mouse(monkeypatch):
    """Replace the shared mouse singleton's behavior with a recording stub."""
    stub = MagicMock()
    stub.position.return_value = (100, 100)
    import src.mouse_output as mo
    for method in ("position", "move", "press", "release", "click",
                   "scroll", "release_all"):
        monkeypatch.setattr(mo.mouse_output, method,
                            getattr(stub, method, MagicMock()))
    monkeypatch.setattr(mo.mouse_output, "position", lambda: (100, 100))
    yield stub


def make_hand(
    extended: tuple[bool, bool, bool, bool, bool] = (True, True, True, True, True),
    pinch: float | None = None,
    pinch_middle: float | None = None,
    hand_size: float = 0.2,
    thumb: tuple[float, float] | None = None,
    index: tuple[float, float] | None = None,
    middle: tuple[float, float] | None = None,
    ring: tuple[float, float] | None = None,
    pinky: tuple[float, float] | None = None,
) -> HandFrame:
    """Build a synthetic HandFrame.

    ``extended`` controls [thumb, index, middle, ring, pinky] extension.
    ``pinch`` places the thumb and index tips exactly ``pinch`` apart;
    ``pinch_middle`` does the same for thumb and middle. ``hand_size`` is
    the wrist-to-middle-MCP distance, matching what the tracker computes.
    
    Alternatively, you can specify exact fingertip positions using the
    ``thumb``, ``index``, ``middle``, ``ring``, and ``pinky`` keyword arguments.
    When explicit positions are provided for some fingers, unspecified fingers
    default to curled (down) positions.
    """
    wrist = (0.5, 0.75)

    # Check if any explicit fingertip positions were provided
    has_explicit_positions = any(x is not None for x in [thumb, index, middle, ring, pinky])
    
    # If explicit positions are provided, default unspecified fingers to curled
    if has_explicit_positions:
        # Default to curled (down) for fingers not explicitly specified
        def fingertip(x: float) -> tuple:
            return (x, 0.62)  # curled position
        
        thumb_tip = thumb if thumb is not None else fingertip(0.48)
        index_tip = index if index is not None else fingertip(0.46)
        middle_tip = middle if middle is not None else fingertip(0.50)
        ring_tip = ring if ring is not None else fingertip(0.54)
        pinky_tip = pinky if pinky is not None else fingertip(0.58)
    else:
        # Use extended parameter as before
        def fingertip(is_extended: bool, x: float) -> tuple:
            return (x, 0.38) if is_extended else (x, 0.62)

        thumb_tip = (0.32, 0.50) if extended[0] else (0.48, 0.62)
        index_tip = fingertip(extended[1], 0.46)
        middle_tip = fingertip(extended[2], 0.50)
        ring_tip = fingertip(extended[3], 0.54)
        pinky_tip = fingertip(extended[4], 0.58)

    # Override with pinch parameters if specified
    if pinch is not None:
        thumb_tip = (0.48 - pinch / 2, 0.40)
        index_tip = (0.48 + pinch / 2, 0.40)
        middle_tip = (0.52, 0.62)   # middle curled so index pinch wins
    if pinch_middle is not None:
        thumb_tip = (0.48 - pinch_middle / 2, 0.40)
        middle_tip = (0.48 + pinch_middle / 2, 0.40)
        index_tip = (0.44, 0.62)    # index curled so middle pinch wins

    # Build intermediate joints
    # For finger extension detection to work: tip must be farther from wrist than PIP and MCP
    # Extended finger: tip_y < pip_y < mcp_y < wrist_y
    # Curled finger: tip_y > pip_y (and closer to wrist overall)
    
    def make_joints(tip_pos: tuple[float, float], x_base: float) -> tuple:
        """Create intermediate joints (MCP, PIP, DIP) for a finger given its tip."""
        tip_x, tip_y = tip_pos
        wrist_x, wrist_y = wrist
        # Determine if finger appears extended based on distance from wrist
        # Extended finger: tip is far from wrist
        # Curled finger: tip is close to wrist
        import math
        tip_dist = math.hypot(tip_x - wrist_x, tip_y - wrist_y)
        is_extended = tip_dist > hand_size * 1.3  # Extended if tip is far from wrist
        
        if is_extended:
            # Extended: joints progress from wrist toward tip
            # For finger_extended() to return True: d(tip) > d(pip) > d(mcp)
            mcp_y = wrist_y - hand_size
            pip_y = (mcp_y + tip_y) / 2 + 0.05
            dip_y = (pip_y + tip_y) / 2
        else:
            # Curled: tip is close to wrist
            # For finger_extended() to return False: d(tip) < d(pip) or d(pip) < d(mcp)
            # Place PIP further from wrist than the tip
            mcp_y = wrist_y - hand_size
            pip_y = wrist_y - hand_size * 1.5  # PIP farther from wrist than tip
            dip_y = (tip_y + pip_y) / 2
        
        return ((x_base, mcp_y), (tip_x, pip_y), (tip_x, dip_y))
    
    # Thumb joints (thumb has different structure)
    thumb_x, thumb_y = thumb_tip
    thumb_is_extended = thumb_y < wrist[1] - 0.1
    if thumb_is_extended:
        thumb_joints = [(0.42, 0.68), (0.40, 0.64), (0.36, 0.58)]
    else:
        thumb_joints = [(0.48, 0.70), (0.49, 0.67), (0.49, 0.64)]
    
    # Finger joints
    index_mcp, index_pip, index_dip = make_joints(index_tip, 0.46)
    middle_mcp, middle_pip, middle_dip = make_joints(middle_tip, 0.50)
    ring_mcp, ring_pip, ring_dip = make_joints(ring_tip, 0.54)
    pinky_mcp, pinky_pip, pinky_dip = make_joints(pinky_tip, 0.58)

    pts = [
        wrist,                                                 # 0
        thumb_joints[0], thumb_joints[1], thumb_joints[2], thumb_tip,  # 1-4 thumb
        index_mcp, index_pip, index_dip, index_tip,            # 5-8 index
        middle_mcp, middle_pip, middle_dip, middle_tip,        # 9-12 middle
        ring_mcp, ring_pip, ring_dip, ring_tip,                # 13-16 ring
        pinky_mcp, pinky_pip, pinky_dip, pinky_tip,            # 17-20 pinky
    ]
    return HandFrame(
        landmarks=[(float(x), float(y)) for x, y in pts],
        label="Right",
        index_tip=(float(index_tip[0]), float(index_tip[1])),
        thumb_tip=(float(thumb_tip[0]), float(thumb_tip[1])),
        middle_tip=(float(middle_tip[0]), float(middle_tip[1])),
        hand_size=float(hand_size),
    )


def pinch_hand(pinch_ratio: float, hand_size: float = 0.2) -> HandFrame:
    """Thumb + index pinch whose distance/hand_size ratio is ``pinch_ratio``."""
    return make_hand(extended=(True, True, False, False, False),
                     pinch=pinch_ratio * hand_size, hand_size=hand_size)


def open_hand() -> HandFrame:
    return make_hand(extended=(True, True, True, True, True))


def fist_hand() -> HandFrame:
    return make_hand(extended=(False, False, False, False, False))


def pointing_hand() -> HandFrame:
    return make_hand(extended=(False, True, False, False, False))
