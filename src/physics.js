// Monkey integration, wall bounce, catch/launch flip, banana grabs, miss.
window.MO = window.MO || {};

MO.physics = (function () {
  const C = MO.config;
  const E = MO.entities;

  function randDrift(level) {
    const d = E.driftForLevel(level);
    return (Math.random() * 2 - 1) * d;
  }

  // Launch a monkey upward from a point (used at round start and on every catch).
  function launch(monkey, x, y, level) {
    monkey.state = "air";
    monkey.x = x;
    monkey.y = y;
    monkey.vy = C.LAUNCH_VY;
    monkey.vx = randDrift(level);
  }

  // Advance one fixed step. Returns an event string when something notable
  // happens this step: "catch", "miss", or null.
  function step(state, dt) {
    const { seesaw } = state;
    const air = state.monkeys[state.airIndex];
    const ground = state.monkeys[1 - state.airIndex];

    // Smoothly chase the player's target see-saw position.
    seesaw.x += (seesaw.targetX - seesaw.x) * Math.min(1, dt * 14);

    // Keep the grounded monkey planted on the down end.
    const dn = E.downEnd(seesaw);
    ground.state = "ground";
    ground.x = dn.x;
    ground.y = dn.y - C.MONKEY_R;

    // Integrate the airborne monkey.
    air.vy += C.GRAV * dt;
    air.x += air.vx * dt;
    air.y += air.vy * dt;
    air.spin += air.vx * dt * 0.02;

    // Bounce off the world's side walls.
    if (air.x < C.MONKEY_R) {
      air.x = C.MONKEY_R;
      air.vx = Math.abs(air.vx);
    } else if (air.x > C.WORLD_W - C.MONKEY_R) {
      air.x = C.WORLD_W - C.MONKEY_R;
      air.vx = -Math.abs(air.vx);
    }

    // Banana grabs (only the airborne monkey grabs).
    grabBananas(state, air);

    // Catch: falling monkey meets the raised end.
    if (air.vy > 0) {
      const up = E.upEnd(seesaw);
      const withinX = Math.abs(air.x - up.x) <= state.catchRadius;
      const withinY = air.y >= up.y - 34 && air.y <= up.y + 34;
      if (withinX && withinY) {
        doCatch(state, air, ground, up, seesaw);
        return "catch";
      }
    }

    // Miss: monkey reaches the water.
    if (air.y >= C.WATER_Y) {
      air.y = C.WATER_Y;
      return "miss";
    }

    return null;
  }

  function grabBananas(state, air) {
    const reach = C.MONKEY_R + C.BANANA_R;
    for (let i = state.bananas.length - 1; i >= 0; i--) {
      const b = state.bananas[i];
      const dx = b.x - air.x;
      const dy = b.y - air.y;
      if (dx * dx + dy * dy <= reach * reach) {
        state.bananas.splice(i, 1);
        state.score += C.POINTS_BANANA;
        if (state.onBanana) state.onBanana(b);
      }
    }
  }

  // The caught monkey lands on the up end (pushing it down); the grounded
  // monkey is flung up from the old down end.
  function doCatch(state, air, ground, up, seesaw) {
    const oldDown = E.downEnd(seesaw);

    // Fling the previously-grounded monkey skyward.
    launch(ground, oldDown.x, oldDown.y - C.MONKEY_R, state.level);

    // The caught monkey becomes grounded where it landed.
    air.state = "ground";
    air.x = up.x;
    air.y = up.y - C.MONKEY_R;
    air.vx = 0;
    air.vy = 0;

    // Flip the see-saw and hand "airborne" over to the freshly launched monkey.
    seesaw.upSide *= -1;
    state.airIndex = 1 - state.airIndex;
    state.score += C.POINTS_CATCH;
  }

  return { step, launch };
})();
