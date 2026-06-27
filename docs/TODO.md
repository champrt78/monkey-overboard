# TODO - Monkey Overboard

## Now
- [ ] Phase 6: Polish (level banner, screen shake, score pop) — waiting on real-device playtest feedback, or user go-ahead to proceed without device test.

## Next (in kimi-monkey-game.txt phases)
- [x] Phase 0: Visual baseline — run in editor, screenshot all 3 screens, verify drag input coordinate mapping
- [x] Phase 1: Title + game-over art via Gemini
- [x] Phase 2: Press Start 2P pixel font
- [x] Phase 3: Off-screen seesaw indicator
- [x] Phase 4: SFX — 6 sounds (launch/catch/banana/splash/chomp/life-lost)
- [x] Phase 5: Android packaging + signed debug APK export
- [ ] Phase 5b: Real-device playtest
- [ ] Phase 6: Polish (level banner, screen shake, score pop)

## Later / Ideas
- [ ] **v1.1 active gator**: `lurk -> telegraph -> lunge -> retreat` state machine, leaps at low monkeys on higher levels. Designed in the spec, gator module is deliberately self-contained to make this drop-in. Currently passive (patrol/dash/chomp).
- [ ] Optional: point the off-screen chevron at the see-saw's **up end** (`seesaw.x + up_side*PLANK`) instead of the fulcrum, and/or add the specced faint vertical guide line at the catch end (never built in either version).
- [ ] Sprite art Phase 5+: AnimatedSprite2D integration over the procedural draw calls (see kimi-monkey-overboard.txt Phase 3).

## Blocked
- Real-device Android playtest: no Android device or `adb` access in this environment.

## Done
- [x] 2026-06-23 - Web prototype v1 built + playtested; design approved/locked.
- [x] 2026-06-23 - Godot 4.6 port (physics/constants 1:4 from web, low-res pixel viewport, headless self-test); verified core loop runs clean.
- [x] 2026-06-23 - Handoff doc + project docs scaffolding written for Kimi.
- [x] 2026-06-26 - Title/game-over art plates + Press Start 2P font + off-screen indicator + SFX wiring verified.
- [x] 2026-06-26 - Android debug APK exports and signs successfully.