// Entity factories + banana-field generation.
window.MO = window.MO || {};

MO.entities = (function () {
  const C = MO.config;

  function makeMonkey(state) {
    return { x: 0, y: 0, vx: 0, vy: 0, state: state, spin: 0 };
  }

  // The see-saw: a plank pivoting on a floating fulcrum. `upSide` is +1 (right
  // end raised) or -1 (left end raised). `x` is the fulcrum's horizontal pos.
  function makeSeesaw() {
    return { x: C.WORLD_W / 2, targetX: C.WORLD_W / 2, upSide: 1 };
  }

  function upEnd(seesaw) {
    return { x: seesaw.x + seesaw.upSide * C.PLANK, y: C.SEESAW_Y - C.TILT };
  }
  function downEnd(seesaw) {
    return { x: seesaw.x - seesaw.upSide * C.PLANK, y: C.SEESAW_Y };
  }

  // Scatter a fresh field of bananas across the reachable band of the tree.
  function generateBananas(level) {
    const count = C.BANANA_BASE + C.BANANA_PER_LEVEL * (level - 1);
    const bananas = [];
    const margin = 50;
    for (let i = 0; i < count; i++) {
      bananas.push({
        x: margin + Math.random() * (C.WORLD_W - margin * 2),
        y: C.BANANA_Y_MIN + Math.random() * (C.BANANA_Y_MAX - C.BANANA_Y_MIN),
        r: C.BANANA_R,
        wobble: Math.random() * Math.PI * 2,
      });
    }
    return bananas;
  }

  function driftForLevel(level) {
    return Math.min(
      C.DRIFT_MAX,
      C.DRIFT_BASE + C.DRIFT_PER_LEVEL * (level - 1)
    );
  }

  function catchRadiusForLevel(level) {
    return Math.max(C.CATCH_RX_MIN, C.CATCH_RX_BASE - (level - 1) * 2);
  }

  return {
    makeMonkey,
    makeSeesaw,
    upEnd,
    downEnd,
    generateBananas,
    driftForLevel,
    catchRadiusForLevel,
  };
})();
