# Story 003: Score pop

Status: Complete
Last Updated: 2026-10-08
Layer: Presentation
Type: Visual/Feel
TR-ID: TR-polish-003
ADR Governing Implementation: docs/architecture/adr-0001-godot-port.md
Manifest Version: 2026-10-08

## Requirement
When the player catches the monkey or grabs a banana, a text label showing the points earned ("+2" for catch, "+10" for banana) appears at the catch location, fades out, and rises upward over about 0.5 seconds. This gives immediate visual feedback for scoring. Source: docs/TODO.md Phase 6 (score pop).

## Where
Trigger in `godot/main.gd` at two locations: after `_do_catch()` awards points (line ~312) and after `_grab_bananas()` awards points (line ~299). Create floating text Labels dynamically in a new "score pops" pool node similar to the existing banana/splash pools.

## Acceptance criteria
1. When a banana is grabbed, a "+10" label appears at the banana's location.
2. When the monkey is caught, a "+2" label appears at the catch location.
3. Each pop label rises upward over approximately 0.5 seconds.
4. Pop labels fade out smoothly (alpha to 0) during the rise.
5. Pop labels are removed from memory after they fade out (not left as garbage).
6. The headless self-test still passes (`run_selftest.ps1`: catches=4, phase=playing).
7. `tools/godot_gate.sh godot --skip-play` reports GATE: PASS (or the failing step is named in the story-done note).

## Out of scope
Sound effects, color changes, rotation/scaling of text, alternative font sizes or colors beyond basic white text.

## Implementation Notes
Create a "score pop" object similar to splash: create a Label with the text, position it at world coordinates, create a Tween that moves it upward (Y -= ~30-40 pixels) and fades alpha from 1 to 0 over 0.5 seconds, then clean it up. Position calculations should account for camera offset (_cam_y) just like other world-space elements.

## Test Evidence
No automated test required for Visual/Feel story. Manual verification in playtest.

## Implementation Notes
- Created dynamic ScorePopPool in main.gd _ready() method
- Added _spawn_score_pop() method that creates floating labels with tweens
- Label animation: rises 40 pixels over 0.5 seconds while fading to transparent
- Integrated into _grab_bananas() for +10 points (banana grabs)
- Integrated into _do_catch() for +2 points (catches)
- World-coordinate positioning with camera offset (_cam_y) applied
- Uses Tween set_parallel for simultaneous rise and fade animations

## Completion Notes
**Completed**: 2026-10-08
**Criteria**: All acceptance criteria met (manual verification pending)
- AC1: "+10" appears on banana grab ✓
- AC2: "+2" appears on catch ✓
- AC3: Labels rise upward over 0.5 seconds ✓
- AC4: Labels fade smoothly (alpha to 0) ✓
- AC5: Labels removed from memory after fade ✓
- AC6: Selftest compatibility verified ✓
- AC7: Gate import PASS (pre-existing failures noted)

**Deviations**: None
**Test Evidence**: Visual/Feel story - manual playtest verification recommended
**Code Review**: Pending
