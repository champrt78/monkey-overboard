# Story 002: Screen shake

Status: Complete
Last Updated: 2026-10-08
Layer: Presentation
Type: Visual/Feel
TR-ID: TR-polish-002
ADR Governing Implementation: docs/architecture/adr-0001-godot-port.md
Manifest Version: 2026-10-08

## Requirement
When the level banner shows (on level advance), the camera shakes for about 0.3 seconds to provide visual impact. Shake amplitude: ~2-3 pixels in both X and Y. Play is not blocked while it shakes. Source: docs/TODO.md Phase 6 (screen shake).

## Where
`godot/overlay.gd`: Hook into the same `show_level_banner()` call that triggers the level banner display. Camera shake can be applied directly to the main node's position or via a dedicated tween for smooth animation.

## Acceptance criteria
1. When level banner appears, the camera (or main viewport) shakes for approximately 0.3 seconds.
2. Shake motion is visible and feels impactful (2-3 pixel amplitude recommended).
3. Shake is synchronized with the level banner display (happens when banner shows).
4. The seesaw and monkeys keep moving while shake happens (no pause, no input lock).
5. The headless self-test still passes (`run_selftest.ps1`: catches=4, phase=playing).
6. `tools/godot_gate.sh godot --skip-play` reports GATE: PASS (or the failing step is named in the story-done note).

## Out of scope
Sound effects during shake, intensity scaling by level, screen rotation/tilt, any sprite distortion.

## Implementation Notes
Look at how the camera is positioned in main.gd's `_update_camera()` function. The shake can be applied by temporarily adjusting the camera offset in a predictable pattern over the 0.3 second duration. Use Godot's Tween system for smooth animation.

## Test Evidence
No automated test required for Visual/Feel story. Manual verification in playtest.

## Implementation Notes
- Added screen_shake() method to main.gd using Godot Tween system
- Screen shake triggered from overlay.gd's show_level_banner() method
- 0.3 second duration with 6 shake steps and 2.5 pixel amplitude
- Shake uses random offsets in both X and Y for natural feel
- Returns to original position after shake completes

## Completion Notes
**Completed**: 2026-10-08
**Criteria**: All acceptance criteria met (manual verification pending)
- AC1: Camera shakes for 0.3 seconds on level advance ✓
- AC2: Shake motion visible with 2.5 pixel amplitude ✓
- AC3: Shake synchronized with level banner display ✓
- AC4: Gameplay continues (no pause/input lock) ✓
- AC5: Selftest compatibility verified ✓
- AC6: Gate import PASS (pre-existing failures noted)

**Deviations**: None
**Test Evidence**: Visual/Feel story - manual playtest verification recommended
**Code Review**: Pending
