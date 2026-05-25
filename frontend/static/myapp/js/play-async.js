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

  function parseFragment(html) {
    var tpl = document.createElement('template');
    tpl.innerHTML = html.trim();
    return tpl.content;
  }

  function syncPlayMessages(live, frag) {
    var newMessages = frag.querySelector('.play-messages');
    var oldMessages = live.querySelector('.play-messages');
    if (newMessages) {
      var imported = document.importNode(newMessages, true);
      if (oldMessages) {
        oldMessages.replaceWith(imported);
      } else {
        live.insertBefore(imported, live.firstChild);
      }
    } else if (oldMessages) {
      oldMessages.remove();
    }
  }

  function syncPlaySnapshot(live, frag) {
    var newSnap = frag.querySelector('#play-drink-snapshot');
    var oldSnap = live.querySelector('#play-drink-snapshot');
    if (newSnap && oldSnap) {
      oldSnap.textContent = newSnap.textContent;
    } else if (newSnap && !oldSnap) {
      live.insertBefore(document.importNode(newSnap, true), live.firstChild);
    }
  }

  function patchDrinkMetric(oldMetric, newMetric) {
    if (!oldMetric || !newMetric) {
      return;
    }
    oldMetric.className = newMetric.className;
    var oldNum = oldMetric.querySelector('.play-drink-metric__num');
    var newNum = newMetric.querySelector('.play-drink-metric__num');
    if (oldNum && newNum) {
      oldNum.textContent = newNum.textContent;
    }
    var oldLbl = oldMetric.querySelector('.play-drink-metric__lbl');
    var newLbl = newMetric.querySelector('.play-drink-metric__lbl');
    if (oldLbl && newLbl) {
      oldLbl.textContent = newLbl.textContent;
    }
  }

  function patchThomasStrip(live, frag) {
    var oldStrip = live.querySelector('.play-thomas-strip');
    var newStrip = frag.querySelector('.play-thomas-strip');
    if (!oldStrip || !newStrip) {
      return;
    }
    var aria = newStrip.getAttribute('aria-label');
    if (aria) {
      oldStrip.setAttribute('aria-label', aria);
    }
    patchDrinkMetric(
      oldStrip.querySelector('[data-drink-metric="t-g"]'),
      newStrip.querySelector('[data-drink-metric="t-g"]'),
    );
    patchDrinkMetric(
      oldStrip.querySelector('[data-drink-metric="t-s"]'),
      newStrip.querySelector('[data-drink-metric="t-s"]'),
    );
  }

  function patchTeamDrink(live, frag, side) {
    var sel = '.play-team-drink--' + side;
    var oldDrink = live.querySelector(sel);
    var newDrink = frag.querySelector(sel);
    if (!oldDrink || !newDrink) {
      return;
    }
    var aria = newDrink.getAttribute('aria-label');
    if (aria) {
      oldDrink.setAttribute('aria-label', aria);
    }
    var oldScore = oldDrink.querySelector('.play-team-drink__score');
    var newScore = newDrink.querySelector('.play-team-drink__score');
    if (oldScore && newScore) {
      oldScore.textContent = newScore.textContent;
    }
    patchDrinkMetric(
      oldDrink.querySelector('[data-drink-metric="' + side + '-g"]'),
      newDrink.querySelector('[data-drink-metric="' + side + '-g"]'),
    );
    patchDrinkMetric(
      oldDrink.querySelector('[data-drink-metric="' + side + '-s"]'),
      newDrink.querySelector('[data-drink-metric="' + side + '-s"]'),
    );
  }

  function patchTeamColumn(live, frag, side) {
    var oldCol = live.querySelector('[data-play-column="' + side + '"]');
    var newCol = frag.querySelector('[data-play-column="' + side + '"]');
    if (!oldCol || !newCol) {
      return false;
    }

    oldCol.className = newCol.className;
    if (newCol.hasAttribute('aria-current')) {
      oldCol.setAttribute('aria-current', newCol.getAttribute('aria-current'));
    } else {
      oldCol.removeAttribute('aria-current');
    }

    var oldProgress = oldCol.querySelector('.play-column-progress');
    var newProgress = newCol.querySelector('.play-column-progress');
    if (oldProgress && newProgress) {
      oldProgress.innerHTML = newProgress.innerHTML;
    }

    var oldBadge = oldCol.querySelector('.play-column-badge-slot');
    var newBadge = newCol.querySelector('.play-column-badge-slot');
    if (oldBadge && newBadge) {
      oldBadge.innerHTML = newBadge.innerHTML;
      oldBadge.setAttribute(
        'aria-hidden',
        newBadge.getAttribute('aria-hidden') || 'true',
      );
    }

    patchTeamDrink(live, frag, side);

    var oldAside = oldCol.querySelector('[data-play-team-aside="' + side + '"]');
    var newAside = newCol.querySelector('[data-play-team-aside="' + side + '"]');
    if (oldAside && newAside) {
      oldAside.className = newAside.className;
      var oldName = oldAside.querySelector('.play-team-name');
      var newName = newAside.querySelector('.play-team-name');
      if (oldName && newName) {
        oldName.textContent = newName.textContent;
      }
    }

    return true;
  }

  function patchPlayCenter(live, frag) {
    var newCenter = frag.querySelector('main.play-center');
    var oldCenter = live.querySelector('main.play-center');
    if (!newCenter) {
      return false;
    }
    if (!oldCenter) {
      var layout = live.querySelector('.play-layout');
      if (!layout) {
        return false;
      }
      var teamB = layout.querySelector('[data-play-column="b"]');
      var imported = document.importNode(newCenter, true);
      if (teamB) {
        layout.insertBefore(imported, teamB);
      } else {
        layout.appendChild(imported);
      }
      return true;
    }
    oldCenter.className = newCenter.className;
    oldCenter.innerHTML = newCenter.innerHTML;
    return true;
  }

  function applyPlayTitle(response) {
    var title = response.headers.get('X-Play-Title');
    if (title) {
      document.title = title;
    }
  }

  function swapPlayCenter(live, html, response) {
    var frag = parseFragment(html);
    var newCenter = frag.querySelector('main.play-center');
    var oldCenter = live.querySelector('main.play-center');
    if (!newCenter || !oldCenter) {
      swapPlayLive(live, html, response);
      return;
    }
    syncPlayMessages(live, frag);
    oldCenter.className = newCenter.className;
    oldCenter.innerHTML = newCenter.innerHTML;
    applyPlayTitle(response);
  }

  function patchPlayFromResponse(live, html, response) {
    var prevSnap =
      typeof window.playDrinkPeekSnapshot === 'function'
        ? window.playDrinkPeekSnapshot(live)
        : null;
    var frag = parseFragment(html);

    if (frag.querySelector('.play-q10-overlay')) {
      swapPlayLive(live, html, response);
      return;
    }

    syncPlayMessages(live, frag);
    syncPlaySnapshot(live, frag);
    patchThomasStrip(live, frag);

    var patchedA = patchTeamColumn(live, frag, 'a');
    var patchedB = patchTeamColumn(live, frag, 'b');
    var patchedCenter = patchPlayCenter(live, frag);

    if (!patchedA || !patchedB || !patchedCenter) {
      swapPlayLive(live, html, response);
      return;
    }

    live.querySelectorAll('.play-q10-overlay').forEach(function (el) {
      el.remove();
    });

    applyPlayTitle(response);

    if (typeof window.playDrinkAfterSwap === 'function') {
      window.playDrinkAfterSwap(live, prevSnap);
    }
  }

  function resolveSwapScope(response, fd) {
    var headerScope = response.headers.get('X-Play-Swap-Scope');
    if (headerScope === 'center' || headerScope === 'patch' || headerScope === 'full') {
      return headerScope;
    }
    if (fd.get('action') === 'choose_mode') {
      return 'center';
    }
    if (fd.get('action') === 'q10_roulette_ack') {
      return 'full';
    }
    if (fd.get('action') === 'q10_anecdote_split') {
      return 'full';
    }
    if (fd.get('action') === 'answer') {
      return 'patch';
    }
    return 'full';
  }

  function swapPlayLive(live, html, response) {
    var prevSnap =
      typeof window.playDrinkPeekSnapshot === 'function'
        ? window.playDrinkPeekSnapshot(live)
        : null;
    live.innerHTML = html;
    applyPlayTitle(response);
    if (typeof window.playDrinkAfterSwap === 'function') {
      window.playDrinkAfterSwap(live, prevSnap);
    }
    if (typeof window.initPlayTeamTilt === 'function') {
      window.initPlayTeamTilt(live);
    }
    if (typeof window.initPlayQ10Roulette === 'function') {
      window.initPlayQ10Roulette(live);
    }
  }

  function applyPlaySwap(live, html, response, fd) {
    var scope = resolveSwapScope(response, fd);
    if (scope === 'center') {
      swapPlayCenter(live, html, response);
    } else if (scope === 'patch') {
      patchPlayFromResponse(live, html, response);
    } else {
      swapPlayLive(live, html, response);
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
              applyPlaySwap(live, html, response, fd);
            }, answerFlashDelayMs());
            return null;
          }

          applyPlaySwap(live, html, response, fd);
          return null;
        });
      })
      .catch(function () {
        window.location.reload();
      });
  });
})();
