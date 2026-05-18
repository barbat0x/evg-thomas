/**
 * Envoie les formulaires de l’écran play en fetch + fragment HTML (template Django).
 */
(function () {
  'use strict';

  function getCookie(name) {
    var value = '; ' + document.cookie;
    var parts = value.split('; ' + name + '=');
    if (parts.length === 2) {
      return parts.pop().split(';').shift();
    }
    return '';
  }

  function getCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.getAttribute('content')) {
      return meta.getAttribute('content');
    }
    return getCookie('csrftoken');
  }

  /**
   * URL de soumission (ne pas utiliser form.action : les champs name="action"
   * écrasent la propriété et deviennent [object HTMLInputElement]).
   */
  function resolveFormAction(form) {
    var raw = form.getAttribute('action');
    if (!raw || !raw.trim()) {
      return window.location.pathname + window.location.search;
    }
    return new URL(raw.trim(), window.location.href).href;
  }

  function swapPlayLive(live, html, response) {
    var prevSnap =
      typeof window.playDrinkPeekSnapshot === 'function'
        ? window.playDrinkPeekSnapshot(live)
        : null;
    live.innerHTML = html;
    var title = response.headers.get('X-Play-Title');
    if (title) {
      document.title = title;
    }
    if (typeof window.playDrinkAfterSwap === 'function') {
      window.playDrinkAfterSwap(live, prevSnap);
    }
    if (typeof window.initPlayTeamTilt === 'function') {
      window.initPlayTeamTilt(live);
    }
  }

  function answerFlashDelayMs() {
    if (
      window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    ) {
      return 260;
    }
    return 760;
  }

  document.body.addEventListener('submit', function (ev) {
    var form = ev.target;
    if (!(form instanceof HTMLFormElement)) return;
    if (form.method.toLowerCase() !== 'post') return;
    var live = document.getElementById('play-live');
    if (!live || !live.contains(form)) return;
    if (live.getAttribute('data-play-enhanced') !== '1') return;

    ev.preventDefault();

    var token = getCsrfToken();
    /* Inclure le bouton cliqué (ex. name=cash_verdict), absent de new FormData(form) seul. */
    var sub = ev.submitter;
    var fd =
      sub instanceof HTMLButtonElement || sub instanceof HTMLInputElement
        ? new FormData(form, sub)
        : new FormData(form);

    fetch(resolveFormAction(form), {
      method: 'POST',
      body: fd,
      headers: {
        'X-CSRFToken': token || '',
        'X-Play-Partial': '1',
      },
      credentials: 'same-origin',
    })
      .then(function (response) {
        var ct = response.headers.get('content-type') || '';
        if (ct.indexOf('application/json') !== -1) {
          return response.json().then(function (data) {
            if (data.redirect) {
              window.location.href = data.redirect;
              return null;
            }
            return null;
          });
        }
        if (!response.ok) {
          window.location.reload();
          return null;
        }
        return response.text().then(function (html) {
          var verdict = response.headers.get('X-Play-Answer-Verdict');
          var isAnswer = fd.get('action') === 'answer';
          var canFlash =
            isAnswer &&
            (verdict === 'correct' || verdict === 'wrong') &&
            sub instanceof HTMLButtonElement;

          if (canFlash) {
            live
              .querySelectorAll('main.play-center button[type="submit"]')
              .forEach(function (b) {
                b.disabled = true;
              });
            sub.classList.add(
              verdict === 'correct'
                ? 'play-answer-flash--correct'
                : 'play-answer-flash--wrong',
            );
            window.setTimeout(function () {
              swapPlayLive(live, html, response);
            }, answerFlashDelayMs());
            return null;
          }

          swapPlayLive(live, html, response);
          return null;
        });
      })
      .catch(function () {
        window.location.reload();
      });
  });
})();
