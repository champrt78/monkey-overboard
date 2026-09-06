---
project_name: Monkey Overboard
status: active
completion_percent: 80
next_task: 'Phase 6: Polish (level banner, screen shake, score pop).'
open_milestone_count: 4
last_milestone_date: '2026-06-27'
---

# Monkey Overboard — Hub Metadata

This file is the structured-data sidecar to `docs/PROJECT_STATE.md`, read by Ray's
Projects Hub dashboard server. Edit the frontmatter above when project state changes;
this prose is for humans only.

Notes for humans:

- Two versions live in this repo: the vanilla-JS web prototype at the root (v1 shipped
  and deployed to GitHub Pages) and the Godot 4.6 port under `godot/`, the real Android
  ship target. A signed debug APK builds cleanly (`builds/monkey-overboard-debug.apk`).
- The most recent milestone (2026-06-27) was a 1:1 pixel-scale sprite overhaul with
  camera framing, restored keyboard control, and larger banana bunches; the headless
  self-test passes (`catches=4, phase=playing`).
- Open work: Phase 6 polish, a real-device Android playtest (blocked — no device or
  `adb` in this environment), a pause/back-to-menu flow, and a high-score leaderboard.
