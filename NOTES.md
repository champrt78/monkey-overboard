# Monkey Overboard Studio Notes

## Project Status
- Branch: gm/polish-level-banner
- Phase: Production
- Current story: story-001-level-banner (Level banner visual/feel feature)

## Decisions Ray made
(none yet)

## Session Log

### Session 2026-10-08
- Picked up story-001-level-banner from production/epics/polish/
- Confirmed branch: gm/polish-level-banner
- Confirmed baseline: gate has pre-existing issues (plugin scene nodes, no test framework)
- Story type: Visual/Feel (no automated tests required)
- Implementing: "LEVEL N" banner display on level advance, ~1.5 seconds duration
- Architecture: Add Label to overlay.gd, hook to main.gd _next_level()
