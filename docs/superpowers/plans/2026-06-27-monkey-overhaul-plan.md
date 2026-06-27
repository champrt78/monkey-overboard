# Monkey / Camera / Banana Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Overhaul monkey sprites, add smart camera framing for the catch, improve seesaw control, and fill the tree with banana bunches.

**Architecture:** Generate eight individual monkey frames on a white background, pack them into the existing 224×28 sheet, then update `main.gd` for camera blending, keyboard/touch control feedback, and branch-based banana bunch generation. Verify with the headless self-test and rebuild the debug APK.

**Tech Stack:** Godot 4.6, Python 3 + Pillow, Gemini image generation.

---

## File Map

| File | Responsibility |
|------|----------------|
| `godot/scripts/generate_monkey_frames.py` | New script: generates 8 individual monkey frames via Gemini and packs them into `monkey_sheet.png`. |
| `godot/main.gd` | Existing game loop. Modify camera (`_update_camera`), input (`_input`, `_draw`), and banana generation (`_generate_bananas`). |
| `godot/assets/sprites/monkey_sheet.png` | Output from the generator. |
| `godot/assets/sprites/monkey_frames.tres` | Existing SpriteFrames; no changes needed because frame size stays 28×28. |
| `docs/sessions/Session_2026-06-26.md` | Append notes about this overhaul. |

---

### Task 1: Create the monkey frame generator

**Files:**
- Create: `godot/scripts/generate_monkey_frames.py`
- Output: `godot/assets/sprites/monkey_sheet.png`

- [ ] **Step 1: Write the generator script**

```python
#!/usr/bin/env python3
"""Generate Monkey Overboard monkey frames individually and pack them into a sheet."""
import os
import sys
from pathlib import Path
from io import BytesIO
import numpy as np
import scipy.ndimage as ndi
from google import genai
from google.genai import types
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "assets" / "sprites"
OUT_DIR.mkdir(parents=True, exist_ok=True)

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    sys.exit("ERROR: GEMINI_API_KEY not set")
client = genai.Client(api_key=api_key)
MODEL = "models/gemini-3.1-flash-image"
MULLET_REF = Path("C:/Users/Ray/Kimi-Repos/mulletdown/docs/mockups/screens/title_plate.png")
JUNGLE_REF = Path("C:/Users/Ray/kimi-repos/monkey-overboard/godot/assets/backgrounds/jungle_bg.png")

FRAME_W, FRAME_H = 28, 28
FINAL_SHEET = (FRAME_W * 8, FRAME_H)


def _load_ref(path: Path):
    return types.Part.from_bytes(data=path.read_bytes(), mime_type="image/png")


def _remove_bg(img: Image.Image) -> Image.Image:
    arr = np.array(img.convert("RGBA"))
    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3]
    maxc = rgb.max(axis=2)
    minc = rgb.min(axis=2)
    desat = maxc - minc
    bg = (desat < 40) | (maxc > 245)
    labels, _ = ndi.label(bg)
    border = np.concatenate([labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]])
    border_labels = set(np.unique(border)) - {0}
    if border_labels:
        remove_mask = np.isin(labels, list(border_labels))
        alpha[remove_mask] = 0
    return Image.fromarray(arr, "RGBA")


def _generate_one(prompt: str, out: Path, gen_wh: tuple):
    print(f"Generating {out.name} ...")
    parts = [prompt, _load_ref(MULLET_REF), _load_ref(JUNGLE_REF)]
    response = client.models.generate_content(model=MODEL, contents=parts)
    for part in response.candidates[0].content.parts:
        if hasattr(part, "inline_data") and part.inline_data and part.inline_data.data:
            img = Image.open(BytesIO(part.inline_data.data)).convert("RGBA")
            if img.size != gen_wh:
                img = img.resize(gen_wh, Image.LANCZOS)
            img = img.resize((FRAME_W, FRAME_H), Image.NEAREST)
            img = _remove_bg(img)
            img.save(out, "PNG")
            print(f"  Saved {out.name} at {img.size}")
            return
    print(f"  WARNING: no image returned for {out.name}")


FRAME_PROMPTS = [
    ("idle_0.png", "Modern-retro pixel-art jungle monkey, standing idle, slight breathing pose, side view facing right. Thick black outline, cel-shaded brown/tan fur, expressive face. PURE SOLID WHITE BACKGROUND #FFFFFF. Final size 28x28 pixels."),
    ("idle_1.png", "Modern-retro pixel-art jungle monkey, standing idle with a tiny upward lean, side view facing right. Thick black outline, cel-shaded brown/tan fur. PURE SOLID WHITE BACKGROUND #FFFFFF. Final size 28x28 pixels."),
    ("ascend_0.png", "Modern-retro pixel-art jungle monkey, ascending with arms reaching up, side view facing right. Thick black outline, cel-shaded brown/tan fur. PURE SOLID WHITE BACKGROUND #FFFFFF. Final size 28x28 pixels."),
    ("ascend_1.png", "Modern-retro pixel-art jungle monkey, ascending higher with arms stretched, side view facing right. Thick black outline, cel-shaded brown/tan fur. PURE SOLID WHITE BACKGROUND #FFFFFF. Final size 28x28 pixels."),
    ("descend_0.png", "Modern-retro pixel-art jungle monkey, descending with arms tucked, side view facing right. Thick black outline, cel-shaded brown/tan fur. PURE SOLID WHITE BACKGROUND #FFFFFF. Final size 28x28 pixels."),
    ("descend_1.png", "Modern-retro pixel-art jungle monkey, descending with arms and legs tucked, side view facing right. Thick black outline, cel-shaded brown/tan fur. PURE SOLID WHITE BACKGROUND #FFFFFF. Final size 28x28 pixels."),
    ("tumble_0.png", "Modern-retro pixel-art jungle monkey, tumbling/spinning in mid-air, side view facing right. Thick black outline, cel-shaded brown/tan fur. PURE SOLID WHITE BACKGROUND #FFFFFF. Final size 28x28 pixels."),
    ("tumble_1.png", "Modern-retro pixel-art jungle monkey, tumbling/spinning further, side view facing right. Thick black outline, cel-shaded brown/tan fur. PURE SOLID WHITE BACKGROUND #FFFFFF. Final size 28x28 pixels."),
]


def main():
    tmp_dir = OUT_DIR / "_monkey_tmp"
    tmp_dir.mkdir(exist_ok=True)
    frames = []
    gen_wh = (FRAME_W * 4, FRAME_H * 4)
    for name, prompt in FRAME_PROMPTS:
        out = tmp_dir / name
        _generate_one(prompt, out, gen_wh)
        frames.append(out)

    # Pack into sheet
    sheet = Image.new("RGBA", FINAL_SHEET, (255, 255, 255, 0))
    for i, path in enumerate(frames):
        frm = Image.open(path).convert("RGBA")
        sheet.paste(frm, (i * FRAME_W, 0), frm)
    sheet.save(OUT_DIR / "monkey_sheet.png", "PNG")
    print("Packed monkey_sheet.png")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the generator**

Run:
```bash
cd C:/Users/Ray/kimi-repos/monkey-overboard
python godot/scripts/generate_monkey_frames.py
```

Expected: 8 frames generated and packed into `godot/assets/sprites/monkey_sheet.png` at 224×28.

- [ ] **Step 3: Verify transparency**

Run:
```python
from PIL import Image
img = Image.open("godot/assets/sprites/monkey_sheet.png")
print(img.size, img.mode, img.getpixel((0, 0)))
```

Expected: `(224, 28) RGBA (255, 255, 255, 0)`.

- [ ] **Step 4: Commit**

```bash
git add godot/scripts/generate_monkey_frames.py godot/assets/sprites/monkey_sheet.png
git commit -m "feat(art): regenerate monkey frames individually on white bg"
```

---

### Task 2: Smart camera framing

**Files:**
- Modify: `godot/main.gd` — replace `_update_camera()`

- [ ] **Step 1: Update `_update_camera()`**

```gdscript
const CAMERA_CATCH_BLEND_WINDOW := 180.0  # world units above seesaw where framing starts

func _update_camera() -> void:
    var target_y := WORLD_H - VIEW_H
    if phase == "playing" or phase == "gameover":
        var air: Dictionary = monkeys[air_index]
        var follow_target := clamp(air.y - VIEW_H * 0.45, 0.0, WORLD_H - VIEW_H)
        target_y = follow_target

        if air.state == "air" and air.vy > 0.0:
            var dist_to_seesaw := SEESAW_Y - air.y
            var t := clamp(1.0 - dist_to_seesaw / CAMERA_CATCH_BLEND_WINDOW, 0.0, 1.0)
            var catch_target := (SEESAW_Y + air.y) * 0.5 - VIEW_H * 0.5
            catch_target = clamp(catch_target, 0.0, WORLD_H - VIEW_H)
            target_y = lerp(follow_target, catch_target, t * t)

    _cam_y = lerp(_cam_y, target_y, 0.15)
    _jungle_bg.position = Vector2(0, -_cam_y)
```

- [ ] **Step 2: Verify the change compiles**

Run Godot import:
```bash
"C:/Users/Ray/Desktop/Godot_v4.6-stable_win64.exe" --path "C:/Users/Ray/kimi-repos/monkey-overboard/godot" --headless --import
```

Expected: import finishes with no errors.

- [ ] **Step 3: Commit**

```bash
git add godot/main.gd
git commit -m "feat(camera): blend to catch framing during descents"
```

---

### Task 3: Seesaw control improvements

**Files:**
- Modify: `godot/main.gd` — `_input()`, `_draw()`, add helper `_draw_drag_zone()`

- [ ] **Step 1: Add keyboard control**

Replace the existing `_input()` function with:

```gdscript
func _input(event: InputEvent) -> void:
    if event is InputEventScreenTouch:
        if event.pressed:
            _on_tap()
            _on_drag(event.position.x)
    elif event is InputEventScreenDrag:
        _on_drag(event.position.x)
    elif event is InputEventMouseButton:
        if event.pressed:
            _on_tap()
            _on_drag(event.position.x)
    elif event is InputEventMouseMotion:
        if event.button_mask & MOUSE_BUTTON_MASK_LEFT:
            _on_drag(event.position.x)

    # Keyboard fallback for desktop testing
    if event is InputEventKey and event.pressed:
        var move := 0.0
        if event.keycode == KEY_LEFT or event.keycode == KEY_A:
            move = -1.0
        elif event.keycode == KEY_RIGHT or event.keycode == KEY_D:
            move = 1.0
        if move != 0.0 and phase == "playing":
            var speed := 110.0 * get_physics_process_delta_time()
            seesaw.target_x = clamp(seesaw.target_x + move * speed,
                MONKEY_R, WORLD_W - MONKEY_R)
```

- [ ] **Step 2: Add a subtle drag-zone hint**

Add a new draw helper:

```gdscript
func _draw_drag_zone() -> void:
    if phase != "playing":
        return
    var bar_h := 12.0
    var y0 := VIEW_H - bar_h
    draw_rect(Rect2(Vector2(0, y0), Vector2(VIEW_W, bar_h)), Color(1, 1, 1, 0.08))
    draw_string(_font, Vector2(0, y0 + 9), "DRAG", HORIZONTAL_ALIGNMENT_CENTER, VIEW_W, 6, Color(1, 1, 1, 0.25))
```

Call it from `_draw()`:

```gdscript
func _draw() -> void:
    if phase == "playing":
        _draw_seesaw_base()
    _draw_hud()
    if phase == "playing":
        _draw_catch_guide()
        _draw_offscreen_indicator()
        _draw_drag_zone()
```

- [ ] **Step 3: Verify input works**

Run the game windowed:
```bash
"C:/Users/Ray/Desktop/Godot_v4.6-stable_win64.exe" --path "C:/Users/Ray/kimi-repos/monkey-overboard/godot" res://main.tscn
```

Expected: left/right arrows and A/D move the seesaw; a faint "DRAG" bar appears at the bottom during play.

- [ ] **Step 4: Commit**

```bash
git add godot/main.gd
git commit -m "feat(input): keyboard seesaw control + drag zone hint"
```

---

### Task 4: Banana bunches in the tree

**Files:**
- Modify: `godot/main.gd` — constants and `_generate_bananas()`

- [ ] **Step 1: Update banana constants**

Change:
```gdscript
const BANANA_BASE := 24
const BANANA_PER_LEVEL := 6
const BANANA_Y_MIN := 60.0
const BANANA_Y_MAX := 620.0
```

- [ ] **Step 2: Replace `_generate_bananas()`**

```gdscript
func _generate_bananas() -> void:
    for child in _banana_pool.get_children():
        child.queue_free()
    bananas = []
    var count := BANANA_BASE + BANANA_PER_LEVEL * (level - 1)

    var bunch_count := max(4, count / 4)
    var row_step := (BANANA_Y_MAX - BANANA_Y_MIN) / bunch_count
    var margin := 14.0

    for i in bunch_count:
        var row_y := BANANA_Y_MIN + i * row_step + randf() * row_step * 0.5
        var side := 1 if randf() > 0.5 else -1
        var branch_x := WORLD_W * 0.5 + side * (18.0 + randf() * 22.0)
        var bunch_size := 3 + (randi() % 3)  # 3-5 bananas per bunch
        for j in bunch_size:
            var b := {
                "x": clamp(branch_x + (j - bunch_size * 0.5) * 5.0 + randf_range(-2.0, 2.0), margin, WORLD_W - margin),
                "y": row_y + randf_range(-3.0, 3.0),
                "wobble": randf() * TAU,
            }
            var spr := AnimatedSprite2D.new()
            spr.sprite_frames = BANANA_FRAMES
            spr.play("default")
            spr.position = Vector2(b.x, b.y - _cam_y)
            spr.scale = Vector2(0.5, 0.5)
            b["spr"] = spr
            _banana_pool.add_child(spr)
            bananas.append(b)

    # Fill remaining count with scattered trunk bananas
    while bananas.size() < count:
        var b := {
            "x": clamp(WORLD_W * 0.5 + randf_range(-8.0, 8.0), margin, WORLD_W - margin),
            "y": BANANA_Y_MIN + randf() * (BANANA_Y_MAX - BANANA_Y_MIN),
            "wobble": randf() * TAU,
        }
        var spr := AnimatedSprite2D.new()
        spr.sprite_frames = BANANA_FRAMES
        spr.play("default")
        spr.position = Vector2(b.x, b.y - _cam_y)
        spr.scale = Vector2(0.5, 0.5)
        b["spr"] = spr
        _banana_pool.add_child(spr)
        bananas.append(b)
```

- [ ] **Step 3: Run selftest**

```bash
"C:/Users/Ray/Desktop/Godot_v4.6-stable_win64.exe" --path "C:/Users/Ray/kimi-repos/monkey-overboard/godot" --headless -- --mo-selftest
```

Expected:
```text
SELFTEST catches=4 score=... lives=3 level=1 phase=playing bananas_left=...
```

- [ ] **Step 4: Commit**

```bash
git add godot/main.gd
git commit -m "feat(bananas): bunches on branches + increased count"
```

---

### Task 5: Final verification and APK rebuild

**Files:**
- Modify: `docs/sessions/Session_2026-06-26.md` (append notes)
- Output: `builds/monkey-overboard-debug.apk`

- [ ] **Step 1: Run full import + selftest**

```bash
"C:/Users/Ray/Desktop/Godot_v4.6-stable_win64.exe" --path "C:/Users/Ray/kimi-repos/monkey-overboard/godot" --headless --import
"C:/Users/Ray/Desktop/Godot_v4.6-stable_win64.exe" --path "C:/Users/Ray/kimi-repos/monkey-overboard/godot" --headless -- --mo-selftest
```

Expected selftest output: `catches > 0`, `phase = playing`.

- [ ] **Step 2: Rebuild debug APK**

```bash
"C:/Users/Ray/Desktop/Godot_v4.6-stable_win64.exe" --path "C:/Users/Ray/kimi-repos/monkey-overboard/godot" --headless --export-debug "Android" "C:/Users/Ray/kimi-repos/monkey-overboard/builds/monkey-overboard-debug.apk"
```

Expected: signed APK at `builds/monkey-overboard-debug.apk`.

- [ ] **Step 3: Update session notes**

Append to `docs/sessions/Session_2026-06-26.md`:

```markdown
## Follow-up: Monkey / Camera / Banana Overhaul
- Regenerated monkey sprites as 8 individual white-bg frames and packed into the sheet.
- Added smart camera blend so the seesaw is visible during descents.
- Added keyboard control (arrows/A-D) and a faint drag-zone hint.
- Converted banana generation to branch bunches and increased total count.
- Rebuilt debug APK; selftest still passes.
```

- [ ] **Step 4: Commit docs and final state**

```bash
git add docs/sessions/Session_2026-06-26.md
git commit -m "docs(session): note monkey/camera/banana overhaul"
```

---

## Spec Coverage Check

| Spec Requirement | Task |
|------------------|------|
| Monkey overhaul with modern-retro style, 8 frames | Task 1 |
| Individual-frame generation for easy hand cleanup | Task 1 |
| Smart camera framing during descents | Task 2 |
| Keyboard seesaw control + drag hint | Task 3 |
| Banana bunches on branches, increased count | Task 4 |
| Selftest still passes | Task 5 |

## Placeholder Scan

No TBD/TODO/"fill in" strings. Every step includes exact file paths, code, and commands.

## Type Consistency Check

- `_cam_y` remains `float`; `lerp` uses GDScript `float`.
- `seesaw.target_x` is `float`; keyboard clamp uses `MONKEY_R`/`WORLD_W - MONKEY_R`.
- `BANANA_BASE`/`BANANA_PER_LEVEL` are `int`; `count` is `int`.
- Banana dictionaries use same keys as before (`x`, `y`, `wobble`, `spr`).
