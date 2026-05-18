/**
 * Inclinaison ±30° comme les portraits du pool (game-compose.js).
 * Repasser initPlayTeamTilt(racine) après mise à jour du fragment #play-live.
 */
(function () {
  'use strict';

  var reduceMotion = false;
  try {
    reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  } catch (e) {
    /* ignore */
  }

  var timers = new WeakMap();

  function randomTiltDelayMs() {
    return Math.round(500 + Math.random() * 1500);
  }

  function stopTilt(card) {
    var t = timers.get(card);
    if (t) {
      clearTimeout(t);
      timers.delete(card);
    }
    card.classList.remove(
      'play-photo-wrap--tilt-left',
      'play-photo-wrap--tilt-right',
    );
    card.style.removeProperty('--play-pool-tilt-duration');
  }

  function startTilt(card) {
    stopTilt(card);
    var initialLeft = Math.random() < 0.5;
    card.classList.add(
      initialLeft ? 'play-photo-wrap--tilt-left' : 'play-photo-wrap--tilt-right',
    );

    function tick() {
      var durationMs = randomTiltDelayMs();
      card.style.setProperty(
        '--play-pool-tilt-duration',
        durationMs / 1000 + 's',
      );
      var isLeft = card.classList.contains('play-photo-wrap--tilt-left');
      card.classList.toggle('play-photo-wrap--tilt-left', !isLeft);
      card.classList.toggle('play-photo-wrap--tilt-right', isLeft);
      timers.set(card, setTimeout(tick, durationMs));
    }

    timers.set(card, setTimeout(tick, 0));
  }

  function initPlayTeamTilt(root) {
    if (reduceMotion) return;
    root = root || document;
    var cards = root.querySelectorAll('[data-play-tilt]');
    for (var i = 0; i < cards.length; i++) {
      startTilt(cards[i]);
    }
  }

  window.initPlayTeamTilt = initPlayTeamTilt;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      initPlayTeamTilt(document.getElementById('play-live') || document);
    });
  } else {
    initPlayTeamTilt(document.getElementById('play-live') || document);
  }
})();
