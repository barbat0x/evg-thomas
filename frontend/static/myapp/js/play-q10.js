/**
 * Roulette Q10 : tirage animé, arrêt sur le segment gagnant.
 */
(function () {
  'use strict';

  var SEGMENT_COUNT = 8;
  var SEGMENT_ANGLE = 360 / SEGMENT_COUNT;
  var FULL_SPINS = 6;
  var SPIN_MS = 6200;
  var PAUSE_AFTER_STOP_MS = 2000;

  var WIN_INDEX = {
    cash_forced: 0,
    anecdote: 4,
  };

  function spinEndRotation(winIndex) {
    var center = winIndex * SEGMENT_ANGLE + SEGMENT_ANGLE / 2;
    var offset = (360 - center) % 360;
    return FULL_SPINS * 360 + offset;
  }

  function initRoulette(root) {
    var overlay = root.querySelector('.play-q10-overlay');
    if (!overlay) {
      return;
    }
    var wheel = overlay.querySelector('[data-play-q10-wheel]');
    var result = overlay.querySelector('[data-play-q10-result]');
    if (!wheel || !result || wheel.dataset.playQ10SpinStarted === '1') {
      return;
    }
    wheel.dataset.playQ10SpinStarted = '1';

    var reduced =
      window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function reveal() {
      var stage = wheel.closest('.play-q10-roulette');
      if (stage) {
        stage.setAttribute('hidden', '');
      }
      result.removeAttribute('hidden');
      var btn = result.querySelector('button[type="submit"]');
      if (btn) {
        btn.focus();
      }
    }

    if (reduced) {
      reveal();
      return;
    }

    var outcome = wheel.getAttribute('data-play-q10-outcome') || 'anecdote';
    var winIndex = WIN_INDEX[outcome] != null ? WIN_INDEX[outcome] : 4;
    var endDeg = spinEndRotation(winIndex);

    wheel.style.transform = 'rotate(0deg)';

    var done = false;
    function finishSpin() {
      if (done) {
        return;
      }
      done = true;
      wheel.style.transform = 'rotate(' + endDeg + 'deg)';
      window.setTimeout(reveal, PAUSE_AFTER_STOP_MS);
    }

    window.requestAnimationFrame(function () {
      var anim = wheel.animate(
        [
          { transform: 'rotate(0deg)' },
          { transform: 'rotate(' + endDeg + 'deg)' },
        ],
        {
          duration: SPIN_MS,
          easing: 'cubic-bezier(0.08, 0.82, 0.12, 1)',
          fill: 'forwards',
        },
      );
      anim.onfinish = finishSpin;
      anim.oncancel = finishSpin;
      window.setTimeout(finishSpin, SPIN_MS + 200);
    });
  }

  function boot() {
    var live = document.getElementById('play-live');
    if (live) {
      initRoulette(live);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

  window.initPlayQ10Roulette = initRoulette;
})();
