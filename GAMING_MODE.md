# 🎮 Gaming Mode - IGI Optimization Guide

## AI Virtual Mouse 2.0 - Gaming Edition

This version has been optimized for FPS games like IGI (Project IGI / IGI 2: Covert Strike).

---

## ⚡ Performance Optimizations

### Applied Changes:
✅ **Lower Camera Resolution** (640x480) - Faster processing, higher FPS
✅ **Increased Sensitivity** (2.8x) - Faster cursor movement for quick aiming
✅ **Reduced Smoothing** (0.20) - More responsive, less lag
✅ **Smaller Dead Zone** (1.5px) - Precise micro-adjustments
✅ **Faster Click Cooldown** (0.25s) - Rapid fire capability
✅ **Lite Hand Tracking Model** - Reduced latency

---

## 🖐️ Gaming Gestures

### Basic Controls:
| Gesture | Action | IGI Use |
|---------|--------|---------|
| 👆 **Index finger pointing** | Move cursor | **Aim weapon** |
| 🤏 **Thumb + Index pinch** | Left click | **Fire weapon** |
| 🤌 **Thumb + Middle pinch** | Right click | **Zoom/Scope** |
| ✊ **Closed fist** | Pause | **Stop aiming** |
| 🖐️ **Open palm (5 fingers)** | Resume | **Resume control** |

### NEW Gaming Gestures:
| Gesture | Action | IGI Use |
|---------|--------|---------|
| 🤟 **3 fingers up** (Index+Middle+Ring) | 🎯 **Steady Aim Mode** | **Sniper precision** (slower, steadier cursor) |
| 🖖 **4 fingers up** (no thumb) | 🔄 **Reload** | **Reload weapon** (press R key) |
| ✌️ **2 fingers up** (Index+Middle) | Scroll | **Weapon switch** |

---

## 🎯 IGI-Specific Tips

### Before Starting:

1. **Good Lighting Required**
   - Face a window or lamp
   - Avoid shadows on your hand
   - Solid background works best

2. **Camera Position**
   - Place camera at chest level
   - 1-2 feet away from hand
   - Keep hand in frame center

3. **Calibration**
   - Run the app first
   - Go to **Calibration** page
   - Follow the 2-point calibration
   - Select a **smaller area** for faster movements

### In-Game Settings:

**IGI Game Settings:**
- Mouse sensitivity: **Medium-Low** (the app already has high sensitivity)
- Invert Y-axis: **No**
- Raw mouse input: **Off** (if available)

---

## 🎮 How to Play IGI

### Step 1: Launch Application
```bash
python main.py
```

### Step 2: Enable Mouse Control
- Click the **toggle switch** on Dashboard
- Or keep it off until you're in-game

### Step 3: Start IGI
- Launch Project IGI / IGI 2
- Load a mission

### Step 4: Gaming Controls

**Movement:** Use keyboard (WASD) as normal
**Aiming:** Point your index finger
**Shooting:** Pinch thumb + index (hold for auto-fire)
**Reload:** Show 4 fingers up briefly
**Zoom:** Thumb + middle pinch (right-click)
**Weapon Switch:** Show 2 fingers, move hand up/down

### Step 5: Emergency Stop
- Press **F10** anytime to disable mouse control
- Use this if cursor goes crazy!

---

## ⚙️ Advanced Settings

### For Better Aiming:

Go to **Settings** page and adjust:

| Setting | Recommended Value | Effect |
|---------|------------------|--------|
| Sensitivity | 2.5 - 3.5 | Higher = faster cursor |
| Smoothing | 0.15 - 0.25 | Lower = more responsive |
| Dead Zone | 1.0 - 2.0 | Lower = more precise |
| Click Cooldown | 0.20 - 0.30 | Lower = faster shots |

### Camera Settings:
- Resolution: **640x480** (fastest)
- If too laggy: Keep at 640x480 but close other apps

---

## 🎯 Gesture Practice

### Before Playing:
1. Open **Dashboard**
2. Practice gestures
3. Watch the gesture label change
4. Get comfortable with:
   - Quick pinches (shooting)
   - Steady pointing (aiming)
   - Fast pinch release (single shots)

### Recommended Practice:
- **Training Mode in IGI** - practice first
- **Slow missions** - start with stealth
- **Save often** - F5 quick save!

---

## ⚠️ Known Limitations

### Won't Work Well For:
❌ Competitive multiplayer
❌ Fast-paced action sequences  
❌ Long sniper shots (hand gets tired)
❌ Precision headshots
❌ Quick 180° turns

### Works Best For:
✅ Single-player campaigns
✅ Stealth missions
✅ Casual gameplay
✅ Practice/training
✅ Showing off to friends! 😎

---

## 🐛 Troubleshooting

### Cursor Too Fast/Slow:
- Adjust **Sensitivity** in Settings (1.5 - 4.0)
- Or adjust **IGI in-game mouse sensitivity**

### Laggy/Stuttering:
- Close other applications
- Ensure good lighting
- Keep hand steady
- Try lowering camera resolution further (but already at 640x480)

### False Clicks:
- Increase **Click Cooldown** (0.3 - 0.5s)
- Keep fingers more separated
- Don't curl fingers when just aiming

### Hand Not Detected:
- Check **lighting** (most common issue)
- Remove jewelry/rings
- Solid color shirt helps
- Try different background

### Steady Aim Not Working:
- Make sure exactly 3 fingers up (index + middle + ring)
- Keep pinky down
- Hold steady for 1 second

---

## 🎓 Pro Tips

1. **Use Keyboard for Movement**: Only use hand gesture for aiming and shooting
2. **Short Sessions**: Hand gets tired after 15-20 minutes
3. **Rest Position**: Keep hand near camera but relaxed when not aiming
4. **Quick Saves**: F5 is your friend! Save before each fight
5. **Practice Makes Perfect**: Spend 10 minutes in training first
6. **Lighting is KING**: Seriously, good lighting = 80% of success
7. **Steady Surface**: Rest your elbow on desk for stability

---

## 📊 Expected Performance

| Metric | Value |
|--------|-------|
| FPS (Frames Per Second) | 20-30 fps |
| Latency | 50-150ms |
| Hand Detection | 85-95% |
| Gesture Accuracy | 90%+ |

---

## 🎮 Alternative Gaming Uses

This setup also works well for:
- **Strategy Games** (Age of Empires, StarCraft)
- **Puzzle Games** (Portal, The Witness)
- **Adventure Games** (Tomb Raider, Uncharted)
- **Menu Navigation** in any game
- **Casual Gaming** sessions

---

## 🔧 Technical Details

### Optimizations Applied:
```python
camera_resolution = 640x480  # Was: 1280x720
sensitivity = 2.8            # Was: 1.6
smoothing_alpha = 0.20       # Was: 0.35
dead_zone_px = 1.5           # Was: 4.0
click_cooldown = 0.25s       # Was: 0.45s
model_complexity = 0         # Lite model
detection_confidence = 0.5   # Was: 0.6
```

### New Features:
- 🎯 Steady Aim mode (3 fingers)
- 🔄 Reload gesture (4 fingers)
- Faster gesture recognition
- Gaming-optimized thresholds

---

## 🚀 Future Improvements

Possible additions:
- [ ] Crouch/Prone gestures
- [ ] Quick 180° turn swipe
- [ ] Voice commands integration
- [ ] Dual-hand mode (left hand = movement)
- [ ] Custom key bindings per gesture
- [ ] Game profile presets

---

## 📝 Feedback

If you have suggestions or find bugs:
1. Test with the original settings first
2. Note your lighting conditions
3. Record a short video if possible
4. Share your experience!

---

## ⚖️ Realistic Expectations

**This is NOT a replacement for:**
- Professional gaming mouse
- Competitive play
- Tournament-level gaming

**This IS great for:**
- Casual gaming
- Experimentation
- Accessibility
- Fun demos
- Learning computer vision

---

## 🎉 Have Fun!

Remember: This is about having fun and experiencing new technology. Don't expect pro-level performance, but enjoy the unique gaming experience!

**மகிழுங்க! (Have fun!)** 🎮🖐️

---

*AI Virtual Mouse 2.0 - Gaming Edition*
*Optimized for IGI and FPS Games*
