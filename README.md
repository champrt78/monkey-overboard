# 🐵 Monkey Overboard

A portrait-mode arcade score-chaser. A see-saw floats on a river at the foot of a tall
tree; two monkeys take turns launching up to grab bananas. Slide the see-saw to catch the
falling monkey on the raised end — each catch fires the *other* monkey skyward. Miss, and
he splashes into the water where a gator is waiting.

Spiritually descended from Bally/Midway's *Clowns* (1978), reskinned and re-themed.

## Play

- **Open `index.html`** in any browser — double-click it, or serve the folder.
- **Drag** left/right to slide the see-saw.
- Catch the falling monkey on the **raised** end. Grab bananas for points. Clear the tree
  to advance a level. Three misses and you're out.

It's built as plain HTML + Canvas + vanilla JS with **no build step**, so it runs straight
from the filesystem and deploys as static files.

### Local dev server (optional)

```bash
npx serve .
# or
python -m http.server 8000
```

## Tech

- Vanilla JS + HTML5 Canvas, zero dependencies, zero build.
- Fixed-timestep simulation (120 Hz) under `requestAnimationFrame`.
- Responsive portrait canvas (540×960 logical) that letterboxes to any screen.
- High score in `localStorage`.

### Structure

| File | Responsibility |
|------|----------------|
| `src/config.js` | Tunable constants (feel/difficulty) |
| `src/input.js` | Touch/pointer → see-saw position |
| `src/entities.js` | Monkey / see-saw / banana factories + field generation |
| `src/physics.js` | Monkey motion, wall bounce, catch/launch flip, banana grabs |
| `src/gator.js` | Alligator state machine (passive in v1) |
| `src/render.js` | Camera, world drawing, HUD |
| `src/game.js` | State machine + main loop |

Full design notes: [`docs/superpowers/specs/2026-06-23-monkey-overboard-design.md`](docs/superpowers/specs/2026-06-23-monkey-overboard-design.md)

## Roadmap

- **v1** *(current)* — full loop, passive gator that chomps on a miss.
- **v1.1** — active gator: lunges out of the water on higher levels (`lurk → telegraph → lunge → retreat`).
- Later — sound, sprite art, polish.

## License

MIT
