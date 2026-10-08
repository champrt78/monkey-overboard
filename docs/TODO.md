# TODO - Monkey Overboard

## Now
- [x] Phase 6: Polish (level banner, screen shake, score pop). — COMPLETED 2026-10-08
- [ ] Phase 5b: Real-device Android playtest. — BLOCKED: no Android device/adb

## Next
- [ ] Pause menu / back-to-menu from game over.
- [ ] High-score leaderboard screen.

## Completed (kept for reference)
- [x] Phase 0: Visual baseline — run in editor, screenshot all 3 screens, verify drag input coordinate mapping
- [x] Phase 1: Title + game-over art via Gemini
- [x] Phase 2: Press Start 2P pixel font
- [x] Phase 3: Off-screen seesaw indicator
- [x] Phase 4: SFX — 6 sounds (launch/catch/banana/splash/chomp/life-lost)
- [x] Phase 5: Android packaging + signed debug APK export
- [x] 2026-06-26 - Sprite sheets regenerated with transparent backgrounds.
- [x] 2026-06-26 - Active gator v1.1 (`patrol -> telegraph -> lunge -> retreat`) implemented.
- [x] 2026-06-26 - Title best score + game-over stats polish.
- [x] 2026-06-26 - Difficulty/QA review; selftest passes.
- [x] 2026-06-27 - 1:1 pixel-scale sprite overhaul, camera overshoot/indicator, keyboard seesaw control, banana bunches; selftest passes; debug APK rebuilt.

## Later / Ideas
- [ ] Optional: point the off-screen chevron at the see-saw's **up end** (`seesaw.x + up_side*PLANK`) instead of the fulcrum.
- [ ] Sprite art Phase 5+: further AnimatedSprite2D polish over procedural draw calls.

## Blocked
- Real-device Android playtest: no Android device or `adb` access in this environment.

## Done
- [x] 2026-06-23 - Web prototype v1 built + playtested; design approved/locked.
- [x] 2026-06-23 - Godot 4.6 port (physics/constants 1:4 from web, low-res pixel viewport, headless self-test); verified core loop runs clean.
- [x] 2026-06-23 - Handoff doc + project docs scaffolding written for Kimi.
- [x] 2026-06-26 - Title/game-over art plates + Press Start 2P font + off-screen indicator + SFX wiring verified.
- [x] 2026-06-26 - Android debug APK exports and signs successfully.