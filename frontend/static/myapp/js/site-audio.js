(function () {
  'use strict';

  var STORAGE_KEY = 'evgThomasSiteAudio';
  var PLAYBACK_KEY = 'evgThomasSiteAudioPlayback';
  var DEFAULT_VOLUME = 0.6;
  var PLAYBACK_SAVE_MS = 1500;

  var root = document.getElementById('site-audio');
  var audio = document.getElementById('site-audio-el');
  var muteBtn = document.getElementById('site-audio-mute');
  var volumeInput = document.getElementById('site-audio-volume');
  if (!root || !audio || !muteBtn || !volumeInput) {
    return;
  }

  var iconOn = muteBtn.querySelector('.site-audio__icon--on');
  var iconOff = muteBtn.querySelector('.site-audio__icon--off');

  function readPrefs() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        return { volume: DEFAULT_VOLUME, muted: false };
      }
      var data = JSON.parse(raw);
      var vol = Number(data.volume);
      if (!Number.isFinite(vol) || vol < 0 || vol > 1) {
        vol = DEFAULT_VOLUME;
      }
      return { volume: vol, muted: Boolean(data.muted) };
    } catch (_err) {
      return { volume: DEFAULT_VOLUME, muted: false };
    }
  }

  function writePrefs() {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ volume: audio.volume, muted: audio.muted })
      );
    } catch (_err) {
      /* quota / private mode */
    }
  }

  function readPlayback() {
    try {
      var raw = sessionStorage.getItem(PLAYBACK_KEY);
      if (!raw) {
        return null;
      }
      var data = JSON.parse(raw);
      var t = Number(data.t);
      if (!Number.isFinite(t) || t < 0) {
        return null;
      }
      return { t: t, wasPlaying: Boolean(data.wasPlaying) };
    } catch (_err) {
      return null;
    }
  }

  function savePlayback() {
    try {
      sessionStorage.setItem(
        PLAYBACK_KEY,
        JSON.stringify({
          t: audio.currentTime,
          wasPlaying: !audio.paused && !audio.muted,
        })
      );
    } catch (_err) {
      /* quota / private mode */
    }
  }

  function seekToSavedTime(targetTime) {
    if (!Number.isFinite(targetTime) || targetTime < 0) {
      return;
    }
    try {
      var duration = audio.duration;
      if (Number.isFinite(duration) && duration > 0) {
        audio.currentTime = targetTime % duration;
      } else {
        audio.currentTime = targetTime;
      }
    } catch (_err) {
      /* seek before metadata */
    }
  }

  function restorePlaybackThenStart() {
    var snap = readPlayback();
    if (!snap) {
      tryPlay();
      return;
    }

    function applySeekAndMaybePlay() {
      seekToSavedTime(snap.t);
      if (snap.wasPlaying && !audio.muted) {
        tryPlay();
      }
    }

    if (audio.readyState >= 1) {
      applySeekAndMaybePlay();
    } else {
      audio.addEventListener('loadedmetadata', applySeekAndMaybePlay, {
        once: true,
      });
    }
  }

  function setExpanded(open) {
    root.classList.toggle('site-audio--expanded', open);
    muteBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
  }

  function syncUi() {
    var pct = Math.round(audio.volume * 100);
    volumeInput.value = String(pct);
    volumeInput.setAttribute('aria-valuenow', String(pct));
    muteBtn.setAttribute('aria-pressed', audio.muted ? 'true' : 'false');
    muteBtn.setAttribute(
      'aria-label',
      audio.muted ? 'Activer le son' : 'Couper le son'
    );
    root.classList.toggle('site-audio--muted', audio.muted);
    if (iconOn && iconOff) {
      iconOn.hidden = audio.muted;
      iconOff.hidden = !audio.muted;
    }
  }

  function applyVolume(fraction) {
    var v = Math.min(1, Math.max(0, fraction));
    audio.volume = v;
    syncUi();
    writePrefs();
  }

  var prefs = readPrefs();
  audio.volume = prefs.volume;
  audio.muted = prefs.muted;
  syncUi();

  volumeInput.addEventListener('input', function () {
    var pct = Number(volumeInput.value);
    if (!Number.isFinite(pct)) {
      return;
    }
    audio.muted = false;
    applyVolume(pct / 100);
  });

  muteBtn.addEventListener('click', function () {
    audio.muted = !audio.muted;
    syncUi();
    writePrefs();
    savePlayback();
    if (!audio.muted) {
      tryPlay();
    }
  });

  muteBtn.setAttribute('aria-expanded', 'false');
  muteBtn.setAttribute('aria-haspopup', 'true');
  muteBtn.setAttribute(
    'title',
    'Couper / activer le son (maintenir pour le volume)'
  );

  var longPressId = null;

  muteBtn.addEventListener('pointerdown', function (event) {
    if (event.pointerType === 'mouse') {
      return;
    }
    longPressId = window.setTimeout(function () {
      longPressId = null;
      setExpanded(true);
      volumeInput.focus();
    }, 420);
  });

  function cancelLongPress() {
    if (longPressId !== null) {
      window.clearTimeout(longPressId);
      longPressId = null;
    }
  }

  muteBtn.addEventListener('pointerup', cancelLongPress);
  muteBtn.addEventListener('pointercancel', cancelLongPress);
  muteBtn.addEventListener('pointerleave', cancelLongPress);

  document.addEventListener('pointerdown', function (event) {
    if (!root.contains(event.target)) {
      setExpanded(false);
    }
  });

  volumeInput.addEventListener('blur', function () {
    window.setTimeout(function () {
      if (!root.contains(document.activeElement)) {
        setExpanded(false);
      }
    }, 0);
  });

  function clearNeedsGesture() {
    root.classList.remove('site-audio--needs-gesture');
  }

  function tryPlay() {
    var promise = audio.play();
    if (!promise || typeof promise.then !== 'function') {
      clearNeedsGesture();
      return;
    }
    promise
      .then(function () {
        clearNeedsGesture();
      })
      .catch(function () {
        root.classList.add('site-audio--needs-gesture');
      });
  }

  function unlockFromGesture() {
    clearNeedsGesture();
    if (audio.paused && !audio.muted) {
      tryPlay();
    }
  }

  document.addEventListener('pointerdown', unlockFromGesture, { once: true });
  document.addEventListener('keydown', unlockFromGesture, { once: true });

  var lastPlaybackSave = 0;
  audio.addEventListener('timeupdate', function () {
    var now = Date.now();
    if (now - lastPlaybackSave < PLAYBACK_SAVE_MS) {
      return;
    }
    lastPlaybackSave = now;
    savePlayback();
  });

  audio.addEventListener('play', savePlayback);
  audio.addEventListener('pause', savePlayback);

  window.addEventListener('pagehide', savePlayback);

  restorePlaybackThenStart();
})();
