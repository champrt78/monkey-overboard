# Monkey Overboard — Monkey / Camera / Banana Overhaul Design

## Context

*Monkey Overboard* is a portrait arcade score-chaser inspired by Bally/Midway's *Clowns* (1978). The current build has the core loop working, but playtesting surfaced four issues:

1. Monkey sprites look flat / off-brand.
2. Camera doesn't frame the seesaw well during the catch.
3. Seesaw control feels unresponsive / unclear.
4. Bananas are too sparse and don't read as a "tree full of fruit".

This design addresses all four.

## Goals

1. Overhaul monkey sprites to match the modern-retro jungle plate.
2. Make the camera pan smoothly so the seesaw is visible when it matters.
3. Make seesaw control obvious and reliable on both phone (touch) and desktop (mouse/keyboard).
4. Fill the tree with banana bunches that reward vertical travel.

## Non-Goals

- No new game modes or scoring systems.
- No changes to physics constants unless playtesting demands it.
- No new sound effects.

## 1. Monkey Sprite Overhaul

### Direction

Modern-retro pixel art, thick black outline, cel-shaded, cohesive with the jungle background plate. Eight frames in one horizontal sheet, final size **224×28** (each frame 28×28). The scene scales the sprite node by 0.5, so in-world it reads as 14×14 per frame.

### Frames

| Frames | Animation | Notes |
|--------|-----------|-------|
| 0–1 | idle | Standing on the seesaw, slight breathing bounce. |
| 2–3 | ascending | Arms reaching up, body stretched. |
| 4–5 | descending | Arms tucked, body compact. |
| 6–7 | tumble | Spin/flip for the launch catch transition. |

### Generation Strategy

To make background removal easy (hand cleanup if Gemini leaves artifacts), generate **eight individual 28×28 PNGs** on a solid white background, then pack them into the 224×28 sheet with a small script. Individual frames avoid neighboring-frame bleed and make magic-wand cleanup trivial.

### Acceptance

- Transparent background (or solid white if hand-cleanup is needed).
- All 8 frames clearly read as the same monkey.
- Style matches the jungle background plate.

## 2. Smart Camera Framing

### Problem

The current camera follows the airborne monkey with a fixed vertical offset. When the monkey is high, the seesaw is off-screen; when falling, the player can't see where to move the catch end.

### Solution

Use two camera targets and blend between them based on game state:

- **Ascending target:** `air.y - VIEW_H * 0.45` (current behavior).
- **Catch target:** `(SEESAW_Y + air.y) / 2 - VIEW_H * 0.5` — frames both the monkey and the seesaw, centered vertically.

Blend factor `t` depends on how close the monkey is to the catch:

```gdscript
var dist_to_seesaw := SEESAW_Y - air.y
var catch_window := 180.0  # world units above the seesaw where framing starts
var t := clamp(1.0 - dist_to_seesaw / catch_window, 0.0, 1.0)
```

Only apply the blend when the monkey is airborne and descending (`air.vy > 0`). When ascending, `t = 0`. Smooth the final `_cam_y` with a lerp or spring so the pan doesn't jerk.

### Acceptance

- During most of the ascent, the monkey is centered and readable.
- During the descent, the seesaw slides into view before the catch.
- The transition is smooth, not jarring.

## 3. Banana Bunches in the Tree

### Problem

Bananas are currently scattered individually and sparsely across a wide Y range. They don't look like tree fruit.

### Solution

Generate bananas as **bunches** positioned along horizontal "branches" at different heights:

- Increase base count: `BANANA_BASE` from 12 to **24**.
- Per-level increase: `BANANA_PER_LEVEL` from 3 to **6**.
- Place branch rows at roughly 80-unit vertical intervals from `BANANA_Y_MIN` up to the canopy.
- For each branch row, pick a random side of the trunk (left or right) and place a cluster of 3–5 bananas close together.
- Add a few scattered solo bananas near the trunk for variety.

Each banana remains an individual collectible (no new bunch entity), but the tight grouping creates the visual of a bunch. When one banana is grabbed, the rest of the bunch stays.

### Acceptance

- The tree looks visibly full of banana bunches.
- Clearing a level still requires traveling up through the tree.
- Performance is unchanged (same AnimatedSprite2D pooling).

## 4. Seesaw Control

### Problem

The seesaw didn't feel controllable during the windowed test.

### Solution

- **Keep the existing drag logic** (drag maps to the raised/catch end), but add **keyboard fallback** for desktop testing:
  - Left / Right arrows or A / D move the seesaw center left/right.
  - This is only for desktop debug/QA; phone stays touch-only.
- Add a subtle **visual drag zone hint** at the bottom of the screen during play (a faint horizontal bar) so phone users know where to slide.
- Ensure the seesaw target clamps still allow the catch end to reach both walls.

### Acceptance

- Keyboard controls work in the desktop build.
- Touch/mouse drag still works.
- The catch end reaches both walls.

## Open Questions

1. Should the monkey sprite frame size stay at 28×28, or do we want larger frames with a smaller scene scale?
2. Should banana bunches award bonus points when the whole bunch is cleared?
3. Should the camera ever show the water/gator at the bottom when the monkey is very high, or only when descending?

## Success Criteria

- New monkey sheet is transparent and looks at home against the jungle background.
- A full playthrough shows the seesaw during catches without losing track of the monkey.
- The tree feels dense with bananas.
- Selftest still passes (`catches > 0`, `phase = playing`).
