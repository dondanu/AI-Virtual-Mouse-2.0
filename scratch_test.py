import math, time
from src.hand_tracker import HandFrame, WRIST
from src.gesture_detector import GestureDetector, GestureType
from config import Settings

s = Settings()

def make_hand(scenario):
    pts = [(0.5, 0.75)] * 21
    pts[0] = (0.50, 0.90)   # WRIST
    pts[9] = (0.52, 0.72)   # MIDDLE_MCP
    hs = math.hypot(pts[9][0]-pts[0][0], pts[9][1]-pts[0][1])
    if scenario == 'point_index':
        pts[8]  = (0.50, 0.30)   # INDEX_TIP (far up)
        pts[4]  = (0.44, 0.78)   # THUMB_TIP (curled)
        pts[12] = (0.52, 0.80)   # MIDDLE_TIP (curled)
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
        pts[4]  = (0.50, 0.33)   # THUMB close to index = pinch
        pts[8]  = (0.50, 0.30)   # INDEX_TIP
        pts[12] = (0.52, 0.80)
        pts[16] = (0.54, 0.80)
        pts[20] = (0.56, 0.80)
    return HandFrame(landmarks=pts, label='Right', index_tip=pts[8],
                     thumb_tip=pts[4], middle_tip=pts[12], hand_size=hs)

# Debug: print raw values for each scenario
print("=== DEBUG ===")
for name in ['point_index', 'fist', 'pinch']:
    gd = GestureDetector(settings=s)
    h = make_hand(name)
    hs = h.hand_size
    wx, wy = h.landmarks[WRIST]
    def dw(idx):
        x, y = h.landmarks[idx]
        return math.hypot(x-wx, y-wy)
    tips = [8, 12, 16, 20]
    ratios = [dw(t)/max(hs,1e-6) for t in tips]
    pinch_ratio = h.dist(4,8) / max(hs, 1e-6)
    raw = gd._classify_raw(h)
    print(f"{name}: hand_size={hs:.3f} tip_ratios={[round(r,2) for r in ratios]} pinch_idx={pinch_ratio:.2f} raw={raw}")

print()
print("=== GESTURE TEST ===")
scenarios = {
    'point_index': GestureType.MOVE,
    'fist':        GestureType.PAUSE,
    'open_palm':   GestureType.RESUME,
    'pinch':       GestureType.LEFT_CLICK,
}
now = time.monotonic()
all_pass = True
for name, expected in scenarios.items():
    gd = GestureDetector(settings=s)
    h = make_hand(name)
    result = None
    for i in range(5):
        result = gd.recognize(h, now + i*0.033)
    ok = result == expected
    if not ok:
        all_pass = False
    status = "PASS" if ok else "FAIL"
    print(f"  {name:15s} expected={expected.value:12s} got={str(result.value):12s}  {status}")

print()
print("ALL PASS" if all_pass else "SOME FAILED - check debug above")
