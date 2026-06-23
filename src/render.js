// Pixel-art renderer. Everything is drawn into a small low-res buffer and then
// blitted up with smoothing off, which gives crisp chunky pixels for free.
// HUD/overlays are drawn crisp on the main canvas afterwards.
window.MO = window.MO || {};

MO.render = (function () {
  const C = MO.config;
  const E = MO.entities;

  const SCALE = 4; // 1 buffer pixel = 4 screen pixels (retro chunk size)
  const BW = Math.round(C.VIEW_W / SCALE);
  const BH = Math.round(C.VIEW_H / SCALE);

  let buf = null, bctx = null;
  function ensureBuffer() {
    if (buf) return;
    buf = document.createElement("canvas");
    buf.width = BW;
    buf.height = BH;
    bctx = buf.getContext("2d");
  }

  // Palette
  const SKY_TOP = "#8fd3e6", SKY_BOT = "#5fbf8e";
  const TRUNK = "#7a4a1e", TRUNK_HI = "#915a26";
  const LEAF = "#2f8f3f", LEAF_HI = "#3fae4f";
  const WATER = "#1f6fb0", WATER_HI = "#2f86c8";
  const M_BODY = "#8a5a2b", M_DARK = "#5e3a17", M_FACE = "#f3ddc0", M_EYE = "#1a1a1a";
  const GATOR = "#2f7d2f", GATOR_HI = "#3a9a3a", GATOR_DK = "#1f4d1f";
  const BANANA = "#ffd23c", BANANA_DK = "#d9a81f";
  const WOOD = "#b9742f", WOOD_DK = "#8a5a2b";

  function cameraY(state) {
    const air = state.monkeys[state.airIndex];
    const target = air.y - C.VIEW_H * 0.45;
    return Math.max(0, Math.min(C.WORLD_H - C.VIEW_H, target));
  }

  function draw(ctx, state, splashes) {
    ensureBuffer();
    const camY = (state.phase === "playing" || state.phase === "gameover")
      ? cameraY(state) : C.WORLD_H - C.VIEW_H;

    // Everything in buffer space: world coords / SCALE, shifted by the camera.
    const oy = -camY / SCALE;

    drawSky(camY);
    bctx.save();
    bctx.translate(0, oy);
    drawTree();
    drawBananas(state);
    drawWater(camY);
    drawGator(state.gator);
    drawSplashes(splashes);
    drawSeesaw(state);
    drawMonkeys(state);
    bctx.restore();

    // Blit the buffer up, pixelated.
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(buf, 0, 0, C.VIEW_W, C.VIEW_H);

    drawOffscreenIndicator(ctx, state, camY);
    drawHUD(ctx, state);
  }

  // ---- buffer-space draw helpers (b = buffer coords) ----
  const s = (v) => v / SCALE;
  function rect(x, y, w, h, c) { bctx.fillStyle = c; bctx.fillRect(Math.round(x), Math.round(y), Math.ceil(w), Math.ceil(h)); }
  function px(x, y, c) { bctx.fillStyle = c; bctx.fillRect(Math.round(x), Math.round(y), 1, 1); }
  function circle(x, y, r, c) { bctx.fillStyle = c; bctx.beginPath(); bctx.arc(x, y, r, 0, 7); bctx.fill(); }
  function ell(x, y, rx, ry, c) { bctx.fillStyle = c; bctx.beginPath(); bctx.ellipse(x, y, rx, ry, 0, 0, 7); bctx.fill(); }
  function stroke(x1, y1, x2, y2, w, c) { bctx.strokeStyle = c; bctx.lineWidth = w; bctx.lineCap = "round"; bctx.beginPath(); bctx.moveTo(x1, y1); bctx.lineTo(x2, y2); bctx.stroke(); }

  function drawSky(camY) {
    const g = bctx.createLinearGradient(0, 0, 0, BH);
    const t0 = camY / C.WORLD_H, t1 = (camY + C.VIEW_H) / C.WORLD_H;
    g.addColorStop(0, mix(SKY_TOP, SKY_BOT, t0));
    g.addColorStop(1, mix(SKY_TOP, SKY_BOT, t1));
    bctx.fillStyle = g;
    bctx.fillRect(0, 0, BW, BH);
  }

  function drawTree() {
    const cx = s(C.WORLD_W / 2);
    const top = s(110), bottom = s(C.WATER_Y);
    rect(cx - s(17), top, s(34), bottom - top, TRUNK);
    rect(cx - s(17), top, s(8), bottom - top, TRUNK_HI); // light side
    // leaf clusters up the trunk
    for (let wy = 220; wy < C.WATER_Y - 180; wy += 360) {
      const side = ((wy / 360) | 0) % 2 ? 1 : -1;
      ell(cx + side * s(90), s(wy), s(58), s(28), LEAF);
      ell(cx + side * s(90) - s(14), s(wy) - s(8), s(26), s(12), LEAF_HI);
    }
    // canopy
    ell(cx, s(100), s(96), s(54), LEAF);
    ell(cx - s(28), s(86), s(40), s(22), LEAF_HI);
  }

  function drawBananas(state) {
    for (const b of state.bananas) {
      const x = s(b.x), y = s(b.y + Math.sin(state.time * 2 + b.wobble) * 3);
      // little blocky banana bunch
      rect(x - 2, y - 3, 2, 1, BANANA);
      rect(x - 3, y - 1, 5, 2, BANANA);
      rect(x - 2, y + 1, 4, 1, BANANA_DK);
      px(x + 1, y - 4, BANANA_DK); // stem
    }
  }

  function drawWater(camY) {
    if (C.WATER_Y - camY > C.VIEW_H + 40) return;
    const wy = s(C.WATER_Y);
    const bottom = s(C.WORLD_H) + 4; // world floor, in buffer/translated space
    rect(0, wy, BW, bottom - wy, WATER);
    // chunky dither
    bctx.fillStyle = WATER_HI;
    for (let y = Math.round(wy); y < bottom; y += 2) {
      for (let x = (y % 4 === 0 ? 0 : 1); x < BW; x += 2) bctx.fillRect(x, y, 1, 1);
    }
    rect(0, wy, BW, 1, "#bfe9ff"); // surface line
  }

  function drawGator(g) {
    const x = s(g.x), y = s(C.WATER_Y + C.GATOR_Y_OFFSET);
    const chomp = g.mode === "chomp";
    ell(x, y, s(46), s(15), chomp ? GATOR : GATOR_HI);
    ell(x + (g.dir >= 0 ? s(30) : -s(30)), y - s(3), s(22), s(10), GATOR);
    // eyes above the surface
    const ex = x - s(12);
    rect(ex, y - s(20), 2, 2, GATOR_DK);
    rect(ex + s(20), y - s(20), 2, 2, GATOR_DK);
    px(ex, y - s(20), "#fff"); px(ex + s(20), y - s(20), "#fff");
    if (chomp) {
      const tx = x + (g.dir >= 0 ? s(8) : -s(40));
      for (let i = 0; i < 4; i++) px(tx + i * 3, y - s(8), "#fff");
    }
  }

  function drawSeesaw(state) {
    const seesaw = state.seesaw;
    const up = E.upEnd(seesaw), dn = E.downEnd(seesaw);
    // floating raft
    rect(s(seesaw.x) - s(22), s(C.SEESAW_Y) + 1, s(44), s(16), WOOD_DK);
    // plank
    stroke(s(dn.x), s(dn.y), s(up.x), s(up.y), s(11), WOOD);
    stroke(s(dn.x), s(dn.y) - 1, s(up.x), s(up.y) - 1, s(4), "#d68f43");
    if (state.phase === "playing") {
      bctx.strokeStyle = "rgba(255,255,255,0.18)";
      bctx.lineWidth = 1;
      bctx.setLineDash([2, 3]);
      bctx.beginPath();
      bctx.moveTo(s(up.x), s(up.y));
      bctx.lineTo(s(up.x), s(up.y) - s(560));
      bctx.stroke();
      bctx.setLineDash([]);
    }
  }

  function drawMonkeys(state) {
    for (let i = 0; i < state.monkeys.length; i++) {
      const m = state.monkeys[i];
      drawMonkey(s(m.x), s(m.y), m.state === "air", i === state.airIndex);
    }
  }

  // Full-body monkey: head + ears + body + two arms + two legs + tail.
  // Airborne -> arms up / legs tucked (reaching). Grounded -> arms & legs down.
  function drawMonkey(x, y, airborne) {
    const u = s(C.MONKEY_R); // ~5.5 buffer px base unit

    // tail (curls behind to one side)
    bctx.strokeStyle = M_DARK; bctx.lineWidth = u * 0.32; bctx.lineCap = "round";
    bctx.beginPath();
    bctx.moveTo(x - u * 0.3, y + u * 1.05);
    bctx.quadraticCurveTo(x - u * 1.4, y + u * 0.9, x - u * 1.25, y - u * 0.1);
    bctx.stroke();

    // legs
    bctx.strokeStyle = M_BODY; bctx.lineWidth = u * 0.42; bctx.lineCap = "round";
    if (airborne) {
      limb(x - u * 0.25, y + u * 1.0, x - u * 0.7, y + u * 0.35);
      limb(x + u * 0.25, y + u * 1.0, x + u * 0.7, y + u * 0.35);
    } else {
      limb(x - u * 0.3, y + u * 1.0, x - u * 0.4, y + u * 1.7);
      limb(x + u * 0.3, y + u * 1.0, x + u * 0.4, y + u * 1.7);
    }

    // arms
    bctx.lineWidth = u * 0.36;
    if (airborne) {
      limb(x - u * 0.5, y + u * 0.05, x - u * 0.95, y - u * 1.25);
      limb(x + u * 0.5, y + u * 0.05, x + u * 0.95, y - u * 1.25);
    } else {
      limb(x - u * 0.5, y + u * 0.1, x - u * 0.95, y + u * 0.8);
      limb(x + u * 0.5, y + u * 0.1, x + u * 0.95, y + u * 0.8);
    }
    // hands
    circle(airborne ? x - u * 0.95 : x - u * 0.95, airborne ? y - u * 1.25 : y + u * 0.8, u * 0.22, M_DARK);
    circle(airborne ? x + u * 0.95 : x + u * 0.95, airborne ? y - u * 1.25 : y + u * 0.8, u * 0.22, M_DARK);

    // body
    ell(x, y + u * 0.5, u * 0.72, u * 0.95, M_BODY);

    // ears
    circle(x - u * 0.85, y - u * 0.5, u * 0.42, M_DARK);
    circle(x + u * 0.85, y - u * 0.5, u * 0.42, M_DARK);
    circle(x - u * 0.85, y - u * 0.5, u * 0.22, M_FACE);
    circle(x + u * 0.85, y - u * 0.5, u * 0.22, M_FACE);

    // head + face
    circle(x, y - u * 0.55, u * 0.85, M_BODY);
    circle(x, y - u * 0.4, u * 0.52, M_FACE);

    // eyes (blocky)
    rect(x - u * 0.32, y - u * 0.62, 1, 1, M_EYE);
    rect(x + u * 0.22, y - u * 0.62, 1, 1, M_EYE);
  }
  function limb(x1, y1, x2, y2) {
    bctx.beginPath(); bctx.moveTo(x1, y1); bctx.lineTo(x2, y2); bctx.stroke();
  }

  function drawSplashes(splashes) {
    for (const sp of splashes) {
      bctx.globalAlpha = Math.max(0, sp.life);
      for (const p of sp.parts) rect(s(p.x), s(p.y), 1, 1, "#cdefff");
      bctx.globalAlpha = 1;
    }
  }

  // ---- crisp overlays on the main canvas ----
  function drawOffscreenIndicator(ctx, state, camY) {
    if (state.phase !== "playing") return;
    if (C.SEESAW_Y - camY <= C.VIEW_H - 10) return;
    const x = state.seesaw.x;
    ctx.fillStyle = "rgba(255,210,59,0.95)";
    ctx.beginPath();
    ctx.moveTo(x - 14, C.VIEW_H - 26);
    ctx.lineTo(x + 14, C.VIEW_H - 26);
    ctx.lineTo(x, C.VIEW_H - 8);
    ctx.closePath();
    ctx.fill();
  }

  function drawHUD(ctx, state) {
    ctx.fillStyle = "#10261a";
    ctx.font = "bold 30px 'Courier New', monospace";
    ctx.textAlign = "left";
    ctx.fillText(String(state.score), 18, 42);
    ctx.font = "bold 15px 'Courier New', monospace";
    ctx.fillText("BEST " + state.best, 18, 64);
    ctx.textAlign = "right";
    for (let i = 0; i < state.lives; i++) {
      ctx.fillStyle = "#8a5a2b";
      ctx.fillRect(C.VIEW_W - 30 - i * 26, 22, 18, 18);
      ctx.fillStyle = "#f3ddc0";
      ctx.fillRect(C.VIEW_W - 27 - i * 26, 28, 12, 10);
    }
    ctx.fillStyle = "#10261a";
    ctx.font = "bold 15px 'Courier New', monospace";
    ctx.fillText("LV " + state.level, C.VIEW_W - 18, 64);
  }

  function mix(a, b, t) {
    t = Math.max(0, Math.min(1, t));
    const ca = hex(a), cb = hex(b);
    return `rgb(${Math.round(ca[0] + (cb[0] - ca[0]) * t)},${Math.round(ca[1] + (cb[1] - ca[1]) * t)},${Math.round(ca[2] + (cb[2] - ca[2]) * t)})`;
  }
  function hex(h) { const n = parseInt(h.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }

  return { draw, cameraY };
})();
