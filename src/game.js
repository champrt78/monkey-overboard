// Main: state machine (menu / playing / gameover), fixed-step loop, glue.
window.MO = window.MO || {};

(function () {
  const C = MO.config;
  const E = MO.entities;
  const P = MO.physics;
  const G = MO.gator;
  const R = MO.render;

  const canvas = document.getElementById("game");
  const ctx = canvas.getContext("2d");
  canvas.width = C.VIEW_W;
  canvas.height = C.VIEW_H;

  const BEST_KEY = "monkey-overboard-best";

  const state = {
    phase: "menu", // menu | playing | gameover
    score: 0,
    best: Number(localStorage.getItem(BEST_KEY) || 0),
    lives: C.LIVES,
    level: 1,
    time: 0,
    monkeys: [E.makeMonkey("ground"), E.makeMonkey("air")],
    airIndex: 1,
    seesaw: E.makeSeesaw(),
    bananas: [],
    gator: G.make(),
    catchRadius: C.CATCH_RX_BASE,
    onBanana: null,
  };

  const splashes = [];

  function startGame() {
    state.phase = "playing";
    state.score = 0;
    state.lives = C.LIVES;
    state.level = 1;
    state.seesaw = E.makeSeesaw();
    state.gator = G.make();
    state.bananas = E.generateBananas(1);
    state.catchRadius = E.catchRadiusForLevel(1);
    splashes.length = 0;
    resetRound();
  }

  // Re-seat the monkeys on the see-saw and launch one (bananas are left as-is).
  function resetRound() {
    state.airIndex = 1;
    state.seesaw.upSide = 1;
    const dn = E.downEnd(state.seesaw);
    state.monkeys[0].state = "ground";
    state.monkeys[0].x = dn.x;
    state.monkeys[0].y = dn.y - C.MONKEY_R;
    P.launch(state.monkeys[1], state.seesaw.x, C.SEESAW_Y - 60, state.level);
  }

  function nextLevel() {
    state.level += 1;
    state.bananas = E.generateBananas(state.level);
    state.catchRadius = E.catchRadiusForLevel(state.level);
  }

  function loseLife(splashX) {
    state.lives -= 1;
    spawnSplash(splashX, C.WATER_Y);
    G.chompAt(state.gator, splashX);
    if (state.lives <= 0) {
      state.phase = "gameover";
      if (state.score > state.best) {
        state.best = state.score;
        localStorage.setItem(BEST_KEY, String(state.best));
      }
    } else {
      resetRound();
    }
  }

  function spawnSplash(x, y) {
    const parts = [];
    for (let i = 0; i < 10; i++) {
      parts.push({
        x, y,
        vx: (Math.random() * 2 - 1) * 120,
        vy: -Math.random() * 220 - 60,
        r: 4 + Math.random() * 5,
      });
    }
    splashes.push({ parts, life: 1 });
  }

  function updateSplashes(dt) {
    for (let i = splashes.length - 1; i >= 0; i--) {
      const s = splashes[i];
      s.life -= dt * 1.6;
      for (const p of s.parts) {
        p.vy += 600 * dt;
        p.x += p.vx * dt;
        p.y += p.vy * dt;
      }
      if (s.life <= 0) splashes.splice(i, 1);
    }
  }

  // --- input ---
  MO.input.attach(canvas, {
    onMove: (worldX) => {
      if (state.phase === "playing") {
        state.seesaw.targetX = Math.max(C.PLANK, Math.min(C.WORLD_W - C.PLANK, worldX));
      }
    },
    onTap: () => {
      if (state.phase === "menu" || state.phase === "gameover") startGame();
    },
  });

  // --- fixed-step loop ---
  let last = performance.now();
  let acc = 0;

  function frame(now) {
    let dt = (now - last) / 1000;
    last = now;
    if (dt > 0.25) dt = 0.25; // avoid spiral-of-death after a tab pause
    state.time += dt;

    if (state.phase === "playing") {
      acc += dt;
      while (acc >= C.FIXED_DT) {
        const ev = P.step(state, C.FIXED_DT);
        G.update(state.gator, C.FIXED_DT);
        if (ev === "miss") {
          loseLife(state.monkeys[state.airIndex].x);
        }
        if (state.phase === "playing" && state.bananas.length === 0) {
          nextLevel();
        }
        acc -= C.FIXED_DT;
        if (state.phase !== "playing") { acc = 0; break; }
      }
    } else {
      G.update(state.gator, dt);
    }
    updateSplashes(dt);

    R.draw(ctx, state, splashes);
    if (state.phase !== "playing") drawOverlay();

    requestAnimationFrame(frame);
  }

  function drawOverlay() {
    ctx.fillStyle = "rgba(8,26,18,0.55)";
    ctx.fillRect(0, 0, C.VIEW_W, C.VIEW_H);
    ctx.textAlign = "center";
    ctx.fillStyle = "#fff";
    if (state.phase === "menu") {
      ctx.font = "bold 56px system-ui, sans-serif";
      ctx.fillText("Monkey", C.VIEW_W / 2, C.VIEW_H * 0.34);
      ctx.fillText("Overboard", C.VIEW_W / 2, C.VIEW_H * 0.34 + 60);
      ctx.font = "20px system-ui, sans-serif";
      ctx.fillText("Catch the falling monkey on the see-saw.", C.VIEW_W / 2, C.VIEW_H * 0.52);
      ctx.fillText("Grab bananas. Don't feed the gator.", C.VIEW_W / 2, C.VIEW_H * 0.52 + 28);
      ctx.font = "bold 26px system-ui, sans-serif";
      ctx.fillText("Tap to start", C.VIEW_W / 2, C.VIEW_H * 0.68);
    } else {
      ctx.font = "bold 52px system-ui, sans-serif";
      ctx.fillText("Game Over", C.VIEW_W / 2, C.VIEW_H * 0.38);
      ctx.font = "28px system-ui, sans-serif";
      ctx.fillText("Score " + state.score, C.VIEW_W / 2, C.VIEW_H * 0.48);
      ctx.fillText("Best " + state.best, C.VIEW_W / 2, C.VIEW_H * 0.48 + 36);
      ctx.font = "bold 24px system-ui, sans-serif";
      ctx.fillText("Tap to play again", C.VIEW_W / 2, C.VIEW_H * 0.64);
    }
    ctx.textAlign = "left";
  }

  // --- responsive letterbox fit ---
  function fit() {
    const ar = C.VIEW_W / C.VIEW_H;
    const ww = window.innerWidth, wh = window.innerHeight;
    let w = ww, h = ww / ar;
    if (h > wh) { h = wh; w = wh * ar; }
    canvas.style.width = w + "px";
    canvas.style.height = h + "px";
  }
  window.addEventListener("resize", fit);
  fit();

  requestAnimationFrame(frame);
})();
