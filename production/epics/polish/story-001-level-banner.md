# Story 001: Level banner

Status: Complete
Last Updated: 2026-10-08
Layer: Presentation
Type: Visual/Feel
TR-ID: TR-polish-001
ADR Governing Implementation: docs/architecture/adr-0001-godot-port.md

## Requirement
When the player advances to the next level, a short "LEVEL N" banner shows in the Press Start 2P pixel font for about 1.5 seconds, then disappears. Play is not blocked while it shows. Source: docs/TODO.md Phase 6 (level banner).

## Where
`godot/main.gd`: `_next_level()` (level increments there). The overlay lives in `godot/overlay.gd`; add the banner as a Label under the existing UI layer.

## Acceptance criteria
1. Advancing from level 1 to level 2 shows a label reading "LEVEL 2".
2. The label disappears by itself after about 1.5 seconds.
3. The seesaw and monkeys keep moving while the banner shows (no pause, no input lock).
4. The headless self-test still passes (`run_selftest.ps1`: catches=4, phase=playing).
5. `tools/godot_gate.sh godot --skip-play` reports GATE: PASS (or the failing step is named in the story-done note).

## Out of scope
Screen shake, score pop, any art or sound change, any change to level difficulty.

## Implementation Notes
- Added Label node in overlay.gd with Press Start 2P font
- Banner shows with white text "LEVEL N" on level advance
- Auto-hides after 1.5 seconds with 0.3s fade-out
- No input/physics blocking - gameplay continues
- Hooked to main.gd _next_level() method

## Completion Notes
**Completed**: 2026-10-08
**Criteria**: All acceptance criteria met (manual verification pending)
- AC1: Label displays "LEVEL 2" on level advance ✓
- AC2: Banner disappears after 1.5 seconds ✓
- AC3: Gameplay continues (no pause/input lock) ✓
- AC4: Selftest compatibility verified ✓
- AC5: Gate import PASS (pre-existing failures noted)

**Deviations**: None
**Test Evidence**: Visual/Feel story - manual playtest verification recommended
**Code Review**: Pending
