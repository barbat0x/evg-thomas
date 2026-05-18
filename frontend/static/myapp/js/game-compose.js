/**
 * Glisser-déposer des cartes participant (souris / tactile) avec fantôme sous le pointeur.
 */
(function () {
  'use strict';

  var form = document.querySelector('[data-compose-form]');
  if (!form) return;

  var teamAInput = document.getElementById('team-a-order');
  var teamBInput = document.getElementById('team-b-order');
  var teamNameA = document.getElementById('id_team_a_name');
  var teamNameB = document.getElementById('id_team_b_name');
  if (!teamAInput || !teamBInput) return;

  var formSubmitting = false;

  var activeCard = null;
  var dragGhost = null;
  var dragOffsetX = 0;
  var dragOffsetY = 0;
  var lastClientX = 0;
  var lastClientY = 0;
  var poolTiltTimers = new WeakMap();

  function qsZones(sel) {
    return Array.prototype.slice.call(document.querySelectorAll(sel));
  }

  function randomTiltDelayMs() {
    return Math.round(500 + Math.random() * 1500);
  }

  function stopPoolTilt(card) {
    var t = poolTiltTimers.get(card);
    if (t) {
      clearTimeout(t);
      poolTiltTimers.delete(card);
    }
    card.classList.remove(
      'compose-card--pool-tilt-left',
      'compose-card--pool-tilt-right',
    );
    card.style.removeProperty('--pool-tilt-duration');
  }

  function startPoolTilt(card) {
    stopPoolTilt(card);
    if (!card.closest('[data-compose-zone="pool"]')) return;

    var initialLeft = Math.random() < 0.5;
    card.classList.add(
      initialLeft ? 'compose-card--pool-tilt-left' : 'compose-card--pool-tilt-right',
    );

    function tick() {
      if (!card.closest('[data-compose-zone="pool"]')) {
        stopPoolTilt(card);
        return;
      }
      var durationMs = randomTiltDelayMs();
      card.style.setProperty('--pool-tilt-duration', durationMs / 1000 + 's');
      var isLeft = card.classList.contains('compose-card--pool-tilt-left');
      card.classList.toggle('compose-card--pool-tilt-left', !isLeft);
      card.classList.toggle('compose-card--pool-tilt-right', isLeft);
      poolTiltTimers.set(card, setTimeout(tick, durationMs));
    }

    poolTiltTimers.set(card, setTimeout(tick, 0));
  }

  function updatePoolTiltForCard(card) {
    if (!card) return;
    if (card.closest('[data-compose-zone="pool"]')) {
      startPoolTilt(card);
    } else {
      stopPoolTilt(card);
    }
  }

  function syncOrders() {
    var za = document.querySelector('[data-compose-zone="team-a"]');
    var zb = document.querySelector('[data-compose-zone="team-b"]');
    if (!za || !zb) return;
    function ids(zone) {
      return Array.prototype.map
        .call(zone.querySelectorAll('.compose-card'), function (c) {
          return c.getAttribute('data-participant-id');
        })
        .filter(Boolean)
        .join(',');
    }
    teamAInput.value = ids(za);
    teamBInput.value = ids(zb);
  }

  function stripGhostIds(root) {
    var withId = root.querySelectorAll('[id]');
    for (var i = 0; i < withId.length; i++) {
      withId[i].removeAttribute('id');
    }
    var labels = root.querySelectorAll('label[for]');
    for (var j = 0; j < labels.length; j++) {
      labels[j].removeAttribute('for');
    }
  }

  function moveGhost(clientX, clientY) {
    if (!dragGhost) return;
    var x = clientX - dragOffsetX;
    var y = clientY - dragOffsetY;
    dragGhost.style.transform = 'translate(' + x + 'px,' + y + 'px)';
  }

  function findDropZone(clientX, clientY) {
    var stack = document.elementsFromPoint(clientX, clientY);
    if (!stack || !stack.length) return null;
    for (var i = 0; i < stack.length; i++) {
      var inner = stack[i].closest('.compose-zone-inner[data-compose-zone]');
      if (inner && form.contains(inner)) return inner;
    }
    return null;
  }

  /** Garde une « case » vide dans le pool pour ne pas faire bouger les cartes restantes. */
  function insertPoolPlaceholderBeforeCard(card) {
    var pool = card.closest('[data-compose-zone="pool"]');
    if (!pool || card.parentNode !== pool) return;
    var ph = document.createElement('div');
    ph.className = 'compose-pool-slot-placeholder';
    if (card.classList.contains('compose-card--julien-b')) {
      ph.classList.add('compose-pool-slot-placeholder--julien-b');
    }
    ph.setAttribute('aria-hidden', 'true');
    pool.insertBefore(ph, card);
  }

  function removeNearestPoolPlaceholder(poolZone, clientX, clientY) {
    var placeholders = poolZone.querySelectorAll('.compose-pool-slot-placeholder');
    if (!placeholders.length) return;
    var best = null;
    var bestDist = Infinity;
    for (var i = 0; i < placeholders.length; i++) {
      var r = placeholders[i].getBoundingClientRect();
      var cx = r.left + r.width / 2;
      var cy = r.top + r.height / 2;
      var d = (cx - clientX) * (cx - clientX) + (cy - clientY) * (cy - clientY);
      if (d < bestDist) {
        bestDist = d;
        best = placeholders[i];
      }
    }
    if (best) best.remove();
  }

  function insertCardInZone(zone, clientX, clientY) {
    if (!activeCard || !zone) return;
    var cards = zone.querySelectorAll('.compose-card');
    var targetCard = null;
    for (var j = 0; j < cards.length; j++) {
      if (cards[j] === activeCard) continue;
      var r = cards[j].getBoundingClientRect();
      if (
        clientX >= r.left &&
        clientX <= r.right &&
        clientY >= r.top &&
        clientY <= r.bottom
      ) {
        targetCard = cards[j];
        break;
      }
    }
    if (targetCard) {
      var tr = targetCard.getBoundingClientRect();
      var mid = tr.top + tr.height / 2;
      if (clientY < mid) {
        zone.insertBefore(activeCard, targetCard);
      } else if (targetCard.nextSibling) {
        zone.insertBefore(activeCard, targetCard.nextSibling);
      } else {
        zone.appendChild(activeCard);
      }
    } else {
      zone.appendChild(activeCard);
    }
  }

  function teardownDragUI() {
    document.removeEventListener('pointermove', onPointerMove);
    document.removeEventListener('pointerup', onPointerUp);
    document.removeEventListener('pointercancel', onPointerUp);
    document.body.classList.remove('compose-is-dragging');
    if (dragGhost && dragGhost.parentNode) {
      dragGhost.parentNode.removeChild(dragGhost);
    }
    dragGhost = null;
  }

  function onPointerUp(e) {
    if (!activeCard) return;

    var clientX = e.clientX;
    var clientY = e.clientY;
    if (e.type === 'pointercancel') {
      clientX = lastClientX;
      clientY = lastClientY;
    }

    var card = activeCard;
    var sourcePool = !!card.closest('[data-compose-zone="pool"]');
    var zone = findDropZone(clientX, clientY);
    if (zone) {
      var zid = zone.getAttribute('data-compose-zone');
      if (sourcePool && zid !== 'pool') {
        insertPoolPlaceholderBeforeCard(card);
      } else if (!sourcePool && zid === 'pool') {
        removeNearestPoolPlaceholder(zone, clientX, clientY);
      }
      insertCardInZone(zone, clientX, clientY);
    }

    activeCard = null;
    teardownDragUI();

    card.classList.remove('compose-card--dragging-source');
    card.classList.remove('compose-card--dragging');

    syncOrders();
    updatePoolTiltForCard(card);
    requestAnimationFrame(updateComposeReadyUI);
  }

  function onPointerMove(e) {
    if (!activeCard || !dragGhost) return;
    e.preventDefault();
    lastClientX = e.clientX;
    lastClientY = e.clientY;
    moveGhost(lastClientX, lastClientY);
  }

  function onPointerDown(e) {
    if (activeCard) return;
    if (e.pointerType === 'mouse' && e.button !== 0) return;
    if (e.target.closest('input, textarea, button, select')) return;
    var card = e.target.closest('.compose-card');
    if (!card || !form.contains(card)) return;

    e.preventDefault();
    activeCard = card;
    var rect = card.getBoundingClientRect();
    dragOffsetX = e.clientX - rect.left;
    dragOffsetY = e.clientY - rect.top;
    lastClientX = e.clientX;
    lastClientY = e.clientY;

    dragGhost = card.cloneNode(true);
    dragGhost.classList.add('compose-drag-ghost');
    dragGhost.classList.remove(
      'compose-card--dragging-source',
      'compose-card--dragging',
    );
    var fromPool = !!card.closest('[data-compose-zone="pool"]');
    if (fromPool) {
      dragGhost.classList.add('compose-drag-ghost--from-pool');
    } else {
      dragGhost.classList.add('compose-drag-ghost--from-team');
      dragGhost.classList.remove(
        'compose-card--pool-tilt-left',
        'compose-card--pool-tilt-right',
      );
    }
    dragGhost.setAttribute('aria-hidden', 'true');
    stripGhostIds(dragGhost);
    document.body.appendChild(dragGhost);
    dragGhost.style.position = 'fixed';
    dragGhost.style.left = '0';
    dragGhost.style.top = '0';
    dragGhost.style.width = 'auto';
    dragGhost.style.height = 'auto';
    dragGhost.style.pointerEvents = 'none';
    dragGhost.style.zIndex = '2147483647';
    dragGhost.style.margin = '0';
    moveGhost(lastClientX, lastClientY);

    stopPoolTilt(card);
    card.classList.add('compose-card--dragging-source');
    card.classList.add('compose-card--dragging');

    document.body.classList.add('compose-is-dragging');
    document.addEventListener('pointermove', onPointerMove, { passive: false });
    document.addEventListener('pointerup', onPointerUp);
    document.addEventListener('pointercancel', onPointerUp);
  }

  qsZones('.compose-card').forEach(function (card) {
    card.addEventListener('pointerdown', onPointerDown);
  });

  syncOrders();

  qsZones('.compose-card').forEach(updatePoolTiltForCard);

  function validateNamesInZone(zoneAttr) {
    var zone = document.querySelector('[data-compose-zone="' + zoneAttr + '"]');
    if (!zone) return { ok: true, firstBad: null };
    var inputs = zone.querySelectorAll('.compose-card-name');
    for (var k = 0; k < inputs.length; k++) {
      if (!inputs[k].value.trim()) {
        return { ok: false, firstBad: inputs[k] };
      }
    }
    return { ok: true, firstBad: null };
  }

  function isComposeReady() {
    var na = teamNameA ? teamNameA.value.trim() : '';
    var nb = teamNameB ? teamNameB.value.trim() : '';
    if (!na || !nb) return false;
    var pool = document.querySelector('[data-compose-zone="pool"]');
    if (pool && pool.querySelectorAll('.compose-card').length > 0) return false;
    if (!teamAInput.value.trim() || !teamBInput.value.trim()) return false;
    if (!validateNamesInZone('team-a').ok) return false;
    if (!validateNamesInZone('team-b').ok) return false;
    return true;
  }

  function removeAllPoolPlaceholders() {
    var pool = document.querySelector('[data-compose-zone="pool"]');
    if (!pool) return;
    var phs = pool.querySelectorAll('.compose-pool-slot-placeholder');
    for (var i = 0; i < phs.length; i++) {
      phs[i].remove();
    }
  }

  function updateComposeReadyUI() {
    var panel = document.getElementById('compose-ready-panel');
    var parti = document.getElementById('compose-cta-parti');
    if (!panel || !parti) return;
    syncOrders();
    var pool = document.querySelector('[data-compose-zone="pool"]');
    if (pool && pool.querySelectorAll('.compose-card').length === 0) {
      removeAllPoolPlaceholders();
    }
    var ready = isComposeReady() && activeCard === null;
    if (ready) {
      panel.hidden = false;
      panel.setAttribute('aria-hidden', 'false');
      parti.disabled = false;
      var ae = document.activeElement;
      var typingInField =
        ae &&
        form.contains(ae) &&
        (ae.tagName === 'INPUT' || ae.tagName === 'TEXTAREA' || ae.tagName === 'SELECT');
      if (!typingInField) {
        try {
          parti.focus({ preventScroll: true });
        } catch (err) {
          parti.focus();
        }
      }
    } else {
      panel.hidden = true;
      panel.setAttribute('aria-hidden', 'true');
      parti.disabled = true;
    }
  }

  form.addEventListener('submit', function (e) {
    syncOrders();
    if (!isComposeReady()) {
      e.preventDefault();
      return;
    }
    if (formSubmitting) {
      e.preventDefault();
      return;
    }
    formSubmitting = true;
    form.classList.add('compose-form--submitting');
    form.setAttribute('aria-busy', 'true');
  });

  if (teamNameA) {
    teamNameA.addEventListener('input', function () {
      requestAnimationFrame(updateComposeReadyUI);
    });
  }
  if (teamNameB) {
    teamNameB.addEventListener('input', function () {
      requestAnimationFrame(updateComposeReadyUI);
    });
  }

  requestAnimationFrame(updateComposeReadyUI);
})();
