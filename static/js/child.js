/**
 * Bipinho — Child TV Client Interface
 * Optimized for Android TV fullscreen display & Barcode Scanner keyboard emulation.
 * 100% Offline, no external dependencies.
 */

(function () {
  "use strict";

  // Elements
  const barcodeInput = document.getElementById("barcode-input");
  const starsContainer = document.getElementById("stars-container");
  const sessionCounter = document.getElementById("session-counter");
  const welcomeScreen = document.getElementById("welcome-screen");
  const mediaScreen = document.getElementById("media-screen");
  const pauseScreen = document.getElementById("pause-screen");
  const tvVideo = document.getElementById("tv-video");
  const tvImage = document.getElementById("tv-image");
  const metaOverlay = document.getElementById("meta-overlay");
  const metaTitle = document.getElementById("meta-title");
  const metaAuthorDate = document.getElementById("meta-author-date");
  const errorToast = document.getElementById("error-toast");
  const errorMessageText = document.getElementById("error-message-text");
  const unlockToast = document.getElementById("unlock-toast");
  const pauseProgressBar = document.getElementById("pause-progress-bar");
  const pauseTimeLabel = document.getElementById("pause-time-label");
  const pauseScanWarning = document.getElementById("pause-scan-warning");

  // State
  let readerProfile = {
    reader_type: "USB",
    max_interchar_ms: 100,
    terminator: "Enter",
    prefix_strip: "",
    suffix_strip: "",
    min_length: 3,
    timeout_ms: 500
  };

  let sessionState = {
    current_scans: 0,
    max_scans: 3,
    is_paused: false,
    remaining_pause_seconds: 0,
    total_pause_seconds: 1080,
    pause_minutes: 18,
    sound_enabled: true,
    title_display_seconds: 30
  };

  let activeItem = null;
  let pauseCountdownInterval = null;
  let metaTimeout = null;
  let errorTimeout = null;
  let warningTimeout = null;
  let keyBuffer = "";
  let lastCharTimestamp = 0;
  let bufferTimeout = null;
  let audioContext = null;

  // ----------------- AUDIO SYNTHESIZER (100% OFFLINE) ----------------- //

  function getAudioContext() {
    if (!audioContext) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        audioContext = new AudioCtx();
      }
    }
    if (audioContext && audioContext.state === "suspended") {
      audioContext.resume();
    }
    return audioContext;
  }

  function playSound(type) {
    if (!sessionState.sound_enabled) return;
    try {
      const ctx = getAudioContext();
      if (!ctx) return;

      const now = ctx.currentTime;
      if (type === "bip") {
        // Bright cheerful dual chime (C5 & G5)
        [523.25, 783.99].forEach((freq, idx) => {
          const osc = ctx.createOscillator();
          const gain = ctx.createGain();
          osc.type = "sine";
          osc.frequency.setValueAtTime(freq, now + idx * 0.05);
          gain.gain.setValueAtTime(0.2, now + idx * 0.05);
          gain.gain.exponentialRampToValueAtTime(0.001, now + idx * 0.05 + 0.35);
          osc.connect(gain);
          gain.connect(ctx.destination);
          osc.start(now + idx * 0.05);
          osc.stop(now + idx * 0.05 + 0.36);
        });
      } else if (type === "surprise") {
        // Cheery rising arpeggio (C5, E5, G5, C6)
        [523.25, 659.25, 783.99, 1046.50].forEach((freq, idx) => {
          const osc = ctx.createOscillator();
          const gain = ctx.createGain();
          osc.type = "triangle";
          osc.frequency.setValueAtTime(freq, now + idx * 0.08);
          gain.gain.setValueAtTime(0.25, now + idx * 0.08);
          gain.gain.exponentialRampToValueAtTime(0.001, now + idx * 0.08 + 0.3);
          osc.connect(gain);
          gain.connect(ctx.destination);
          osc.start(now + idx * 0.08);
          osc.stop(now + idx * 0.08 + 0.31);
        });
      } else if (type === "unlock") {
        // Magic sparkle chord (A4, C#5, E5, A5)
        [440.0, 554.37, 659.25, 880.0].forEach((freq) => {
          const osc = ctx.createOscillator();
          const gain = ctx.createGain();
          osc.type = "sine";
          osc.frequency.setValueAtTime(freq, now);
          gain.gain.setValueAtTime(0.18, now);
          gain.gain.exponentialRampToValueAtTime(0.001, now + 0.6);
          osc.connect(gain);
          gain.connect(ctx.destination);
          osc.start(now);
          osc.stop(now + 0.61);
        });
      } else if (type === "error") {
        // Gentle friendly boing
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(260, now);
        osc.frequency.exponentialRampToValueAtTime(160, now + 0.3);
        gain.gain.setValueAtTime(0.2, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now);
        osc.stop(now + 0.36);
      }
    } catch (e) {
      console.warn("Audio synth notice:", e);
    }
  }

  // ----------------- FOCUS GUARDIAN ----------------- //

  function ensureInputFocus() {
    if (document.activeElement !== barcodeInput) {
      barcodeInput.focus({ preventScroll: true });
    }
  }

  window.addEventListener("click", () => {
    ensureInputFocus();
    getAudioContext(); // Unlock audio on first interaction
  });

  window.addEventListener("blur", () => setTimeout(ensureInputFocus, 50));
  setInterval(ensureInputFocus, 350);

  // ----------------- BARCODE SCANNER HANDLER ----------------- //

  function processScannedBarcode(rawCode) {
    if (!rawCode) return;
    let code = rawCode.trim();

    // Strip prefix if configured
    if (readerProfile.prefix_strip && code.startsWith(readerProfile.prefix_strip)) {
      code = code.substring(readerProfile.prefix_strip.length);
    }

    // Strip suffix if configured
    if (readerProfile.suffix_strip && code.endsWith(readerProfile.suffix_strip)) {
      code = code.substring(0, code.length - readerProfile.suffix_strip.length);
    }

    code = code.trim();

    if (code.length < readerProfile.min_length) {
      console.log("Ignored short code:", code);
      return;
    }

    console.log("Processing valid barcode scan:", code);

    // Send to backend
    fetch("/api/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: code })
    })
      .then((res) => res.json())
      .then((data) => {
        handleScanResponse(data);
      })
      .catch((err) => {
        console.error("Scan error:", err);
      });
  }

  // Handle keystrokes globally (HID Keyboard emulation from scanner)
  window.addEventListener("keydown", (e) => {
    const now = Date.now();
    const isTerminator =
      (readerProfile.terminator === "Enter" && e.key === "Enter") ||
      (readerProfile.terminator === "Tab" && e.key === "Tab");

    // Inter-character timing check
    if (lastCharTimestamp > 0 && now - lastCharTimestamp > readerProfile.max_interchar_ms) {
      // Too slow for scanner reading: discard previous buffer
      keyBuffer = "";
    }
    lastCharTimestamp = now;

    if (isTerminator) {
      e.preventDefault();
      clearTimeout(bufferTimeout);
      const codeToSend = keyBuffer || barcodeInput.value;
      keyBuffer = "";
      barcodeInput.value = "";
      processScannedBarcode(codeToSend);
      return;
    }

    // Accumulate printable characters
    if (e.key.length === 1) {
      keyBuffer += e.key;

      // Incomplete scan timeout
      clearTimeout(bufferTimeout);
      bufferTimeout = setTimeout(() => {
        keyBuffer = "";
        barcodeInput.value = "";
      }, readerProfile.timeout_ms);
    }
  });

  // Also listen on input change/enter as fallback
  barcodeInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || (readerProfile.terminator === "Tab" && e.key === "Tab")) {
      e.preventDefault();
      const val = barcodeInput.value;
      barcodeInput.value = "";
      keyBuffer = "";
      processScannedBarcode(val);
    }
  });

  // ----------------- SCAN RESPONSE DISPATCHER ----------------- //

  function handleScanResponse(data) {
    if (!data) return;

    if (data.status === "success") {
      if (data.is_surprise) {
        playSound("surprise");
      } else {
        playSound("bip");
      }
      sessionState.current_scans = data.current_scans;
      sessionState.max_scans = data.max_scans;
      updateStarsUI();
      displayMediaItem(data.item, data.limit_reached);
    } else if (data.status === "parent_unlock") {
      playSound("unlock");
      showUnlockCelebration();
      endPauseScreen();
      sessionState.current_scans = 0;
      updateStarsUI();
      showWelcomeScreen();
    } else if (data.status === "in_pause") {
      playSound("error");
      showPauseScanWarning();
    } else if (data.status === "not_found") {
      playSound("error");
      showErrorToast(data.message || "Ops! Esse desenho não está aqui!");
    } else if (data.status === "debounce_ignored") {
      // Silently ignored to prevent accidental double-scans
      console.log("Debounce ignored.");
    }
  }

  // ----------------- VIEW SWITCHING & RENDERING ----------------- //

  function showWelcomeScreen() {
    welcomeScreen.classList.add("active");
    mediaScreen.classList.remove("active");
    pauseScreen.classList.remove("active");
    tvVideo.pause();
    tvVideo.src = "";
    tvImage.src = "";
    tvVideo.classList.remove("show");
    tvImage.classList.remove("show");
    metaOverlay.classList.remove("visible");
  }

  function displayMediaItem(item, limitReached) {
    if (!item) return;
    activeItem = item;

    welcomeScreen.classList.remove("active");
    pauseScreen.classList.remove("active");
    mediaScreen.classList.add("active");

    const mediaUrl = `/media/uploads/${item.filename}`;

    if (item.media_type === "video") {
      tvImage.classList.remove("show");
      tvVideo.classList.add("show");
      tvVideo.src = mediaUrl;
      tvVideo.load();
      tvVideo
        .play()
        .catch((err) => console.log("Video autoplay prevented:", err));

      // Video end handling
      tvVideo.onended = () => {
        if (limitReached) {
          triggerPauseTransition();
        }
      };
    } else {
      // Image
      tvVideo.pause();
      tvVideo.classList.remove("show");
      tvImage.classList.add("show");
      tvImage.src = mediaUrl;

      // For image: if limit reached, transition to pause after 45s of viewing
      if (limitReached) {
        setTimeout(() => {
          if (sessionState.current_scans >= sessionState.max_scans && !sessionState.is_paused) {
            triggerPauseTransition();
          }
        }, 45000);
      }
    }

    // Show Metadata Card (Title, Author, Date)
    metaTitle.textContent = item.title;
    metaAuthorDate.textContent = `${item.author} • ${formatDate(item.date)}`;
    metaOverlay.classList.add("visible");

    clearTimeout(metaTimeout);
    metaTimeout = setTimeout(() => {
      metaOverlay.classList.remove("visible");
    }, sessionState.title_display_seconds * 1000);
  }

  function triggerPauseTransition() {
    fetch("/api/session/trigger-pause", { method: "POST" })
      .then((res) => res.json())
      .then((data) => {
        startPauseScreen(data.remaining_seconds, data.total_pause_seconds);
      })
      .catch((err) => console.error("Pause trigger error:", err));
  }

  function startPauseScreen(remainingSec, totalSec) {
    sessionState.is_paused = true;
    sessionState.remaining_pause_seconds = remainingSec;
    sessionState.total_pause_seconds = totalSec || remainingSec;

    tvVideo.pause();
    metaOverlay.classList.remove("visible");
    welcomeScreen.classList.remove("active");
    mediaScreen.classList.remove("active");
    pauseScreen.classList.add("active");

    updatePauseTimerDisplay();

    clearInterval(pauseCountdownInterval);
    pauseCountdownInterval = setInterval(() => {
      sessionState.remaining_pause_seconds--;
      if (sessionState.remaining_pause_seconds <= 0) {
        clearInterval(pauseCountdownInterval);
        // Check with server if pause unlocked
        fetch("/api/session/status")
          .then((r) => r.json())
          .then((status) => {
            if (!status.is_paused) {
              endPauseScreen();
              sessionState.current_scans = 0;
              updateStarsUI();
              showWelcomeScreen();
            }
          });
      } else {
        updatePauseTimerDisplay();
      }
    }, 1000);
  }

  function endPauseScreen() {
    clearInterval(pauseCountdownInterval);
    sessionState.is_paused = false;
    sessionState.remaining_pause_seconds = 0;
    pauseScreen.classList.remove("active");
  }

  function updatePauseTimerDisplay() {
    const sec = Math.max(0, sessionState.remaining_pause_seconds);
    const total = sessionState.total_pause_seconds || 1080;
    const progressPercent = Math.min(100, Math.max(0, (sec / total) * 100));
    pauseProgressBar.style.width = `${progressPercent}%`;

    const mins = Math.ceil(sec / 60);
    if (mins <= 1) {
      pauseTimeLabel.textContent = `${sec} segundos restantes`;
    } else {
      pauseTimeLabel.textContent = `${mins} minutos restantes`;
    }
  }

  function showPauseScanWarning() {
    pauseScanWarning.classList.add("visible");
    clearTimeout(warningTimeout);
    warningTimeout = setTimeout(() => {
      pauseScanWarning.classList.remove("visible");
    }, 3500);
  }

  function showErrorToast(msg) {
    errorMessageText.textContent = msg;
    errorToast.classList.add("show");
    clearTimeout(errorTimeout);
    errorTimeout = setTimeout(() => {
      errorToast.classList.remove("show");
    }, 3500);
  }

  function showUnlockCelebration() {
    unlockToast.classList.add("show");
    setTimeout(() => {
      unlockToast.classList.remove("show");
    }, 3500);
  }

  // ----------------- STARS PROGRESS COMPONENT ----------------- //

  function updateStarsUI() {
    const max = sessionState.max_scans || 3;
    const current = Math.min(sessionState.current_scans, max);

    // Build star SVGs if count changed
    if (starsContainer.children.length !== max) {
      starsContainer.innerHTML = "";
      for (let i = 0; i < max; i++) {
        const starSvg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        starSvg.setAttribute("class", "tv-star");
        starSvg.setAttribute("viewBox", "0 0 24 24");
        starSvg.innerHTML =
          '<path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>';
        starsContainer.appendChild(starSvg);
      }
    }

    // Set active stars
    const stars = starsContainer.querySelectorAll(".tv-star");
    stars.forEach((star, index) => {
      if (index < current) {
        star.classList.add("active");
      } else {
        star.classList.remove("active");
      }
    });

    if (sessionState.is_paused) {
      sessionCounter.textContent = "Hora de colorir";
    } else {
      sessionCounter.textContent = `${current} de ${max} desenhos`;
    }
  }

  function formatDate(dateStr) {
    if (!dateStr) return "";
    try {
      const parts = dateStr.split("-");
      if (parts.length === 3) {
        return `${parts[2]}/${parts[1]}/${parts[0]}`;
      }
    } catch (e) {}
    return dateStr;
  }

  // ----------------- INITIALIZATION & SYNC ----------------- //

  function loadReaderProfile() {
    fetch("/api/reader-profile")
      .then((r) => r.json())
      .then((p) => {
        readerProfile = p;
        console.log("Loaded barcode scanner profile:", p.reader_type, p);
      })
      .catch((e) => console.warn("Could not load reader profile:", e));
  }

  function syncSessionStatus() {
    fetch("/api/session/status")
      .then((r) => r.json())
      .then((s) => {
        sessionState.current_scans = s.current_scans;
        sessionState.max_scans = s.max_scans;
        sessionState.sound_enabled = s.sound_enabled;
        sessionState.title_display_seconds = s.title_display_seconds;
        updateStarsUI();

        if (s.is_paused) {
          startPauseScreen(s.remaining_pause_seconds, s.total_pause_seconds);
        } else if (s.current_item) {
          displayMediaItem(s.current_item, s.current_scans >= s.max_scans);
        } else {
          showWelcomeScreen();
        }
      })
      .catch((e) => console.warn("Session sync error:", e));
  }

  // Server-Sent Events for real-time synchronization
  function initSSE() {
    const evtSource = new EventSource("/api/events");

    evtSource.addEventListener("message", (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.type === "play_drawing") {
          handleScanResponse(msg.data);
        } else if (msg.type === "pause_started") {
          startPauseScreen(msg.data.remaining_seconds, msg.data.total_pause_seconds);
        } else if (msg.type === "pause_unlocked") {
          playSound("unlock");
          showUnlockCelebration();
          endPauseScreen();
          sessionState.current_scans = 0;
          updateStarsUI();
          showWelcomeScreen();
        } else if (msg.type === "settings_updated") {
          loadReaderProfile();
          if (msg.data.sound_enabled !== undefined) {
            sessionState.sound_enabled = msg.data.sound_enabled === "1";
          }
          if (msg.data.max_scans !== undefined) {
            sessionState.max_scans = parseInt(msg.data.max_scans, 10);
            updateStarsUI();
          }
        } else if (msg.type === "session_reset") {
          endPauseScreen();
          sessionState.current_scans = 0;
          updateStarsUI();
          showWelcomeScreen();
        }
      } catch (err) {
        console.error("SSE parse error:", err);
      }
    });

    evtSource.onerror = () => {
      // EventSource automatically retries connection
      console.warn("SSE connection interrupted, retrying...");
    };
  }

  // Boot
  document.addEventListener("DOMContentLoaded", () => {
    ensureInputFocus();
    loadReaderProfile();
    syncSessionStatus();
    initSSE();
  });
})();
