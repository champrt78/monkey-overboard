# Monkey Overboard Sprite Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all gameplay sprites with transparent, Mulletdown-style modern-retro pixel-art sprite sheets, add a flying/tumble monkey animation, and keep the headless self-test passing.

**Architecture:** Generate frames at 4× final resolution via Gemini using the Mulletdown title plate as a style reference, downscale with nearest-neighbor to keep crisp pixels, lay out as horizontal sprite sheets, then update the existing `SpriteFrames` `.tres` resources and `main.gd` animation mapping.

**Tech Stack:** Python 3, `google-genai`, `PIL`, Godot 4.6, GDScript.

---

## File Structure

| File | Purpose |
|---|---|
| `godot/scripts/generate_sprites.py` | Generates/replaces all sprite sheet PNGs via Gemini. |
| `godot/assets/sprites/monkey_sheet.png` | 8-frame monkey sheet (idle×2, ascend×2, descend×2, tumble×2). |
| `godot/assets/sprites/gator_sheet.png` | 5-frame gator sheet (patrol×2, alert×1, chomp×2). |
| `godot/assets/sprites/banana_sheet.png` | 3-frame banana wobble sheet. |
| `godot/assets/sprites/splash_sheet.png` | 5-frame splash sheet. |
| `godot/assets/sprites/seesaw_plank.png` | Single detailed plank. |
| `godot/assets/sprites/monkey_frames.tres` | SpriteFrames for monkey. |
| `godot/assets/sprites/gator_frames.tres` | SpriteFrames for gator. |
| `godot/assets/sprites/banana_frames.tres` | SpriteFrames for banana. |
| `godot/assets/sprites/splash_frames.tres` | SpriteFrames for splash. |
| `godot/main.gd` | Maps monkey states to new animations; adds tumble flair. |

---

### Task 1: Update the sprite generation script

**Files:**
- Modify: `godot/scripts/generate_sprites.py`

- [ ] **Step 1: Replace script contents**

```python
#!/usr/bin/env python3
"""Generate Monkey Overboard sprites via Gemini in Mulletdown-style pixel art."""
import os
import sys
from pathlib import Path
from io import BytesIO
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
MODEL = "models/gemini-3-pro-image-preview"
REF_IMAGE = Path("C:/Users/Ray/Kimi-Repos/mulletdown/assets/screens/title_plate.png")


def _load_ref(path: Path):
    return types.Part.from_bytes(data=path.read_bytes(), mime_type="image/png")


def generate(name: str, prompt: str, final_wh: tuple, gen_wh: tuple):
    out = OUT_DIR / name
    print(f"Generating {name} ...")
    parts = [prompt, _load_ref(REF_IMAGE)]
    response = client.models.generate_content(model=MODEL, contents=parts)
    for part in response.candidates[0].content.parts:
        if hasattr(part, "inline_data") and part.inline_data and part.inline_data.data:
            img = Image.open(BytesIO(part.inline_data.data)).convert("RGBA")
            # Resize from generation resolution to final in-game resolution.
            if img.size != gen_wh:
                img = img.resize(gen_wh, Image.LANCZOS)
            if gen_wh != final_wh:
                img = img.resize(final_wh, Image.NEAREST)
            # Make sure pure-white backgrounds are transparent.
            datas = img.getdata()
            new_data = []
            for item in datas:
                r, g, b, a = item
                if a > 0 and r > 245 and g > 245 and b > 245:
                    new_data.append((255, 255, 255, 0))
                else:
                    new_data.append(item)
            img.putdata(new_data)
            img.save(out, "PNG")
            print(f"  Saved {out.name} at {img.size}")
            return
    print(f"  WARNING: no image returned for {name}")


# Frame sizes are kept identical to the current sheets so no scene scaling is needed.
# Each frame is generated at 4x then downscaled with nearest-neighbor.
SPRITES = [
    (
        "monkey_sheet.png",
        "Pixel art sprite sheet in the style of the reference image. A cartoon jungle monkey, "
        "8 frames in one horizontal row, final size 112x14 pixels (each frame 14x14). "
        "Transparent background, NO white mat, thick black outline, cel-shaded, warm jungle palette. "
        "Frame 0-1: idle standing. Frame 2-3: ascending with arms reaching up. "
        "Frame 4-5: descending with arms tucked. Frame 6-7: tumbling spin. "
        "Side-view 2D game sprite, modern retro pixel art.",
        (112, 14),
        (448, 56),
    ),
    (
        "gator_sheet.png",
        "Pixel art sprite sheet in the style of the reference image. A cartoon alligator, "
        "5 frames in one horizontal row, final size 160x12 pixels (each frame 32x12). "
        "Transparent background, NO white mat, thick black outline, cel-shaded, jungle green palette. "
        "Frame 0-1: patrol swimming. Frame 2: alert rearing up. Frame 3-4: chomp with jaws wide. "
        "Side-view 2D game sprite, modern retro pixel art.",
        (160, 12),
        (640, 48),
    ),
    (
        "banana_sheet.png",
        "Pixel art sprite sheet in the style of the reference image. A bright yellow banana, "
        "3 frames in one horizontal row, final size 30x10 pixels (each frame 10x10). "
        "Transparent background, NO white mat, thick black outline, slight wobble/shimmer. "
        "Side-view 2D game sprite, modern retro pixel art.",
        (30, 10),
        (120, 40),
    ),
    (
        "splash_sheet.png",
        "Pixel art sprite sheet in the style of the reference image. A water splash, "
        "5 frames in one horizontal row, final size 80x16 pixels (each frame 16x16). "
        "Transparent background, NO white mat, blue and white, impact to dissipate. "
        "Side-view 2D game sprite, modern retro pixel art.",
        (80, 16),
        (320, 64),
    ),
    (
        "seesaw_plank.png",
        "Pixel art wooden seesaw plank in the style of the reference image. "
        "Single frame, final size 44x6 pixels. "
        "Transparent background, NO white mat, brown wood grain with darker ends. "
        "Modern retro pixel art.",
        (44, 6),
        (176, 24),
    ),
]

for name, prompt, final_size, gen_size in SPRITES:
    generate(name, prompt, final_size, gen_size)

print("Done.")
```

- [ ] **Step 2: Commit the updated generator**

```bash
git add godot/scripts/generate_sprites.py
git commit -m "chore: update sprite generator for Mulletdown-style transparent sheets"
```

---

### Task 2: Generate the new sprite sheets

**Files:**
- Create: `godot/assets/sprites/monkey_sheet.png`
- Create: `godot/assets/sprites/gator_sheet.png`
- Create: `godot/assets/sprites/banana_sheet.png`
- Create: `godot/assets/sprites/splash_sheet.png`
- Create: `godot/assets/sprites/seesaw_plank.png`

- [ ] **Step 1: Run the generator**

Run:
```bash
cd /c/Users/Ray/kimi-repos/monkey-overboard/godot
python scripts/generate_sprites.py
```

Expected: five "Saved ..." lines with the sizes above.

- [ ] **Step 2: Inspect for white backgrounds**

Open each PNG in an image viewer or run:
```bash
python - <<'PY'
from PIL import Image
from pathlib import Path
p = Path("assets/sprites")
for f in ["monkey_sheet.png", "gator_sheet.png", "banana_sheet.png", "splash_sheet.png", "seesaw_plank.png"]:
    img = Image.open(p/f).convert("RGBA")
    white = sum(1 for r,g,b,a in img.getdata() if a>0 and r>245 and g>245 and b>245)
    print(f, img.size, "white-ish pixels:", white)
PY
```

Expected: each file has the correct size; white-ish pixel count should be near 0.

- [ ] **Step 3: Commit generated art**

```bash
git add godot/assets/sprites/*.png
git commit -m "feat: regenerate gameplay sprites in Mulletdown-style pixel art"
```

---

### Task 3: Update SpriteFrames resources

**Files:**
- Overwrite: `godot/assets/sprites/monkey_frames.tres`
- Overwrite: `godot/assets/sprites/gator_frames.tres`
- Overwrite: `godot/assets/sprites/banana_frames.tres`
- Overwrite: `godot/assets/sprites/splash_frames.tres`

- [ ] **Step 1: Write `monkey_frames.tres`**

```ini
[gd_resource type="SpriteFrames" load_steps=9 format=3]

[ext_resource type="Texture2D" path="res://assets/sprites/monkey_sheet.png" id="monkey_sheet"]

[sub_resource type="AtlasTexture" id="AtlasTexture_idle0"]
atlas = ExtResource("monkey_sheet")
region = Rect2(0, 0, 14, 14)

[sub_resource type="AtlasTexture" id="AtlasTexture_idle1"]
atlas = ExtResource("monkey_sheet")
region = Rect2(14, 0, 14, 14)

[sub_resource type="AtlasTexture" id="AtlasTexture_asc0"]
atlas = ExtResource("monkey_sheet")
region = Rect2(28, 0, 14, 14)

[sub_resource type="AtlasTexture" id="AtlasTexture_asc1"]
atlas = ExtResource("monkey_sheet")
region = Rect2(42, 0, 14, 14)

[sub_resource type="AtlasTexture" id="AtlasTexture_desc0"]
atlas = ExtResource("monkey_sheet")
region = Rect2(56, 0, 14, 14)

[sub_resource type="AtlasTexture" id="AtlasTexture_desc1"]
atlas = ExtResource("monkey_sheet")
region = Rect2(70, 0, 14, 14)

[sub_resource type="AtlasTexture" id="AtlasTexture_tumble0"]
atlas = ExtResource("monkey_sheet")
region = Rect2(84, 0, 14, 14)

[sub_resource type="AtlasTexture" id="AtlasTexture_tumble1"]
atlas = ExtResource("monkey_sheet")
region = Rect2(98, 0, 14, 14)

[resource]
animations = [{
"frames": [{
"duration": 1.0,
"texture": SubResource("AtlasTexture_idle0")
}, {
"duration": 1.0,
"texture": SubResource("AtlasTexture_idle1")
}],
"loop": true,
"name": &"idle",
"speed": 8.0
}, {
"frames": [{
"duration": 1.0,
"texture": SubResource("AtlasTexture_asc0")
}, {
"duration": 1.0,
"texture": SubResource("AtlasTexture_asc1")
}],
"loop": true,
"name": &"ascending",
"speed": 8.0
}, {
"frames": [{
"duration": 1.0,
"texture": SubResource("AtlasTexture_desc0")
}, {
"duration": 1.0,
"texture": SubResource("AtlasTexture_desc1")
}],
"loop": true,
"name": &"descending",
"speed": 8.0
}, {
"frames": [{
"duration": 1.0,
"texture": SubResource("AtlasTexture_tumble0")
}, {
"duration": 1.0,
"texture": SubResource("AtlasTexture_tumble1")
}],
"loop": true,
"name": &"tumble",
"speed": 12.0
}]
```

- [ ] **Step 2: Write `gator_frames.tres`**

```ini
[gd_resource type="SpriteFrames" load_steps=6 format=3]

[ext_resource type="Texture2D" path="res://assets/sprites/gator_sheet.png" id="gator_sheet"]

[sub_resource type="AtlasTexture" id="AtlasTexture_patrol0"]
atlas = ExtResource("gator_sheet")
region = Rect2(0, 0, 32, 12)

[sub_resource type="AtlasTexture" id="AtlasTexture_patrol1"]
atlas = ExtResource("gator_sheet")
region = Rect2(32, 0, 32, 12)

[sub_resource type="AtlasTexture" id="AtlasTexture_alert"]
atlas = ExtResource("gator_sheet")
region = Rect2(64, 0, 32, 12)

[sub_resource type="AtlasTexture" id="AtlasTexture_chomp0"]
atlas = ExtResource("gator_sheet")
region = Rect2(96, 0, 32, 12)

[sub_resource type="AtlasTexture" id="AtlasTexture_chomp1"]
atlas = ExtResource("gator_sheet")
region = Rect2(128, 0, 32, 12)

[resource]
animations = [{
"frames": [{
"duration": 1.0,
"texture": SubResource("AtlasTexture_patrol0")
}, {
"duration": 1.0,
"texture": SubResource("AtlasTexture_patrol1")
}],
"loop": true,
"name": &"patrol",
"speed": 6.0
}, {
"frames": [{
"duration": 1.0,
"texture": SubResource("AtlasTexture_alert")
}],
"loop": true,
"name": &"alert",
"speed": 6.0
}, {
"frames": [{
"duration": 1.0,
"texture": SubResource("AtlasTexture_chomp0")
}, {
"duration": 1.0,
"texture": SubResource("AtlasTexture_chomp1")
}],
"loop": true,
"name": &"chomp",
"speed": 10.0
}]
```

- [ ] **Step 3: Write `banana_frames.tres`**

```ini
[gd_resource type="SpriteFrames" load_steps=4 format=3]

[ext_resource type="Texture2D" path="res://assets/sprites/banana_sheet.png" id="banana_sheet"]

[sub_resource type="AtlasTexture" id="AtlasTexture_b0"]
atlas = ExtResource("banana_sheet")
region = Rect2(0, 0, 10, 10)

[sub_resource type="AtlasTexture" id="AtlasTexture_b1"]
atlas = ExtResource("banana_sheet")
region = Rect2(10, 0, 10, 10)

[sub_resource type="AtlasTexture" id="AtlasTexture_b2"]
atlas = ExtResource("banana_sheet")
region = Rect2(20, 0, 10, 10)

[resource]
animations = [{
"frames": [{
"duration": 1.0,
"texture": SubResource("AtlasTexture_b0")
}, {
"duration": 1.0,
"texture": SubResource("AtlasTexture_b1")
}, {
"duration": 1.0,
"texture": SubResource("AtlasTexture_b2")
}],
"loop": true,
"name": &"default",
"speed": 6.0
}]
```

- [ ] **Step 4: Write `splash_frames.tres`**

```ini
[gd_resource type="SpriteFrames" load_steps=6 format=3]

[ext_resource type="Texture2D" path="res://assets/sprites/splash_sheet.png" id="splash_sheet"]

[sub_resource type="AtlasTexture" id="AtlasTexture_s0"]
atlas = ExtResource("splash_sheet")
region = Rect2(0, 0, 16, 16)

[sub_resource type="AtlasTexture" id="AtlasTexture_s1"]
atlas = ExtResource("splash_sheet")
region = Rect2(16, 0, 16, 16)

[sub_resource type="AtlasTexture" id="AtlasTexture_s2"]
atlas = ExtResource("splash_sheet")
region = Rect2(32, 0, 16, 16)

[sub_resource type="AtlasTexture" id="AtlasTexture_s3"]
atlas = ExtResource("splash_sheet")
region = Rect2(48, 0, 16, 16)

[sub_resource type="AtlasTexture" id="AtlasTexture_s4"]
atlas = ExtResource("splash_sheet")
region = Rect2(64, 0, 16, 16)

[resource]
animations = [{
"frames": [{
"duration": 1.0,
"texture": SubResource("AtlasTexture_s0")
}, {
"duration": 1.0,
"texture": SubResource("AtlasTexture_s1")
}, {
"duration": 1.0,
"texture": SubResource("AtlasTexture_s2")
}, {
"duration": 1.0,
"texture": SubResource("AtlasTexture_s3")
}, {
"duration": 1.0,
"texture": SubResource("AtlasTexture_s4")
}],
"loop": false,
"name": &"default",
"speed": 12.0
}]
```

- [ ] **Step 5: Commit SpriteFrames**

```bash
git add godot/assets/sprites/*.tres
git commit -m "feat: update SpriteFrames for new Mulletdown-style sheets"
```

---

### Task 4: Update monkey animation mapping in main.gd

**Files:**
- Modify: `godot/main.gd`

- [ ] **Step 1: Add a tumble timer/state variable**

Near the top state block (after `var _selftest_catches := 0`), add:

```gdscript
var _tumble_timer := 0.0
```

- [ ] **Step 2: Update _update_monkey_sprites to use ascending/descending/tumble**

Replace the body of `_update_monkey_sprites()` with:

```gdscript
func _update_monkey_sprites() -> void:
    for i in range(2):
        var m: Dictionary = monkeys[i]
        var spr: AnimatedSprite2D = _mono[i]
        spr.position = Vector2(m.x, m.y - _cam_y)
        match m.state:
            "ground":
                spr.play("idle")
            "air":
                if _tumble_timer > 0.0:
                    spr.play("tumble")
                elif m.vy < 0.0:
                    spr.play("ascending")
                else:
                    spr.play("descending")
        spr.flip_h = (m.vx < 0.0)
```

- [ ] **Step 3: Trigger tumble on catches**

In `_do_catch`, after `seesaw.up_side *= -1`, add:

```gdscript
    _tumble_timer = 0.25
```

- [ ] **Step 4: Decay tumble timer**

In `_process(delta)`, after `time += delta`, add:

```gdscript
    if _tumble_timer > 0.0:
        _tumble_timer = max(0.0, _tumble_timer - delta)
```

- [ ] **Step 5: Commit code change**

```bash
git add godot/main.gd
git commit -m "feat: add monkey tumble animation and map ascend/descend states"
```

---

### Task 5: Re-import assets in Godot

**Files:**
- Modify: `.godot/imported/*` (auto-generated)

- [ ] **Step 1: Run headless editor import**

```bash
cd /c/Users/Ray/kimi-repos/monkey-overboard/godot
"C:/Users/Ray/Desktop/Godot_v4.6-stable_win64_console.exe" --headless --editor --quit
```

Expected: completes without errors; `.godot/imported/` and `.import` files refresh.

- [ ] **Step 2: Commit import cache**

```bash
git add .godot godot/assets/sprites/*.png.import godot/assets/sprites/*.tres
git commit -m "chore: reimport sprite assets"
```

---

### Task 6: Verify with headless self-test

**Files:**
- None (read-only test)

- [ ] **Step 1: Run self-test**

```bash
cd /c/Users/Ray/kimi-repos/monkey-overboard
powershell -ExecutionPolicy Bypass -File run_selftest.ps1
```

Expected stdout contains: `SELFTEST catches=... phase=playing`.

- [ ] **Step 2: If self-test fails, fix and re-run**

Common issues:
- Missing animation name → add it to the SpriteFrames resource.
- Sprite sheet size mismatch → regenerate or fix `.tres` regions.

---

### Task 7: Windowed visual check

**Files:**
- None (read-only test)

- [ ] **Step 1: Run windowed with self-test**

```bash
cd /c/Users/Ray/kimi-repos/monkey-overboard/godot
"C:/Users/Ray/Desktop/Godot_v4.6-stable_win64_console.exe" --mo-selftest
```

- [ ] **Step 2: Visually confirm**

- Monkeys show no white boxes.
- Monkey changes pose when ascending vs descending.
- Tumble flash plays on catch.
- Gator, banana, splash, seesaw all render crisply.

- [ ] **Step 3: Final commit if visual check passes**

```bash
git commit -m "feat: Mulletdown-style sprite overhaul complete"
```

---

## Self-Review Checklist

- [ ] Spec coverage: every sprite from the spec has a generation task.
- [ ] No placeholders: all prompts, file paths, commands, and code blocks are concrete.
- [ ] Type consistency: animation names match between `.tres` files and `main.gd`.
- [ ] Integration verified: headless self-test and windowed run steps included.
