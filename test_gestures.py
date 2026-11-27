"""Quick gesture sanity test — run with: python test_gestures.py"""
import math, time, sys
sys.path.insert(0, '.')

from src.hand_tracker import HandFrame
from src.gesture_detector import GestureDetector, GestureType
from config import Settings

s = Settings()

def make_hand(scenario):
    pts = [(0.5, 0.75)] * 21
    pts[0]  = (0.50, 0.90)
    pts[9]  = (0.52, 0.72)
    hs = math.hypot(pts[9][0]-pts[0][0], pts[9][1]-pts[0][1])
    if scenario == 'point_index':
        pts[8]  = (0.50, 0.30)
        pts[4]  = (0.44, 0.78)
        pts[12] = (0.52, 0.80)
        pts[16] = (0.54, 0.80)
        pts[20] = (0.56, 0.80)
    elif scenario == 'fist':
        pts[8]  = (0.50, 0.82)
        pts[4]  = (0.44, 0.84)
        pts[12] = (0.52, 0.82)
        pts[16] = (0.54, 0.83)
        pts[20] = (0.56, 0.83)
    elif scenario == 'open_palm':
        pts[8]  = (0.48, 0.30)
        pts[4]  = (0.35, 0.60)
        pts[12] = (0.50, 0.28)
        pts[16] = (0.52, 0.30)
        pts[20] = (0.54, 0.35)
    elif scenario == 'pinch':
        pts[4]  = (0.50, 0.33)
        pts[8]  = (0.50, 0.30)
        pts[12] = (0.52, 0.80)
        pts[16] = (0.54, 0.80)
        pts[20] = (0.56, 0.80)
    elif scenario == 'scroll':
        pts[8]  = (0.48, 0.30)
        pts[12] = (0.50, 0.28)
        pts[4]  = (0.44, 0.78)
        pts[16] = (0.54, 0.83)
        pts[20] = (0.56, 0.83)
    return HandFrame(landmarks=pts, label='Right',
        index_tip=pts[8], thumb_tip=pts[4], middle_tip=pts[12], hand_size=hs)

scenarios = {
    'point_index': GestureType.MOVE,
    'fist':        GestureType.PAUSE,
    'open_palm':   GestureType.RESUME,
    'pinch':       GestureType.LEFT_CLICK,
    'scroll':      GestureType.SCROLL,
}

now = time.monotonic()
all_pass = True
for name, expected in scenarios.items():
    gd = GestureDetector(settings=s)
    h = make_hand(name)
    result = None
    for i in range(5):
        result = gd.recognize(h, now + i * 0.033)
    ok = result == expected
    if not ok:
        all_pass = False
    status = "PASS" if ok else "FAIL"
    icon   = "OK" if ok else "XX"
    print(f"  {name:15s}  expected={expected.value:12s}  got={str(result.value if result else 'None'):12s}  [{icon}] {status}")

print()
print("ALL PASS" if all_pass else "SOME FAILED - check thresholds")
