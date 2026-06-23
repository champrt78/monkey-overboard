// Pointer/touch input → see-saw target x (in world coords).
window.MO = window.MO || {};

MO.input = (function () {
  const C = MO.config;

  let dragging = false;
  let canvas = null;
  let onMoveCb = null;
  let onTapCb = null;

  // Map a clientX on the (letterboxed) canvas to a world x.
  function clientToWorldX(clientX) {
    const rect = canvas.getBoundingClientRect();
    const t = (clientX - rect.left) / rect.width;
    return Math.max(0, Math.min(1, t)) * C.WORLD_W;
  }

  function attach(canvasEl, opts) {
    canvas = canvasEl;
    onMoveCb = opts.onMove;
    onTapCb = opts.onTap;

    const down = (clientX) => {
      dragging = true;
      if (onTapCb) onTapCb();
      if (onMoveCb) onMoveCb(clientToWorldX(clientX));
    };
    const move = (clientX) => {
      if (dragging && onMoveCb) onMoveCb(clientToWorldX(clientX));
    };
    const up = () => { dragging = false; };

    canvas.addEventListener("pointerdown", (e) => { e.preventDefault(); down(e.clientX); });
    canvas.addEventListener("pointermove", (e) => { e.preventDefault(); move(e.clientX); });
    window.addEventListener("pointerup", up);
    window.addEventListener("pointercancel", up);

    // Block the long-press / scroll gestures that fight a canvas game.
    canvas.addEventListener("touchstart", (e) => e.preventDefault(), { passive: false });
    canvas.addEventListener("touchmove", (e) => e.preventDefault(), { passive: false });
  }

  return { attach };
})();
