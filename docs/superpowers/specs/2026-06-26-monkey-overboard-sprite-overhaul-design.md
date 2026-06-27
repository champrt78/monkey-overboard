# Monkey Overboard — Sprite Overhaul Design

## Goal
Replace every gameplay sprite with a coherent, modern-retro pixel-art set in the style of the reference project *Mulletdown* (detailed pixel art, bold black outlines, high-contrast cel shading, saturated warm palette, transparent background). Fix the white-background issue on the current monkey sprites and add a flying animation.

## Reference Style
- Thick black or near-black outlines.
- 2–3 tone cel-shading with strong top-left light.
- Chunky, expressive, slightly muscular/cartoony proportions.
- Warm palette: browns, golds, jungle greens, water blues/oranges.
- Transparent PNG, no background mat, no white border.

## Scope
- **In scope:** monkey, gator, banana, splash, seesaw plank sprites and their SpriteFrames.
- **Out of scope (for this pass):** title/game-over plates, sky/tree/water backgrounds, UI/HUD polish.

## Asset List

| Asset | File | Frames | Description |
|---|---|---|---|
| Monkey | `assets/sprites/monkey_sheet.png` | 8 | idle×2, ascend×2, descend×2, tumble×2 |
| Gator | `assets/sprites/gator_sheet.png` | 5 | patrol×2, alert×1, chomp×2 |
| Banana | `assets/sprites/banana_sheet.png` | 3 | idle wobble |
| Splash | `assets/sprites/splash_sheet.png` | 5 | splash expansion |
| Seesaw | `assets/sprites/seesaw_plank.png` | 1 | detailed wood plank with metal fulcrum |

## Animation States

### Monkey
- `idle` — when standing on the plank.
- `ascending` — when `vy < 0` (arms reaching up).
- `descending` — when `vy > 0` (arms tucked/falling).
- `tumble` — occasional flair spin; can be triggered on high catches or every N catches.

### Gator
- `patrol` — swimming back and forth.
- `alert` — rearing up before a dash.
- `chomp` — biting at the splash.

### Banana
- `default` — gentle wobble loop.

### Splash
- `default` — expansion/dissipate one-shot.

## Prompt Strategy
Use Gemini image generation with the Mulletdown title plate as a style reference. Each prompt must include:
- "pixel art sprite sheet"
- "transparent background"
- "no white border, no background, no mat"
- "thick black outline"
- "cel-shaded, 2–3 colors"
- "side-view 2D game sprite"
- Character-specific pose/action description.

## Integration
1. Generate PNGs at roughly 32×32–64×64 per frame.
2. Lay them out as horizontal sprite sheets.
3. Update the existing `.tres` SpriteFrames to point at the new sheets and set frame counts.
4. Update `main.gd` to map `ascending`/`descending` correctly and add optional `tumble`.
5. Run `run_selftest.ps1`; expected output: `catches>0, phase=playing`.
6. Run windowed to visually inspect for white boxes and crisp pixels.

## Success Criteria
- All sprites have transparent backgrounds in-game.
- Monkey clearly shows different poses for ascending vs descending.
- Visual style feels consistent with the Mulletdown reference.
- Headless self-test still passes.
