# Monkey Overboard — Overnight Polish + QA Sprint

## What This Game Is

Monkey Overboard is a portrait-mode arcade score-chaser inspired by Bally/Midway's *Clowns* (1978).
Two monkeys take turns launching up a tall jungle tree. The player slides a see-saw left/right to
catch the falling monkey on the raised end — each catch fires the OTHER monkey upward. Grab bananas
on the way up for points. Miss the catch and the monkey splashes in the river where a gator is waiting.

**Three lives. Clear the banana tree to advance a level. Gator gets faster and more aggressive.**

## Repo + Project Structure

```
C:\Users\Ray\Kimi-Repos\monkey-overboard\
├── godot/                   ← THE GODOT PROJECT (open this in Godot 4.6)
│   ├── project.godot        ← 135×240 low-res viewport, nearest filtering
│   ├── main.gd              ← ENTIRE game in one file (game loop, physics, drawing, state)
│   ├── overlay.gd           ← HUD/menu/gameover text overlay
│   ├── main.tscn
│   ├── assets/
│   │   ├── sprites/         ← monkey, gator, banana, splash sheets + seesaw plank
│   │   ├── backgrounds/     ← jungle_bg.png (tall strip, scrolls with camera)
│   │   ├── screens/         ← title_plate.png, gameover_plate.png
│   │   ├── fonts/           ← PressStart2P-Regular.ttf
│   │   └── audio/           ← SFX (launch, catch, banana, splash, chomp, life_lost)
│   └── scripts/
│       ├── generate_sprites.py     ← Gemini sprite generator
│       ├── generate_title_art.py   ← title/gameover plate generator
│       └── generate_jungle_bg.py   ← background generator
└── docs/                    ← this file lives here
```

## Godot Binary + Commands

```
Godot:     C:\Users\Ray\Desktop\Godot_v4.6-stable_win64.exe
Import:    <godot> --path "C:\Users\Ray\Kimi-Repos\monkey-overboard\godot" --headless --import
Selftest:  <godot> --path "C:\Users\Ray\Kimi-Repos\monkey-overboard\godot" --headless -- --mo-selftest
```

The selftest autopilots the see-saw for 1200 frames and prints:
`SELFTEST catches=N score=N lives=N level=N phase=playing bananas_left=N`
A successful run should show `catches > 0` and `phase=playing`. If `phase=gameover` the physics is broken.

**There is NO GUT test suite** — the selftest is the only automated check. Run it after every task.

## Current State (as of this brief)

- Core loop: works. Monkey launches, catches, gator chomps on miss.
- All 5 sprite sheets are **modified but uncommitted** (`git status` will show them as ` M`).
- Sprite generator uses model name `models/gemini-3-pro-image-preview` — this is **wrong/expired**.
  Working model: `models/gemini-3.1-flash-image` (same as Mulletdown).
- Title plate: "MONKEY OVERBOARD" logo over jungle — looks good.
- Game-over plate: dark jungle with "GAME OVER" — needs the score + best baked in the empty zone.
- Active gator (v1.1): **not yet implemented** — gator currently just dash-chomps passively.
- No high score leaderboard screen — just `BEST X` in the HUD.

---

## Task 1 — Regenerate Sprite Sheets with Transparent Backgrounds

The current sprite sheets in `godot/assets/sprites/` have broken backgrounds (Gemini baked in a
gray or checkerboard pattern). All 5 need to be regenerated with proper transparent backgrounds.

**The problem with the old `generate_sprites.py`:**
Gemini returns images with gray or checkerboard backgrounds baked into RGB pixels. The old
`_remove_bg` / `_flatten_to_white` helpers don't reliably fix this. You need a border-flood
approach using scipy to detect and remove the background.

**Fix `godot/scripts/generate_sprites.py`:**

1. The model name is already correct: `MODEL = "models/gemini-3.1-flash-image"` ✓

2. Replace the background-removal helper with a scipy border-flood that works on ANY background color:

```python
import numpy as np
import scipy.ndimage as ndi

def _remove_bg(img: Image.Image) -> Image.Image:
    """Remove border-connected background using scipy flood-fill. Works on any bg color."""
    arr = np.array(img.convert("RGB"))
    # A pixel is a background candidate if it's desaturated (close to gray or white).
    # Saturation = max(RGB) - min(RGB). Low saturation = gray/white = likely background.
    r, g, b = arr[:,:,0].astype(int), arr[:,:,1].astype(int), arr[:,:,2].astype(int)
    saturation = np.maximum(np.maximum(r, g), b) - np.minimum(np.minimum(r, g), b)
    bg_candidate = saturation < 40   # desaturated = gray/white/checkerboard
    # Also include very bright pixels (near-white, even if slightly tinted)
    bg_candidate |= arr.min(axis=2) > 200
    # Label connected components and keep only those touching the border
    labels, _ = ndi.label(bg_candidate)
    border = np.concatenate([labels[0,:], labels[-1,:], labels[:,0], labels[:,-1]])
    bg_labels = set(np.unique(border)) - {0}
    bg_mask = np.isin(labels, list(bg_labels)) if bg_labels else np.zeros(arr.shape[:2], bool)
    # Build RGBA output: background = transparent, art = opaque
    rgba = np.concatenate([arr, np.full(arr.shape[:2] + (1,), 255, dtype=np.uint8)], axis=2)
    rgba[bg_mask, 3] = 0
    return Image.fromarray(rgba, "RGBA")
```

3. In the `generate()` function, make sure it calls `_remove_bg` and saves as PNG:
```python
img = Image.open(BytesIO(part.inline_data.data)).convert("RGBA")
if img.size != gen_wh:
    img = img.resize(gen_wh, Image.LANCZOS)
if gen_wh != final_wh:
    img = img.resize(final_wh, Image.NEAREST)
img = _remove_bg(img)
img.save(out, "PNG")
```

4. Run: `python godot/scripts/generate_sprites.py` (needs `GEMINI_API_KEY` env var)

5. Verify transparency: open each sheet — the background should show as checkerboard in your
   image viewer (checkerboard = transparent = correct). The sprite art should be fully visible.

6. Also verify with Python:
```python
from PIL import Image
import numpy as np
img = Image.open("assets/sprites/banana_sheet.png")
arr = np.array(img)
print(f"mode={img.mode}, transparent_corners={arr[0,0,3]==0}")
# Should print: mode=RGBA, transparent_corners=True
```

**Commit after all 5 look good:**
```
git add godot/assets/sprites/ godot/scripts/generate_sprites.py
git commit -m "feat(sprites): regenerated sheets with transparent backgrounds"
```

Then run the selftest to confirm physics still works.

---

## Task 2 — Self-Test Verification + Visual QA

Run the selftest:
```
<godot> --path "C:\Users\Ray\Kimi-Repos\monkey-overboard\godot" --headless -- --mo-selftest
```

Expected output: `catches > 10`, `score > 0`, `phase=playing`.
If selftest fails (exits before 1200 frames, or `phase=gameover` with `catches=0`), the core
catch/flip physics is broken — investigate `step()` in main.gd before doing anything else.

Also run the selftest with more frames if you want confidence: look at the frame count constant
(`_selftest_frames >= 1200` in main.gd) — you can temporarily bump it to 3600 for a deeper run.

---

## Task 3 — Active Gator (v1.1)

**Goal:** The gator currently only reacts after a miss (dash-to-chomp). v1.1 adds a live threat:
the gator lurks, telegraphs, and lunges at the monkey during gameplay — not just on misses.

**Design spec from README:**
- `lurk` — slow patrol (current behavior)
- `telegraph` — gator rises up, pauses, facing the falling monkey (visual warning, ~0.4s)
- `lunge` — fast dash toward the monkey's X position
- `retreat` — slow retreat back to center after lunge

**Trigger condition:** When the airborne monkey is within 30 world-units of the water (`air.y > WATER_Y - 30`)
AND moving downward (`air.vy > 0`), the gator transitions: `lurk → telegraph`.

**Implementation in main.gd — update `_update_gator(dt)`:**

Add new gator modes. The gator dict already has: `x`, `dir`, `mode`, `target_x`, `chomp_timer`.
Add: `lunge_timer`, `telegraph_timer`.

```gdscript
const GATOR_LUNGE_SPEED := 280.0
const GATOR_TELEGRAPH_TIME := 0.4
const GATOR_LUNGE_TIME := 0.5
const GATOR_RETREAT_SPEED := 20.0
const GATOR_LUNGE_TRIGGER_Y := 30.0  # world units above water

func _make_gator() -> Dictionary:
    return {"x": WORLD_W / 2.0, "dir": 1, "mode": "patrol",
            "target_x": WORLD_W / 2.0, "chomp_timer": 0.0,
            "telegraph_timer": 0.0, "lunge_timer": 0.0}
```

In `_update_gator(dt)`, add cases for `"telegraph"`, `"lunge"`, `"retreat"`.

In `_physics_process`, after the `step()` call, check if the gator should telegraph:
```gdscript
var air: Dictionary = monkeys[air_index]
if gator.mode == "patrol" and air.vy > 0.0 and air.y > WATER_Y - GATOR_LUNGE_TRIGGER_Y:
    gator.mode = "telegraph"
    gator.telegraph_timer = GATOR_TELEGRAPH_TIME
    gator.target_x = clamp(air.x, 15.0, WORLD_W - 15.0)
```

**Update `_update_gator_sprite()`** to add `"telegraph"` and `"lunge"` animation states.
Use the existing `"alert"` frame for telegraph, `"chomp"` for lunge.

**Important:** The lunge should NOT kill the monkey directly — only a MISS (monkey hits water)
triggers `_lose_life()`. The lunge is a visual threat/scare. The miss detection is already handled
in `step()` → `"miss"` → `_lose_life()`. The gator is purely visual threat.

**Selftest after:** Must still pass with `catches > 10`. The active gator shouldn't affect the
autopilot (it can't actually intercept the monkey before it hits water in the autopilot).

---

## Task 4 — Title Screen: Show Best Score

**Goal:** The title plate (`title_plate.png`) is shown during `phase == "menu"`. The overlay text
shows "MONKEY OVERBOARD" and "Tap to start". Add the best score to the title overlay.

**In `overlay.gd` → `_draw_overlay_on()`**, in the `phase == "menu"` branch:
After the "Tap to start" line, add:
```gdscript
if best > 0:
    c.draw_string(_font, Vector2(0, VIEW_H * 0.80), "BEST  " + str(best),
                  HORIZONTAL_ALIGNMENT_CENTER, VIEW_W, 8, Color("#ffd23c"))
```

But `best` is a variable on `main.gd`, not accessible from `overlay.gd`. Check how overlay.gd
currently gets state from main.gd (it likely calls `get_parent()` or has a reference). Follow
the same pattern.

---

## Task 5 — Game-Over Screen Polish

**Goal:** The gameover plate has a black empty zone at the bottom for stats. Currently the overlay
draws score + best in the center over the plate. Move these stats down into the empty zone.

In `overlay.gd` → `_draw_overlay_on()`, in the `phase == "gameover"` branch, adjust Y positions:
- "GAME OVER" → top zone (keep current position or slightly higher)
- `Score N` and `Best N` → position them in the dark bottom zone (y ≈ VIEW_H * 0.72 and 0.80)
- "Tap to play again" → bottom of dark zone (y ≈ VIEW_H * 0.90)

Also consider formatting the score with commas for large values (no shared NumFormat here — just
a simple GDScript helper function `_commas(n: int) -> String`).

---

## Task 6 — Difficulty Tuning Pass

**Goal:** Check that level progression feels good. These are the key dials in `main.gd`:

```gdscript
const GRAV := 225.0            # gravity (px/s²)
const LAUNCH_VY := -525.0      # launch speed
const DRIFT_BASE := 24.0       # horizontal drift at level 1
const DRIFT_PER_LEVEL := 4.5   # drift added per level
const DRIFT_MAX := 57.0        # max drift cap
const CATCH_RX_BASE := 14.0    # catch window at level 1 (px)
const CATCH_RX_MIN := 8.5      # catch window floor
const BANANA_BASE := 12        # bananas at level 1
const BANANA_PER_LEVEL := 3    # bananas added per level
```

Run the selftest at level 1, then manually check: does drift progression make sense? At level 1
the monkey drifts ~24px left or right (out of 135px total width = ~18% drift). Level 5 = 42px.
Level 8 hits the 57px cap. This seems reasonable.

Catch window shrinks from 14px → 8.5px over levels. With monkey radius 5.5px, total catch window
is about 3× the monkey radius at level 1, shrinking to 1.5×. Reasonable.

**If selftest at high level fails** (set `level = 5` before `start_game()` in selftest init):
```gdscript
if _selftest:
    level = 5
    start_game()
```
Check `catches > 5` at level 5. If catches drop to 0, drift is too high or catch window too small.
Tune `DRIFT_MAX` down or `CATCH_RX_MIN` up.

Document what you found/changed in the commit message.

---

## Task 7 — Full QA Flow Check

Trace every game flow in `main.gd` and `overlay.gd` by code review. Confirm:

### Menu → Playing
- `phase == "menu"` shows title_plate + overlay text
- Any tap/click calls `start_game()` → `phase = "playing"`
- `start_game()` resets score, lives, level, monkeys, seesaw, gator, generates bananas

### Playing Loop
- Physics: `_physics_process` → `step()` returns `"catch"` or `"miss"` or `""`
- Catch: monkey lands on raised end → other monkey launches
- Miss: `_lose_life()` → `lives -= 1` → if `lives == 0` → `phase = "gameover"`
- Bananas empty: `_next_level()` → level++, new bananas
- Camera follows the airborne monkey (`_cam_y` clamps to world bounds)
- Gator: patrol normally; dash-chomp on miss

### Game Over
- `phase == "gameover"` shows gameover_plate + overlay
- `score > best` → saves new best to disk
- Any tap → `start_game()` (new game, NOT back to menu)

### Missing features (note but don't implement unless fast):
- No "back to menu" from game over (tap always restarts — intentional for now)
- No pause menu
- No level indicator on title screen

For any broken flow you find, fix it and note it in the commit.

---

## Task 8 — Final Verification + Session Log

1. Run selftest — must show `catches > 0`, `phase=playing`.
2. Run `--import` to confirm all assets registered.
3. Create `docs/sessions/` directory and write `docs/sessions/Session_2026-06-26.md`:
   - What was done in each task
   - Discoveries / gotchas
   - Selftest output before and after
   - What's still open

4. Create `docs/TODO.md` with open items discovered during QA.

5. Create `docs/PROJECT_STATE.md`:
```
# Project State — Monkey Overboard
- **2026-06-26** — Overnight sprint: active gator (v1.1), sprite sheets committed,
  title/gameover polish, difficulty verification. Selftest passing.
```

6. Final commit covering everything not yet committed.

---

## Priority Order (if time runs short)

1. **Task 1** (sprite sheets) — must be committed before anything else
2. **Task 2** (selftest) — verify core loop never broke
3. **Task 3** (active gator) — the main new feature
4. **Task 7** (QA flow check) — catch broken flows
5. **Task 4** (title best score) — quick polish
6. **Task 5** (gameover polish) — quick polish
7. **Task 6** (difficulty tuning) — only if selftest shows issues
8. **Task 8** (final verify + docs) — always last

---

## Notes + Gotchas

- **Low-res viewport**: Everything is in 135×240 "world space". The window shows at 540×960
  via `window/stretch/mode=viewport`. All draw calls use 135×240 coordinates. Don't use
  pixel sizes that assume 540×960 — you'll draw things 4× too big.
- **Single-file architecture**: Everything is in `main.gd` and `overlay.gd`. There are no
  separate scenes for title/gameover — they're just phases in the same scene. Work within this.
- **Sprite scale**: Sprites are generated at 4× final size, then scaled down. The
  `AnimatedSprite2D` nodes in the scene use `scale = Vector2(0.5, 0.5)` to compensate.
  If you regenerate sprites, keep the same final dimensions.
- **Gemini model**: Use `models/gemini-3.1-flash-image` (NOT `gemini-3-pro-image-preview` —
  that name is expired/wrong). GEMINI_API_KEY env var must be set.
- **No GUT**: Run `-- --mo-selftest` instead. It's the only automated check.
- **`_draw()` vs sprites**: The background, tree, water, seesaw base, and HUD are drawn via
  GDScript `_draw()` calls (not sprites). The monkey, gator, banana, splash are `AnimatedSprite2D`
  nodes. Don't mix these up when editing.
