// Monkey Overboard — tunable constants. Everything that affects feel lives here.
window.MO = window.MO || {};

MO.config = {
  // Logical render resolution (portrait). The canvas always draws at this size
  // and is scaled/letterboxed to fit the device.
  VIEW_W: 540,
  VIEW_H: 960,

  // The world is three screens tall.
  SCREENS: 3,
  get WORLD_W() { return this.VIEW_W; },
  get WORLD_H() { return this.VIEW_H * this.SCREENS; },

  // Waterline / see-saw placement (measured from the top of the world).
  get WATER_Y() { return this.WORLD_H - 60; },
  get SEESAW_Y() { return this.WATER_Y - 18; },

  // See-saw geometry.
  PLANK: 82,   // half-length of the plank
  TILT: 46,    // how high the raised end sits above the fulcrum
  CATCH_RX_BASE: 56,  // horizontal catch tolerance at level 1
  CATCH_RX_MIN: 40,   // floor as difficulty ramps

  // Monkey.
  MONKEY_R: 22,
  GRAV: 900,         // px/s^2
  LAUNCH_VY: -2100,  // initial upward velocity off the see-saw
  DRIFT_BASE: 95,    // |max horizontal launch velocity| at level 1
  DRIFT_PER_LEVEL: 18,
  DRIFT_MAX: 230,

  // Bananas.
  BANANA_R: 16,
  BANANA_BASE: 12,
  BANANA_PER_LEVEL: 3,
  BANANA_Y_MIN: 430,   // highest a banana can sit (must be reachable)
  get BANANA_Y_MAX() { return this.WATER_Y - 240; },

  // Gator.
  GATOR_Y_OFFSET: 30,   // how far below the waterline it patrols
  GATOR_PATROL_SPEED: 55,
  GATOR_DASH_SPEED: 760,

  // Scoring.
  POINTS_BANANA: 10,
  POINTS_CATCH: 2,

  LIVES: 3,

  // Simulation.
  FIXED_DT: 1 / 120,
};
