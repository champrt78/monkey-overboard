# Monkey Overboard - handoff to Kimi Code (2026-06-23)

**To:** Kimi Code
**From:** Claude (orientation, verification, docs scaffolding; Opus advisor consulted once)
**Repo:** `champrt78/monkey-overboard` (this repo). Up to date with `origin/main` as of this doc.

This doc explains exactly where the project is, what's verified, and what to do next - ranked. Read it top to bottom before touching code.

---

## 1. What this project is

A portrait-mode arcade score-chaser (spiritual descendant of Bally/Midway's *Clowns*, 1978, reskinned). A see-saw floats on a river at the base of a tall tree; two monkeys take turns launching up to grab bananas. Slide the see-saw so its raised end catches the falling monkey - each catch flips the see-saw and fires the *other* monkey skyward. Miss -> he splashes -> the gator chomps -> lose a life. Three lives, endless, level up by clearing every banana.

Full design: `docs/superpowers/specs/2026-06-23-monkey-overboard-design.md` (status: **Approved, v1 scope locked**).

## 2. Two codebases - which one is authoritative

There are **two** complete implementations in this repo. Know which to edit:

| Path | What it is | Status for go-forward work |
| --- | --- | --- |
| `/` (root: `index.html`, `style.css`, `src/*.js`) | Vanilla JS + Canvas web prototype. Where the mechanic and pixel look were prototyped and **verified by playtesting**. Deploys to GitHub Pages. | **Frozen reference.** Treat as the spec-in-code. Don't add features here. Read it to understand intended behavior. |
| `/godot` (`main.gd`, `main.tscn`, `project.godot`) | Godot 4.6 port - **the real ship target** (native Android `.aab`). | **This is where you build.** All new feature work happens here. |

**Rule:** the web build is the source of truth for *gameplay behavior*; the Godot build is the source of truth for *what ships*. If they ever disagree on feel, the web build wins (it's the playtested one) - port the web behavior into Godot, don't invent new behavior in Godot. Don't let the two drift silently; if you change gameplay, note it.

## 3. Current state (what's verified, what's not)

**Verified working:**
- The Godot port **compiles and runs cleanly** - no parse errors, no runtime errors.
- The **core loop executes end-to-end**: catch -> flip -> re-launch -> banana grab -> miss -> gator dash/chomp -> lose life -> level-up on banana clear. Confirmed via the headless self-test (see Section 6).
- **Physics/constants are a faithful 1:4 port** of the verified web build. Every Godot constant in `main.gd` equals the web `src/config.js` value divided by 4 (the world is rendered in a 135x240 low-res buffer = web's 540x960 / 4). I spot-checked the full constant list - parity is exact.
- The pixel look comes from `project.godot`'s `135x240` viewport with `stretch/mode="viewport"`, `aspect="keep"`, `default_texture_filter=0` (nearest). Portrait orientation set. GL Compatibility renderer (good for low-end Android).

**NOT verified (and can't be, headlessly):** anything that depends on seeing a rendered frame. The self-test runs with no display and autopilots the see-saw, so it proves the *simulation* is correct, not that the game *looks* right on a screen. **Do a real playtest (editor + device) before calling any visual item done.** This is the single most important caveat in this doc.

## 4. What to do next - ranked

### 4a. [TOP / HEADLINE] Android packaging -> Play Store `.aab`

This is the stated goal of the whole port and **nothing for it exists yet**: no `export_presets.cfg`, no app icon, no Android build config. (`export_presets.cfg` is intentionally gitignored - it can hold keystore paths/passwords - so each machine sets it up locally.)

**Highest-leverage move: copy the structure from the `plummet` repo** (`C:\Users\Ray\kimi-repos\plummet`). Plummet is the same author's Godot 4.6 Android game and already has the full skeleton: `export_presets.cfg`, `android/` build template, app icon wiring, Gradle/AAB config, and the Godot Android export setup. Mirror it here rather than building from scratch. Steps, roughly:
- Install the Godot Android build template + export preset for this project.
- Add an app icon (`assets/icon` + `project.godot` `config/icon`). None exists yet.
- Set a unique package name (e.g. `com.champrt78.monkeyoverboard`), version code/name.
- Confirm portrait lock and the `135x240` viewport stretch survive on a real device aspect ratio (the letterbox math is in `project.godot`, not code).
- Produce a debug `.aab`/`.apk`, install on a phone, **playtest the actual touch controls** (drag-to-slide via `InputEventScreenDrag` - this has never run on hardware).

### 4b. [#1 GAMEPLAY GAP] Port the off-screen see-saw indicator

The design (spec section "World & camera") requires an indicator at the screen's bottom edge showing the see-saw's horizontal position **while it's scrolled off-screen** during the monkey's apex (the "blind window"). The **web build has this** (`src/render.js` -> `drawOffscreenIndicator`, a yellow downward chevron). **The Godot port omits it** - this is the one place the port is not at parity with the verified web build, and it's the key aiming aid for a human player (the self-test autopilot cheats past it by reading the monkey's x directly, so the loop "works" in testing but is much harder to actually play without this).

Why it matters: with VIEW_H=240 and the camera following the monkey, the see-saw (at y=700.5, world height 720) is off the bottom of the screen for most of each arc - the player is dragging something they can't see. The chevron is how they aim.

**Prescribed 1:4 port (drop-in).** Mirror the web logic, divided by 4. Two things make it correct in Godot, both load-bearing:
1. **It is screen-space.** Do NOT route the coordinates through `_wy()` (the camera offset helper). The HUD does the same - draw in raw viewport coords.
2. **Verify it actually renders on a real frame** - winding order, draw order (call it after `_draw_hud()` so it sits on top of the water, before `_draw_overlay()`), and alpha. A headless self-test will pass whether or not this draws correctly, so it proves nothing here - you must look at it.

```gdscript
# Call from _draw(), in screen space, after _draw_hud():
func _draw_offscreen_indicator() -> void:
    if phase != "playing":
        return
    # Only while the see-saw is below the bottom of the 240-tall view (the blind window).
    if SEESAW_Y - _cam_y <= VIEW_H - 2.5:   # web: SEESAW_Y - camY <= VIEW_H - 10, /4
        return
    var x: float = seesaw.x
    var col := Color(BANANA.r, BANANA.g, BANANA.b, 0.95)   # web rgba(255,210,59,0.95) == BANANA #ffd23c
    var pts := PackedVector2Array([
        Vector2(x - 3.5, VIEW_H - 6.5),   # web x-14, VIEW_H-26  (/4)
        Vector2(x + 3.5, VIEW_H - 6.5),   # web x+14, VIEW_H-26
        Vector2(x,       VIEW_H - 2.0),   # web x,    VIEW_H-8
    ])
    draw_colored_polygon(pts, col)
```

Optional refinement worth considering: the web chevron points at `seesaw.x` (the fulcrum center), but the catch actually happens at the **up end** (`seesaw.x + seesaw.up_side * PLANK`). The design doc asks for a guide "at the catch (up) end." Pointing the chevron at the up-end instead of the fulcrum would be more precise - your call after playtesting which feels right. The web build's faint vertical guide line at the catch end was specced but never built in either version; add it only if the chevron alone isn't enough.

### 4c. [v1.1, designed but stubbed] Active gator

Currently the gator is **passive** (spec v1): patrols slowly, dashes to the splash point on a miss, chomps, resumes. That's fully implemented and working (`_update_gator`, modes `patrol`/`dash`/`chomp`). The spec's **v1.1 active gator** (`lurk -> telegraph -> lunge -> retreat`, periodically leaping at a low monkey on higher levels) is **not built**. The gator is deliberately a self-contained module so wiring the lunge in later won't disturb the rest - keep it that way. This is a fast-follow, not a v1 blocker.

### 4d. [polish, later] Sound, sprite art

Both explicitly out of scope for v1 (spec). Flat-shape art ships first; sprites can drop in over the existing `_draw_*` functions later. No audio yet - easy add.

## 5. Things NOT to worry about

- **No seed/determinism contract, no leaderboard.** Unlike plummet, this game has no daily-seed reproducibility requirement and no server. `randomize()` + a `localStorage`/`user://` best score is correct - don't add seed plumbing or anti-cheat. (If a leaderboard is ever wanted, that's a new feature, not a fix.)
- The `_cam_y = WORLD_H - VIEW_H` assignment at the top of `_draw()` (line ~351) is immediately overwritten during play - it's just the menu/default framing. Harmless, leave it.

## 6. How to verify your work (regression asset)

The port ships a **headless self-test** that autopilots the see-saw and runs ~1200 frames of the real game loop, then prints a summary and quits. Run it after every change to catch regressions in the simulation:

```
godot --headless --path godot --mo-selftest
```

Expected output (numbers vary, the shape doesn't):
```
SELFTEST catches=3 score=96 lives=2 level=1 phase=playing bananas_left=3
```
A healthy run shows `catches > 0` and `phase=playing` (the loop sustained without crashing). The test deliberately also exercises the miss/gator/lose-life path, so `lives < 3` is normal, not a failure.

PowerShell wrapper that worked on this machine (Godot 4.6 console build on the Desktop; the bare `--headless` invocation can hang waiting, so wrap it with an explicit timeout + redirect):
```powershell
$godot = "C:\Users\Ray\Desktop\Godot_v4.6-stable_win64_console.exe"
$proj  = "C:\Users\Ray\kimi-repos\monkey-overboard\godot"
$p = Start-Process -FilePath $godot -ArgumentList @('--headless','--path',$proj,'--mo-selftest') `
     -NoNewWindow -PassThru `
     -RedirectStandardOutput "$env:TEMP\mo_out.txt" -RedirectStandardError "$env:TEMP\mo_err.txt"
if (-not $p.WaitForExit(40000)) { $p.Kill() }
Get-Content "$env:TEMP\mo_out.txt"
```

**Reminder:** the self-test verifies *simulation*, never *rendering*. For 4a and 4b (anything visual or touch-based), there is no substitute for a real run in the editor and on a device.

## 7. Project docs in this repo

Per the author's working conventions, this repo now has:
- `docs/PROJECT_STATE.md` - milestones (big wins only).
- `docs/TODO.md` - the canonical open-work list (the ranked items above live here too).
- `docs/sessions/Session_YYYY-MM-DD.md` - per-day narrative log. Update it proactively as you work.
- `docs/handoffs/` - this doc.

Keep `docs/TODO.md` and the session log current as you go - that's how context survives between sessions and between you and the author.