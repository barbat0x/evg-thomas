/**
 * Orbite elliptique autour du bouton (sin/cos), comme l’approche canvas de
 * https://stackoverflow.com/questions/31603154/how-to-make-object-orbit-from-behind-to-front
 * Ici : positionnement en px via getBoundingClientRect, pas de canvas.
 */
(function () {
  'use strict';

  var field = document.getElementById('home-orbit-field');
  var hub = document.getElementById('home-cta');
  if (!field || !hub) return;

  var sprites = Array.prototype.slice.call(
    field.querySelectorAll('.js-orbit-sprite'),
  );
  if (!sprites.length) return;

  var reduceMotion = false;
  try {
    reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)')
      .matches;
  } catch (e) {
    /* ignore */
  }

  var tOffset = performance.now() / 1000;

  function numAttr(el, name) {
    var raw = el.getAttribute(name);
    if (raw == null || raw === '') {
      return NaN;
    }
    return parseFloat(String(raw).replace(',', '.'));
  }

  function hubCenter() {
    var r = hub.getBoundingClientRect();
    return {
      x: r.left + r.width / 2,
      y: r.top + r.height / 2,
    };
  }

  /** Vertical un peu plus ample qu’horizontal (étoiles plus haut/bas). */
  function orbitBaseXY() {
    var w = window.innerWidth;
    var h = window.innerHeight;
    return {
      bx: w * 0.47,
      by: h * 0.46,
    };
  }

  function step(nowMs) {
    var t = reduceMotion ? tOffset : nowMs / 1000;
    var c = hubCenter();
    var cx = c.x;
    var cy = c.y;
    var bases = orbitBaseXY();

    for (var i = 0; i < sprites.length; i++) {
      var el = sprites[i];
      var rxPct = numAttr(el, 'data-rx-pct');
      var ryPct = numAttr(el, 'data-ry-pct');
      var speed = numAttr(el, 'data-speed');
      var phase = numAttr(el, 'data-phase');
      var tilt = numAttr(el, 'data-tilt');
      if (isNaN(tilt)) {
        tilt = 0;
      }
      if (isNaN(speed)) {
        speed = 0;
      }
      if (isNaN(phase)) {
        phase = 0;
      }

      if (isNaN(rxPct) || isNaN(ryPct)) continue;

      var rx = rxPct * bases.bx;
      var ry = ryPct * bases.by;
      var angle = phase + (reduceMotion ? 0 : t * speed);
      var ox = Math.sin(angle) * rx;
      var oy = Math.cos(angle) * ry;

      el.style.left = cx + ox + 'px';
      el.style.top = cy + oy + 'px';
      el.style.transform =
        'translate(-50%, -50%) rotate(' + tilt + 'deg)';

      /* Profondeur : au-dessus du hub (y écran plus petit) = derrière */
      var starY = cy + oy;
      el.style.zIndex = starY > cy ? '2' : '0';
    }

    requestAnimationFrame(step);
  }

  requestAnimationFrame(step);
})();

/** Même bascule ±30° que les portraits du pool (game-compose.js). */
(function () {
  'use strict';

  var img = document.querySelector('.home-center-photo__img');
  if (!img) return;

  var reduceMotion = false;
  try {
    reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)')
      .matches;
  } catch (e) {
    /* ignore */
  }
  if (reduceMotion) return;

  var timer = null;

  function randomTiltDelayMs() {
    return Math.round(500 + Math.random() * 1500);
  }

  function tick() {
    var durationMs = randomTiltDelayMs();
    img.style.setProperty(
      '--home-pool-tilt-duration',
      durationMs / 1000 + 's',
    );
    var isLeft = img.classList.contains('home-center-photo__img--tilt-left');
    img.classList.toggle('home-center-photo__img--tilt-left', !isLeft);
    img.classList.toggle('home-center-photo__img--tilt-right', isLeft);
    timer = setTimeout(tick, durationMs);
  }

  var hasTilt =
    img.classList.contains('home-center-photo__img--tilt-left') ||
    img.classList.contains('home-center-photo__img--tilt-right');
  if (!hasTilt) {
    var initialLeft = Math.random() < 0.5;
    img.classList.add(
      initialLeft
        ? 'home-center-photo__img--tilt-left'
        : 'home-center-photo__img--tilt-right',
    );
  }

  /* Double rAF : inclinaison dès le HTML, 1er basculement dès le 1er frame utile. */
  requestAnimationFrame(function () {
    requestAnimationFrame(tick);
  });
})();
