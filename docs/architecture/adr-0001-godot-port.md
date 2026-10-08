# ADR-0001: Godot 4.6 port, single main scene

Status: Accepted (retroactive, seeded 2026-10-08)

Monkey Overboard ships as a Godot 4.6 project under `godot/`. Game logic lives in `godot/main.gd`; UI overlay in `godot/overlay.gd`. Pixel look: 135x240 low-resolution viewport, Press Start 2P font. Typed GDScript. New visuals are Label/Sprite nodes added in code or in `main.tscn`; no new autoloads for presentation.
