# Monkey Overboard — Design

**Date:** 2026-06-23
**Status:** Approved (v1 scope locked)

## Concept

A portrait-mode arcade score-chaser, spiritually descended from Bally/Midway's *Clowns* (1978) but reskinned and re-themed so it is not a direct ripoff.

A see-saw floats on a river at the base of a tall mangrove tree. **Two monkeys** take turns launching off the see-saw, sailing up the tree to grab bananas. The player slides the see-saw left/right to catch the falling monkey on the raised end — each catch fires the *other* monkey skyward. Miss, and the monkey splashes into the water where an alligator is waiting. Endless until you run out of lives.

## Why this works on a phone

The original *Clowns* was a wide landscape game. By standing the playfield up into a ~3-screen-tall tree with a vertically panning camera, the layout fits portrait naturally and the "where will he come down?" tension becomes the core feel.

## World & camera

- World is one tall logical canvas: **540 × 2880** (3 portrait screens of 540 × 960).
- A mangrove tree rises out of a river. Bananas are scattered up the trunk and branches.
- The see-saw floats on the water near the bottom of the world.
- **Camera** follows the airborne monkey vertically, clamped to world bounds. When the monkey is low, the camera sits at the bottom and the see-saw + water are fully visible. As he rises past mid-screen the camera pans up to reveal the treetop; the see-saw scrolls off-bottom during the apex (brief blind window), then the camera pans back down for the catch.
- A small indicator at the screen's bottom edge shows the see-saw's horizontal position while it is off-screen, plus a faint vertical guide line at the catch (up) end so the player can line up.

## Core loop

1. One monkey is airborne; the other sits grounded on the **down** end of the see-saw.
2. The player drags left/right to slide the see-saw so its **up** end is under the falling monkey.
3. Catch → the impact flips the see-saw, launching the grounded monkey upward. The caught monkey is now grounded on the (newly down) end. Repeat.
4. The airborne monkey grabs any banana it overlaps → +score, banana removed.
5. Miss the falling monkey → he hits the water → the gator chomps → lose a life (3 lives).
6. Clear every banana on the tree → fresh tree with more bananas and tighter difficulty (faster horizontal drift, smaller catch zone). Endless.

## Controls

Touch-and-drag anywhere to slide the see-saw horizontally (1:1, lightly smoothed). Mouse drag works on desktop for development.

## The alligator

Lives just under the waterline.

- **v1 (this scope):** passive. Patrols slowly side to side; on a miss it dashes to the splash point, plays a chomp, then resumes patrol. Pure consequence/feedback — it does not threaten an in-flight monkey.
- **v1.1 (fast-follow, not built yet):** active. A state machine (`lurk → telegraph → lunge → retreat`) lets it periodically leap out of the water at a low monkey or snap near the see-saw on higher levels, forcing the player to juggle catching *and* dodging.

The gator is a self-contained module so wiring up the lunge later does not disturb the rest of the game.

## Tech

- **Vanilla JS + HTML5 Canvas. Zero build step.** Plain ordered `<script>` tags sharing a global `MO` namespace, so the game runs by double-clicking `index.html` (file://) *and* when deployed.
- Fixed-timestep simulation (120 Hz accumulator) under `requestAnimationFrame` for stable physics.
- Responsive portrait canvas (540 × 960 internal) that letterboxes to fit any phone screen.
- Simple flat vector/canvas art (jungle palette) — no external assets required for v1; sprites can be dropped in later.
- High score persisted in `localStorage`.

### Module layout (`/src`)

| File | Responsibility |
|------|----------------|
| `config.js` | Tunable constants (world size, gravity, launch speed, catch zone, etc.) |
| `input.js` | Pointer/touch → see-saw target x, with screen→world mapping |
| `entities.js` | Monkey / banana / see-saw factories + banana-field generation |
| `physics.js` | Monkey integration, wall bounce, catch/launch flip, miss detection |
| `gator.js` | Alligator state + patrol/chomp (lunge stubbed for v1.1) |
| `render.js` | Camera, world draw, HUD, off-screen indicators |
| `game.js` | State machine (menu/playing/gameover), main loop, glue |

## Ship target

GitHub repo `champrt78/monkey-overboard` → deploy to GitHub Pages or Vercel → playable link on a phone the same day.

## Out of scope for v1

- Active/lunging gator (v1.1)
- Sound (easy add later)
- Sprite art (flat shapes ship first)
- Monetization, leaderboards, accounts
