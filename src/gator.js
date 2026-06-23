// The alligator. v1: passive patrol + chomp-on-miss feedback.
// v1.1 will add an active "lunge" state — the `mode` field is here for that.
window.MO = window.MO || {};

MO.gator = (function () {
  const C = MO.config;

  function make() {
    return {
      x: C.WORLD_W / 2,
      dir: 1,
      mode: "patrol",   // "patrol" | "dash" | "chomp"  (future: "lunge")
      targetX: C.WORLD_W / 2,
      chompTimer: 0,
    };
  }

  // Send the gator after a splash point.
  function chompAt(g, x) {
    g.mode = "dash";
    g.targetX = Math.max(60, Math.min(C.WORLD_W - 60, x));
  }

  function update(g, dt) {
    switch (g.mode) {
      case "patrol": {
        g.x += g.dir * C.GATOR_PATROL_SPEED * dt;
        if (g.x < 60) { g.x = 60; g.dir = 1; }
        else if (g.x > C.WORLD_W - 60) { g.x = C.WORLD_W - 60; g.dir = -1; }
        break;
      }
      case "dash": {
        const d = g.targetX - g.x;
        const step = C.GATOR_DASH_SPEED * dt;
        if (Math.abs(d) <= step) {
          g.x = g.targetX;
          g.mode = "chomp";
          g.chompTimer = 0.6;
        } else {
          g.x += Math.sign(d) * step;
        }
        break;
      }
      case "chomp": {
        g.chompTimer -= dt;
        if (g.chompTimer <= 0) g.mode = "patrol";
        break;
      }
    }
  }

  return { make, chompAt, update };
})();
