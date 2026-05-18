/**
 * Après échange du fragment play : pop sur les métriques, effets cartoon,
 * ajustement visuel Thomas (nudge du chiffre à l’incrémentation).
 */
(function () {
  'use strict';

  var lastSnap = null;

  function prefersReducedMotion() {
    try {
      return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    } catch (e) {
      return false;
    }
  }

  function parseSnapshot(root) {
    if (!root) return null;
    var el = root.querySelector('#play-drink-snapshot');
    if (!el || !el.textContent) return null;
    try {
      return JSON.parse(el.textContent);
    } catch (err) {
      return null;
    }
  }

  function toInt(snap, key) {
    if (!snap || snap[key] == null) return 0;
    return parseInt(String(snap[key]), 10) || 0;
  }

  function peekSnapshot(root) {
    return parseSnapshot(root) || lastSnap;
  }

  function bumpMetric(root, selector) {
    var node = root.querySelector(selector);
    if (!node || prefersReducedMotion()) return;
    node.classList.add('play-drink-metric--pop');
    node.addEventListener(
      'animationend',
      function onEnd() {
        node.removeEventListener('animationend', onEnd);
        node.classList.remove('play-drink-metric--pop');
      },
      { once: true },
    );
  }

  function thomasNudgeMetric(root, selector) {
    var node = root.querySelector(selector);
    if (!node || prefersReducedMotion()) return;
    node.classList.add('play-drink-metric--thomas-nudge');
    node.addEventListener(
      'animationend',
      function onEnd() {
        node.removeEventListener('animationend', onEnd);
        node.classList.remove('play-drink-metric--thomas-nudge');
      },
      { once: true },
    );
  }

  function cartoonHitTeamPhotos(live, side) {
    if (prefersReducedMotion()) return;
    var sel =
      side === 'a'
        ? '.play-side--a .play-photo-wrap'
        : '.play-side--b .play-photo-wrap';
    var wraps = live.querySelectorAll(sel);
    for (var i = 0; i < wraps.length; i++) {
      (function (wrap) {
        wrap.classList.add('play-cartoon-hit');
        window.setTimeout(function () {
          wrap.classList.remove('play-cartoon-hit');
        }, 780);
      })(wraps[i]);
    }
  }

  function cartoonHitThomasPhoto(live) {
    if (prefersReducedMotion()) return;
    var th = live.querySelector('.play-thomas-strip .play-top-photo');
    if (!th) return;
    th.classList.add('play-cartoon-hit');
    window.setTimeout(function () {
      th.classList.remove('play-cartoon-hit');
    }, 780);
  }

  function afterSwap(live, prevSnap) {
    var nextSnap = parseSnapshot(live);
    if (!nextSnap) return;

    var p = prevSnap != null ? prevSnap : lastSnap;
    if (p == null) {
      lastSnap = nextSnap;
      return;
    }

    if (toInt(nextSnap, 'a_g') > toInt(p, 'a_g')) {
      bumpMetric(live, '[data-drink-metric="a-g"]');
      cartoonHitTeamPhotos(live, 'a');
    }
    if (toInt(nextSnap, 'a_s') > toInt(p, 'a_s')) {
      bumpMetric(live, '[data-drink-metric="a-s"]');
      cartoonHitTeamPhotos(live, 'a');
    }
    if (toInt(nextSnap, 'b_g') > toInt(p, 'b_g')) {
      bumpMetric(live, '[data-drink-metric="b-g"]');
      cartoonHitTeamPhotos(live, 'b');
    }
    if (toInt(nextSnap, 'b_s') > toInt(p, 'b_s')) {
      bumpMetric(live, '[data-drink-metric="b-s"]');
      cartoonHitTeamPhotos(live, 'b');
    }
    if (toInt(nextSnap, 't_g') > toInt(p, 't_g')) {
      bumpMetric(live, '[data-drink-metric="t-g"]');
      thomasNudgeMetric(live, '[data-drink-metric="t-g"]');
      cartoonHitThomasPhoto(live);
    }
    if (toInt(nextSnap, 't_s') > toInt(p, 't_s')) {
      bumpMetric(live, '[data-drink-metric="t-s"]');
      thomasNudgeMetric(live, '[data-drink-metric="t-s"]');
      cartoonHitThomasPhoto(live);
    }

    lastSnap = nextSnap;
  }

  function initFromDom() {
    var live = document.getElementById('play-live');
    var s = parseSnapshot(live);
    if (s) lastSnap = s;
  }

  window.playDrinkPeekSnapshot = peekSnapshot;
  window.playDrinkAfterSwap = afterSwap;
  window.playDrinkInitSnapshot = initFromDom;

  document.addEventListener('DOMContentLoaded', initFromDom);
})();
