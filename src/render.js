// Camera + all drawing: world, tree, water, see-saw, monkeys, bananas, gator, HUD.
window.MO = window.MO || {};

MO.render = (function () {
  const C = MO.config;
  const E = MO.entities;

  // Camera follows the airborne monkey, clamped to the world.
  function cameraY(state) {
    const air = state.monkeys[state.airIndex];
    const target = air.y - C.VIEW_H * 0.45;
    return Math.max(0, Math.min(C.WORLD_H - C.VIEW_H, target));
  }

  function draw(ctx, state, splashes) {
    const camY = state.phase === "playing" || state.phase === "gameover"
      ? cameraY(state) : C.WORLD_H - C.VIEW_H;

    drawSky(ctx, camY);
    ctx.save();
    ctx.translate(0, -camY);

    drawTree(ctx);
    drawBananas(ctx, state);
    drawWater(ctx, camY);
    drawGator(ctx, state.gator);
    drawSplashes(ctx, splashes);
    drawSeesaw(ctx, state);
    drawMonkeys(ctx, state);

    ctx.restore();

    drawOffscreenIndicator(ctx, state, camY);
    drawHUD(ctx, state);
  }

  function drawSky(ctx, camY) {
    // A vertical gradient over the whole world, sampled for the current view.
    const g = ctx.createLinearGradient(0, 0, 0, C.VIEW_H);
    const topT = camY / C.WORLD_H;
    const botT = (camY + C.VIEW_H) / C.WORLD_H;
    g.addColorStop(0, mix("#aee7ff", "#5bbf8a", topT));
    g.addColorStop(1, mix("#aee7ff", "#5bbf8a", botT));
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, C.VIEW_W, C.VIEW_H);
  }

  function drawTree(ctx) {
    const trunkW = 70;
    const cx = C.WORLD_W / 2;
    ctx.fillStyle = "#6b4226";
    ctx.fillRect(cx - trunkW / 2, 120, trunkW, C.WATER_Y - 120);
    // A few leafy branches.
    ctx.fillStyle = "#3f8f3f";
    for (let y = 220; y < C.WATER_Y - 200; y += 360) {
      const side = (y / 360) % 2 < 1 ? -1 : 1;
      ctx.beginPath();
      ctx.ellipse(cx + side * 90, y, 110, 46, 0, 0, Math.PI * 2);
      ctx.fill();
    }
    // Canopy at the top.
    ctx.fillStyle = "#2f7d2f";
    ctx.beginPath();
    ctx.ellipse(cx, 110, 180, 90, 0, 0, Math.PI * 2);
    ctx.fill();
  }

  function drawBananas(ctx, state) {
    for (const b of state.bananas) {
      ctx.save();
      ctx.translate(b.x, b.y + Math.sin(state.time * 2 + b.wobble) * 3);
      ctx.rotate(-0.5);
      ctx.fillStyle = "#ffd93b";
      ctx.strokeStyle = "#c79a13";
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.arc(0, 0, b.r, Math.PI * 0.15, Math.PI * 1.05);
      ctx.arc(2, 2, b.r, Math.PI * 1.05, Math.PI * 0.15, true);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
      ctx.restore();
    }
  }

  function drawWater(ctx, camY) {
    // Only paint if the waterline is anywhere near the current view.
    if (C.WATER_Y - camY > C.VIEW_H + 40) return;
    ctx.fillStyle = "rgba(40,110,170,0.85)";
    ctx.fillRect(0, C.WATER_Y, C.WORLD_W, C.WORLD_H - C.WATER_Y);
    ctx.strokeStyle = "rgba(255,255,255,0.5)";
    ctx.lineWidth = 3;
    ctx.beginPath();
    for (let x = 0; x <= C.WORLD_W; x += 20) {
      const yy = C.WATER_Y + Math.sin(x * 0.08 + performance.now() * 0.003) * 4;
      if (x === 0) ctx.moveTo(x, yy); else ctx.lineTo(x, yy);
    }
    ctx.stroke();
  }

  function drawGator(ctx, g) {
    const y = C.WATER_Y + C.GATOR_Y_OFFSET;
    const chomping = g.mode === "chomp";
    ctx.fillStyle = chomping ? "#2e6b2e" : "#357a35";
    // Body
    ctx.beginPath();
    ctx.ellipse(g.x, y, 60, 22, 0, 0, Math.PI * 2);
    ctx.fill();
    // Snout
    ctx.beginPath();
    ctx.ellipse(g.x + (g.dir >= 0 ? 55 : -55), y - 4, 34, 14, 0, 0, Math.PI * 2);
    ctx.fill();
    // Eyes above the surface
    ctx.fillStyle = "#1f4d1f";
    ctx.beginPath();
    ctx.arc(g.x - 18, y - 22, 7, 0, Math.PI * 2);
    ctx.arc(g.x + 6, y - 22, 7, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#fff";
    ctx.beginPath();
    ctx.arc(g.x - 18, y - 23, 3, 0, Math.PI * 2);
    ctx.arc(g.x + 6, y - 23, 3, 0, Math.PI * 2);
    ctx.fill();
    if (chomping) {
      ctx.fillStyle = "#fff";
      const sx = g.x + (g.dir >= 0 ? 40 : -70);
      for (let i = 0; i < 5; i++) {
        ctx.beginPath();
        ctx.moveTo(sx + i * 12, y - 12);
        ctx.lineTo(sx + i * 12 + 5, y - 2);
        ctx.lineTo(sx + i * 12 + 10, y - 12);
        ctx.fill();
      }
    }
  }

  function drawSeesaw(ctx, state) {
    const s = state.seesaw;
    const up = E.upEnd(s);
    const dn = E.downEnd(s);
    // Floating raft fulcrum
    ctx.fillStyle = "#8a5a2b";
    ctx.beginPath();
    ctx.moveTo(s.x - 26, C.SEESAW_Y + 6);
    ctx.lineTo(s.x + 26, C.SEESAW_Y + 6);
    ctx.lineTo(s.x + 14, C.SEESAW_Y + 26);
    ctx.lineTo(s.x - 14, C.SEESAW_Y + 26);
    ctx.closePath();
    ctx.fill();
    // Plank
    ctx.strokeStyle = "#b9742f";
    ctx.lineWidth = 12;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(dn.x, dn.y);
    ctx.lineTo(up.x, up.y);
    ctx.stroke();
    // Faint aim guide rising from the catch (up) end
    if (state.phase === "playing") {
      ctx.strokeStyle = "rgba(255,255,255,0.18)";
      ctx.lineWidth = 2;
      ctx.setLineDash([6, 10]);
      ctx.beginPath();
      ctx.moveTo(up.x, up.y);
      ctx.lineTo(up.x, up.y - 600);
      ctx.stroke();
      ctx.setLineDash([]);
    }
  }

  function drawMonkeys(ctx, state) {
    for (const m of state.monkeys) drawMonkey(ctx, m);
  }

  function drawMonkey(ctx, m) {
    ctx.save();
    ctx.translate(m.x, m.y);
    if (m.state === "air") ctx.rotate(m.spin);
    const r = C.MONKEY_R;
    // Ears
    ctx.fillStyle = "#7a4a1e";
    ctx.beginPath();
    ctx.arc(-r * 0.8, -r * 0.2, r * 0.5, 0, Math.PI * 2);
    ctx.arc(r * 0.8, -r * 0.2, r * 0.5, 0, Math.PI * 2);
    ctx.fill();
    // Body/head
    ctx.fillStyle = "#8a5a2b";
    ctx.beginPath();
    ctx.arc(0, 0, r, 0, Math.PI * 2);
    ctx.fill();
    // Face
    ctx.fillStyle = "#e6c79a";
    ctx.beginPath();
    ctx.arc(0, r * 0.15, r * 0.6, 0, Math.PI * 2);
    ctx.fill();
    // Eyes
    ctx.fillStyle = "#222";
    ctx.beginPath();
    ctx.arc(-r * 0.28, -r * 0.1, 2.6, 0, Math.PI * 2);
    ctx.arc(r * 0.28, -r * 0.1, 2.6, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  function drawSplashes(ctx, splashes) {
    for (const s of splashes) {
      ctx.globalAlpha = Math.max(0, s.life);
      ctx.fillStyle = "#cdefff";
      for (const p of s.parts) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
    }
  }

  // When the see-saw is below the view, show where it is along the bottom edge.
  function drawOffscreenIndicator(ctx, state, camY) {
    if (state.phase !== "playing") return;
    if (C.SEESAW_Y - camY <= C.VIEW_H - 10) return;
    const x = state.seesaw.x;
    ctx.fillStyle = "rgba(255,210,59,0.9)";
    ctx.beginPath();
    ctx.moveTo(x - 14, C.VIEW_H - 26);
    ctx.lineTo(x + 14, C.VIEW_H - 26);
    ctx.lineTo(x, C.VIEW_H - 8);
    ctx.closePath();
    ctx.fill();
  }

  function drawHUD(ctx, state) {
    ctx.fillStyle = "#1d3b2a";
    ctx.font = "bold 30px system-ui, sans-serif";
    ctx.textAlign = "left";
    ctx.fillText(String(state.score), 18, 42);
    ctx.font = "bold 16px system-ui, sans-serif";
    ctx.fillText("BEST " + state.best, 18, 64);
    // Lives as little monkeys
    ctx.textAlign = "right";
    for (let i = 0; i < state.lives; i++) {
      ctx.fillStyle = "#8a5a2b";
      ctx.beginPath();
      ctx.arc(C.VIEW_W - 22 - i * 30, 32, 11, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.fillStyle = "#1d3b2a";
    ctx.font = "bold 16px system-ui, sans-serif";
    ctx.fillText("LV " + state.level, C.VIEW_W - 18, 64);
  }

  // --- tiny color lerp helper ---
  function mix(a, b, t) {
    t = Math.max(0, Math.min(1, t));
    const ca = hex(a), cb = hex(b);
    const r = Math.round(ca[0] + (cb[0] - ca[0]) * t);
    const g = Math.round(ca[1] + (cb[1] - ca[1]) * t);
    const bl = Math.round(ca[2] + (cb[2] - ca[2]) * t);
    return `rgb(${r},${g},${bl})`;
  }
  function hex(h) {
    const n = parseInt(h.slice(1), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }

  return { draw, cameraY };
})();
