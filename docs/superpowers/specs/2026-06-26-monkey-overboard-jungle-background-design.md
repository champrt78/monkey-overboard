# Monkey Overboard — Jungle Background Plate Design

## Goal
Replace the current procedural blue-sky/tree/water background with a single detailed pixel-art jungle plate that reads as dense jungle with only a small sky strip at the top.

## Visual Layout
- **Canvas size:** 135×720 pixels (matches the logical world height).
- **Top ~60 px:** narrow sky strip with distant treetop silhouettes and a few clouds.
- **Middle ~600 px:** dense jungle — thick tree trunk, hanging vines, layered canopy leaves, dappled light patches, tropical plants.
- **Bottom ~60 px:** water surface with subtle reflections, reeds, or lily pads.
- **Style:** Mulletdown-style modern retro pixel art, thick black outlines where appropriate, strong cel-shading, saturated jungle palette (greens, browns, blues, golds), transparent areas only where the background plate does not fill the canvas (none expected).

## Integration
- Add `godot/assets/backgrounds/jungle_bg.png`.
- Add a `Sprite2D` node named `JungleBG` as the first child of `Main` so it renders behind everything.
- In `main.gd`, update the background sprite position in `_update_camera()` so it follows the camera vertically.
- Remove or disable the old procedural `_draw_sky`, `_draw_tree`, and `_draw_water` calls from `_draw()`.
- Keep the title/game-over plates and HUD unchanged.

## Verification
- Headless self-test still passes (`catches>0, phase=playing`).
- Windowed run shows the full jungle plate behind the gameplay.
- No white borders or transparent gaps in the background.
