# TODO - Monkey Overboard

## Now
- [ ] **Android packaging -> `.aab`** (the ship target; nothing exists yet). Mirror the `plummet` repo's structure: export preset, Android build template, app icon, package name/version, then build a debug `.aab`/`.apk` and playtest touch controls on a real device. See handoff section 4a.
- [ ] **Port the off-screen see-saw indicator** into the Godot build (the one parity gap vs the verified web prototype; key aiming aid during the apex blind window). Prescribed 1:4 drop-in is in the handoff (section 4b) - screen-space, must be visually verified on a real frame.

## Next
- [ ] App icon asset + `config/icon` wiring (currently none).
- [ ] Real-device playtest pass of the whole loop (touch drag has never run on hardware).

## Later / Ideas
- [ ] **v1.1 active gator**: `lurk -> telegraph -> lunge -> retreat` state machine, leaps at low monkeys on higher levels. Designed in the spec, gator module is deliberately self-contained to make this drop-in. Currently passive (patrol/dash/chomp).
- [ ] Optional: point the off-screen chevron at the see-saw's **up end** (`seesaw.x + up_side*PLANK`) instead of the fulcrum, and/or add the specced faint vertical guide line at the catch end (never built in either version).
- [ ] Sound (out of scope v1, easy add).
- [ ] Sprite art to replace flat shapes (drops in over the existing `_draw_*` functions).

## Blocked
- (none)

## Done
- [x] 2026-06-23 - Web prototype v1 built + playtested; design approved/locked.
- [x] 2026-06-23 - Godot 4.6 port (physics/constants 1:4 from web, low-res pixel viewport, headless self-test); verified core loop runs clean.
- [x] 2026-06-23 - Handoff doc + project docs scaffolding written for Kimi.