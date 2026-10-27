/**
 * Bipinho — Admin Dashboard Logic
 * Handles media CRUD, settings, scanner profiles, live diagnostics, and simulation.
 */

(function () {
  "use strict";

  // State
  let currentSettings = {};
  let currentItems = [];
  let currentProfileType = "USB";

  const READER_TIPS = {
    USB: "Se nada acontecer ao bipar, desconecte e reconecte o cabo na TV.",
    Bluetooth: "Se o leitor parar de responder, bipe uma vez para acordá-lo ou refaça o pareamento nas configurações da TV.",
    "2.4G": "Verifique se o receptor USB está bem encaixado na TV."
  };

  // ----------------- TABS ----------------- //
  const tabButtons = document.querySelectorAll(".tab-btn");
  const tabPanes = document.querySelectorAll(".tab-pane");

  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.getAttribute("data-tab");
      tabButtons.forEach((b) => b.classList.remove("active"));
      tabPanes.forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(target).classList.add("active");

      if (target === "tab-stats") loadStats();
      if (target === "tab-diagnostics") loadDiagnostics();
      if (target === "tab-live") loadLiveStatus();
      if (target === "tab-history") loadHistory();
      if (target === "tab-parental") { loadParentalSettings(); loadChallenges(); }
      if (target === "tab-tester") {
        setTimeout(() => document.getElementById("tester-input").focus(), 100);
      }
    });
  });

  // ----------------- HEADER & TV BANNER ----------------- //
  function loadAdminInfo() {
    fetch("/api/admin/info")
      .then((r) => r.json())
      .then((info) => {
        document.getElementById("tv-url-text").textContent = info.tv_url;
        document.getElementById("active-profile-pill").innerHTML =
          `Leitor: <strong>${info.reader_type}</strong>`;
        currentProfileType = info.reader_type;
        document.getElementById("item-code").placeholder = `Ex: ${info.next_auto_code}`;
      })
      .catch((e) => console.error("Error loading admin info:", e));
  }

  document.getElementById("btn-copy-url").addEventListener("click", () => {
    const text = document.getElementById("tv-url-text").textContent;
    navigator.clipboard.writeText(text).then(() => {
      const btn = document.getElementById("btn-copy-url");
      btn.textContent = "Copiado! ✓";
      setTimeout(() => (btn.textContent = "Copiar"), 2000);
    });
  });

  // Quick simulate scan from header
  document.getElementById("btn-simulate-scan").addEventListener("click", () => {
    const input = document.getElementById("sim-code-input");
    const code = input.value.trim();
    if (!code) {
      alert("Digite um código para simular o bipe!");
      return;
    }
    simulateBip(code);
  });

  function simulateBip(code) {
    fetch("/api/admin/simulate-scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: code })
    })
      .then((r) => r.json())
      .then((res) => {
        if (res.status === "success") {
          alert(`Bipe simulado com sucesso na TV! Desenho: "${res.item.title}"`);
        } else if (res.status === "parent_unlock") {
          alert("Código dos pais simulado: Pausa liberada na TV!");
        } else if (res.status === "in_pause") {
          alert("A TV está na Hora de Colorir! Desenhos pausados.");
        } else if (res.status === "not_found") {
          alert(`Código desconhecido: "${code}". Aviso exibido na TV.`);
        } else if (res.status === "debounce_ignored") {
          alert("Bipe repetido ignorado (intervalo menor que o configurado).");
        }
      })
      .catch((err) => alert("Erro ao simular bipe: " + err));
  }

  // ----------------- TAB 1: MEDIA CRUD ----------------- //

  // Today's date default
  const todayIso = new Date().toISOString().split("T")[0];
  document.getElementById("item-date").value = todayIso;

  document.getElementById("btn-auto-code").addEventListener("click", () => {
    fetch("/api/admin/info")
      .then((r) => r.json())
      .then((info) => {
        document.getElementById("item-code").value = info.next_auto_code;
      });
  });

  function loadItems() {
    fetch("/api/admin/items")
      .then((r) => r.json())
      .then((items) => {
        currentItems = items;
        document.getElementById("items-count").textContent = items.length;
        renderItemsGrid(items);
      });
  }

  function renderItemsGrid(items) {
    const grid = document.getElementById("items-grid");
    if (!items || items.length === 0) {
      grid.innerHTML = `
        <div style="grid-column: 1/-1; text-align: center; padding: 40px; color: #64748b;">
          <p style="font-size: 18px; font-weight: 600;">Nenhum desenho cadastrado ainda.</p>
          <p style="font-size: 14px; margin-top: 6px;">Use o formulário acima para adicionar vídeos ou imagens.</p>
        </div>
      `;
      return;
    }

    grid.innerHTML = items
      .map((item) => {
        const thumbUrl = `/media/thumbs/${item.thumb_filename}`;
        const typeBadge =
          item.media_type === "video"
            ? '<span class="badge-media-type video">Vídeo</span>'
            : '<span class="badge-media-type image">Imagem</span>';

        const catName = item.category || "Geral";
        const catColorMap = {
          "Animais": "#10b981",
          "Músicas": "#f59e0b",
          "Histórias": "#3b82f6",
          "Educativos": "#8b5cf6",
          "Geral": "#64748b"
        };
        const catColor = catColorMap[catName] || "#64748b";

        return `
        <div class="media-item-card">
          <div class="media-thumb-wrapper">
            <img src="${thumbUrl}" alt="${item.title}" onerror="this.src='/static/icons/default_thumb.svg'">
            ${typeBadge}
            <span class="badge-code">${item.code}</span>
            <span class="badge-category" style="background:${catColor}; color:white; font-size:10px; font-weight:800; padding:2px 6px; border-radius:4px; position:absolute; bottom:6px; left:6px;">${catName}</span>
          </div>
          <div class="media-item-info">
            <h4>${item.title}</h4>
            <div class="media-meta-line">${item.author} • ${formatDate(item.date)}</div>
            <div class="media-views-count">👀 Visto ${item.view_count || 0} vezes</div>
          </div>
          <div class="media-item-actions">
            <button class="btn btn-secondary btn-xs" onclick="BipinhoAdmin.quickBip('${item.code}')" title="Testar exibição na TV">
              📡 Bipar
            </button>
            <a href="/admin/colorir/${item.id}" target="_blank" class="btn btn-outline btn-xs" title="Imprimir versão em contorno para colorir">
              🖍️ Colorir
            </a>
            <button class="btn btn-outline btn-xs" onclick="BipinhoAdmin.viewBarcode('${item.code}', '${escapeHtml(item.title)}')">
              🏷️ Código
            </button>
            <button class="btn btn-outline btn-xs" onclick="BipinhoAdmin.openEditModal(${item.id})">
              ✏️
            </button>
            <button class="btn btn-danger btn-xs" onclick="BipinhoAdmin.deleteItem(${item.id}, '${escapeHtml(item.title)}')">
              🗑️
            </button>
          </div>
        </div>
      `;
      })
      .join("");
  }

  // Create Item Form
  document.getElementById("form-add-item").addEventListener("submit", (e) => {
    e.preventDefault();
    const btn = document.getElementById("btn-submit-item");
    const status = document.getElementById("upload-status");
    btn.disabled = true;
    btn.textContent = "Processando e gerando miniaturas...";
    status.className = "status-msg";
    status.textContent = "";

    const formData = new FormData(e.target);

    fetch("/api/admin/items", {
      method: "POST",
      body: formData
    })
      .then((r) => r.json().then((data) => ({ status: r.status, body: data })))
      .then(({ status: httpStatus, body }) => {
        btn.disabled = false;
        btn.textContent = "Salvar Desenho";
        if (httpStatus === 200) {
          status.className = "status-msg success";
          status.textContent = "Desenho cadastrado com sucesso!";
          if (body.warning) {
            alert("Aviso: " + body.warning);
          }
          document.getElementById("form-add-item").reset();
          document.getElementById("item-date").value = todayIso;
          loadItems();
          loadAdminInfo();
        } else {
          status.className = "status-msg error";
          status.textContent = body.detail || "Erro ao cadastrar desenho.";
        }
      })
      .catch((err) => {
        btn.disabled = false;
        btn.textContent = "Salvar Desenho";
        status.className = "status-msg error";
        status.textContent = "Erro na requisição: " + err;
      });
  });

  // Edit Modal
  window.BipinhoAdmin = window.BipinhoAdmin || {};

  window.BipinhoAdmin.openEditModal = function (itemId) {
    const item = currentItems.find((i) => i.id === itemId);
    if (!item) return;

    document.getElementById("edit-item-id").value = item.id;
    document.getElementById("edit-title").value = item.title;
    document.getElementById("edit-author").value = item.author;
    document.getElementById("edit-date").value = item.date;
    document.getElementById("edit-code").value = item.code;
    const catSelect = document.getElementById("edit-category");
    if (catSelect) catSelect.value = item.category || "Geral";
    document.getElementById("edit-file").value = "";

    document.getElementById("modal-edit").classList.add("active");
  };

  document.getElementById("btn-close-edit").addEventListener("click", () => {
    document.getElementById("modal-edit").classList.remove("active");
  });
  document.getElementById("btn-cancel-edit").addEventListener("click", () => {
    document.getElementById("modal-edit").classList.remove("active");
  });

  document.getElementById("form-edit-item").addEventListener("submit", (e) => {
    e.preventDefault();
    const itemId = document.getElementById("edit-item-id").value;
    const formData = new FormData();
    formData.append("title", document.getElementById("edit-title").value);
    formData.append("author", document.getElementById("edit-author").value);
    formData.append("date", document.getElementById("edit-date").value);
    formData.append("code", document.getElementById("edit-code").value);
    const catSelect = document.getElementById("edit-category");
    if (catSelect) formData.append("category", catSelect.value);

    const fileInput = document.getElementById("edit-file");
    if (fileInput.files.length > 0) {
      formData.append("file", fileInput.files[0]);
    }

    fetch(`/api/admin/items/${itemId}`, {
      method: "PUT",
      body: formData
    })
      .then((r) => r.json().then((data) => ({ status: r.status, body: data })))
      .then(({ status, body }) => {
        if (status === 200) {
          document.getElementById("modal-edit").classList.remove("active");
          loadItems();
        } else {
          alert(body.detail || "Erro ao atualizar desenho.");
        }
      });
  });

  // Delete Item
  window.BipinhoAdmin.deleteItem = function (itemId, title) {
    if (!confirm(`Deseja realmente excluir o desenho "${title}"?`)) return;

    fetch(`/api/admin/items/${itemId}`, { method: "DELETE" })
      .then((r) => r.json())
      .then(() => {
        loadItems();
      });
  };

  // Quick Bip
  window.BipinhoAdmin.quickBip = function (code) {
    simulateBip(code);
  };

  // View Barcode
  window.BipinhoAdmin.viewBarcode = function (code, title) {
    document.getElementById("barcode-modal-title").textContent = title;
    document.getElementById("barcode-modal-code").textContent = code;
    const container = document.getElementById("barcode-svg-container");
    container.innerHTML = "Carregando código de barras...";

    fetch(`/api/barcode/${encodeURIComponent(code)}.svg`)
      .then((r) => r.text())
      .then((svg) => {
        container.innerHTML = svg;
      })
      .catch(() => {
        container.innerHTML = "Erro ao carregar código de barras.";
      });

    document.getElementById("modal-barcode").classList.add("active");
  };

  document.getElementById("btn-close-barcode").addEventListener("click", () => {
    document.getElementById("modal-barcode").classList.remove("active");
  });

  // ----------------- TAB 2: SETTINGS ----------------- //

  function loadSettings() {
    fetch("/api/admin/settings")
      .then((r) => r.json())
      .then((cfg) => {
        currentSettings = cfg;
        document.getElementById("cfg-max-scans").value = cfg.max_scans || 3;
        document.getElementById("cfg-pause-minutes").value = cfg.pause_minutes || 18;
        document.getElementById("cfg-debounce").value = cfg.repeat_debounce_seconds || 3;
        document.getElementById("cfg-title-time").value = cfg.title_display_seconds || 30;
        document.getElementById("cfg-sound").value = cfg.sound_enabled || "1";
        document.getElementById("cfg-parent-code").value = cfg.parent_unlock_code || "PAIS-LIBERAR-99";
        document.getElementById("cfg-surprise-code").value = cfg.surprise_code || "BIP-SURPRESA";
        document.getElementById("cfg-surprise-toggle").value = cfg.surprise_enabled || "1";
        document.getElementById("cfg-access-restriction").value = cfg.admin_access_restriction || "all";
        document.getElementById("cfg-login-max-attempts").value = cfg.login_max_attempts || 5;
        document.getElementById("cfg-login-lockout-minutes").value = cfg.login_lockout_minutes || 15;

        // Etapa 2 new settings
        const watchLimitEl = document.getElementById("cfg-watch-time-limit");
        if (watchLimitEl) watchLimitEl.value = cfg.watch_time_limit_minutes || 15;
        const videoScanEl = document.getElementById("cfg-video-scan-behavior");
        if (videoScanEl) videoScanEl.value = cfg.video_scan_behavior || "interrupt";

        // Radio count_mode
        const countMode = cfg.count_mode || "leituras";
        const countRadio = document.querySelector(`input[name="count_mode"][value="${countMode}"]`);
        if (countRadio) countRadio.checked = true;

        // Radio pause_unlock_mode
        const unlockMode = cfg.pause_unlock_mode || "ambas";
        const unlockRadio = document.querySelector(`input[name="pause_unlock_mode"][value="${unlockMode}"]`);
        if (unlockRadio) unlockRadio.checked = true;

        // Reader profile tab
        updateReaderTabInputs(cfg.reader_type || "USB", cfg);
      });
  }

  document.getElementById("form-settings").addEventListener("submit", (e) => {
    e.preventDefault();
    const status = document.getElementById("settings-status");

    const payload = {
      max_scans: document.getElementById("cfg-max-scans").value,
      pause_minutes: document.getElementById("cfg-pause-minutes").value,
      count_mode: document.querySelector('input[name="count_mode"]:checked').value,
      pause_unlock_mode: document.querySelector('input[name="pause_unlock_mode"]:checked').value,
      repeat_debounce_seconds: document.getElementById("cfg-debounce").value,
      title_display_seconds: document.getElementById("cfg-title-time").value,
      sound_enabled: document.getElementById("cfg-sound").value,
      parent_unlock_code: document.getElementById("cfg-parent-code").value.trim().toUpperCase(),
      surprise_code: document.getElementById("cfg-surprise-code").value.trim().toUpperCase(),
      surprise_enabled: document.getElementById("cfg-surprise-toggle").value,
      admin_access_restriction: document.getElementById("cfg-access-restriction").value,
      login_max_attempts: document.getElementById("cfg-login-max-attempts").value,
      login_lockout_minutes: document.getElementById("cfg-login-lockout-minutes").value,
      watch_time_limit_minutes: (document.getElementById("cfg-watch-time-limit") || {}).value || "15",
      video_scan_behavior: (document.getElementById("cfg-video-scan-behavior") || {}).value || "interrupt"
    };

    fetch("/api/admin/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ settings: payload })
    })
      .then((r) => r.json())
      .then(() => {
        status.className = "status-msg success";
        status.textContent = "Configurações salvas com sucesso!";
        setTimeout(() => (status.textContent = ""), 3000);
      });
  });

  // Change Password
  document.getElementById("form-password").addEventListener("submit", (e) => {
    e.preventDefault();
    const status = document.getElementById("password-status");
    const currentPwd = document.getElementById("pwd-current").value;
    const newPwd = document.getElementById("pwd-new").value;
    const confirmPwd = document.getElementById("pwd-confirm").value;

    if (newPwd !== confirmPwd) {
      status.className = "status-msg error";
      status.textContent = "A nova senha e a confirmação não conferem.";
      return;
    }

    fetch("/api/admin/change-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        current_password: currentPwd,
        new_password: newPwd
      })
    })
      .then((r) => r.json().then((d) => ({ ok: r.ok, body: d })))
      .then(({ ok, body }) => {
        if (ok) {
          status.className = "status-msg success";
          status.textContent = "Senha alterada com sucesso!";
          document.getElementById("form-password").reset();
        } else {
          status.className = "status-msg error";
          status.textContent = body.detail || "Erro ao alterar senha.";
        }
      });
  });

  // ----------------- TAB 3: BARCODE READER PROFILE ----------------- //

  function updateReaderTabInputs(type, cfg) {
    currentProfileType = type;
    const cards = document.querySelectorAll(".reader-type-card");
    cards.forEach((c) => c.classList.remove("selected"));

    const selectedCard = document.querySelector(
      `.reader-type-card input[value="${type}"]`
    );
    if (selectedCard) {
      selectedCard.checked = true;
      selectedCard.closest(".reader-type-card").classList.add("selected");
    }

    // Update Tip
    document.getElementById("tip-text-content").textContent =
      READER_TIPS[type] || "";

    // Set parameters based on type
    if (type === "Bluetooth") {
      document.getElementById("cfg-interchar").value =
        cfg.reader_bt_max_interchar_ms || 300;
      document.getElementById("cfg-terminator").value =
        cfg.reader_bt_terminator || "Enter";
      document.getElementById("cfg-prefix").value =
        cfg.reader_bt_prefix_strip || "";
      document.getElementById("cfg-suffix").value =
        cfg.reader_bt_suffix_strip || "";
      document.getElementById("cfg-min-len").value =
        cfg.reader_bt_min_length || 3;
      document.getElementById("cfg-timeout").value =
        cfg.reader_bt_timeout_ms || 1000;
    } else if (type === "2.4G") {
      document.getElementById("cfg-interchar").value =
        cfg.reader_24g_max_interchar_ms || 100;
      document.getElementById("cfg-terminator").value =
        cfg.reader_24g_terminator || "Enter";
      document.getElementById("cfg-prefix").value =
        cfg.reader_24g_prefix_strip || "";
      document.getElementById("cfg-suffix").value =
        cfg.reader_24g_suffix_strip || "";
      document.getElementById("cfg-min-len").value =
        cfg.reader_24g_min_length || 3;
      document.getElementById("cfg-timeout").value =
        cfg.reader_24g_timeout_ms || 500;
    } else {
      // USB
      document.getElementById("cfg-interchar").value =
        cfg.reader_usb_max_interchar_ms || 100;
      document.getElementById("cfg-terminator").value =
        cfg.reader_usb_terminator || "Enter";
      document.getElementById("cfg-prefix").value =
        cfg.reader_usb_prefix_strip || "";
      document.getElementById("cfg-suffix").value =
        cfg.reader_usb_suffix_strip || "";
      document.getElementById("cfg-min-len").value =
        cfg.reader_usb_min_length || 3;
      document.getElementById("cfg-timeout").value =
        cfg.reader_usb_timeout_ms || 500;
    }
  }

  // Switch reader type immediately without reboot
  document.querySelectorAll('input[name="reader_type"]').forEach((radio) => {
    radio.addEventListener("change", (e) => {
      const newType = e.target.value;
      updateReaderTabInputs(newType, currentSettings);

      // Save active reader type immediately
      fetch("/api/admin/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ settings: { reader_type: newType } })
      })
        .then((r) => r.json())
        .then(() => {
          currentSettings.reader_type = newType;
          loadAdminInfo();
        });
    });
  });

  // Save detailed profile parameters
  document.getElementById("form-reader-profile").addEventListener("submit", (e) => {
    e.preventDefault();
    const status = document.getElementById("reader-status");
    const type = currentProfileType;

    const payload = {};
    if (type === "Bluetooth") {
      payload.reader_bt_max_interchar_ms = document.getElementById("cfg-interchar").value;
      payload.reader_bt_terminator = document.getElementById("cfg-terminator").value;
      payload.reader_bt_prefix_strip = document.getElementById("cfg-prefix").value;
      payload.reader_bt_suffix_strip = document.getElementById("cfg-suffix").value;
      payload.reader_bt_min_length = document.getElementById("cfg-min-len").value;
      payload.reader_bt_timeout_ms = document.getElementById("cfg-timeout").value;
    } else if (type === "2.4G") {
      payload.reader_24g_max_interchar_ms = document.getElementById("cfg-interchar").value;
      payload.reader_24g_terminator = document.getElementById("cfg-terminator").value;
      payload.reader_24g_prefix_strip = document.getElementById("cfg-prefix").value;
      payload.reader_24g_suffix_strip = document.getElementById("cfg-suffix").value;
      payload.reader_24g_min_length = document.getElementById("cfg-min-len").value;
      payload.reader_24g_timeout_ms = document.getElementById("cfg-timeout").value;
    } else {
      payload.reader_usb_max_interchar_ms = document.getElementById("cfg-interchar").value;
      payload.reader_usb_terminator = document.getElementById("cfg-terminator").value;
      payload.reader_usb_prefix_strip = document.getElementById("cfg-prefix").value;
      payload.reader_usb_suffix_strip = document.getElementById("cfg-suffix").value;
      payload.reader_usb_min_length = document.getElementById("cfg-min-len").value;
      payload.reader_usb_timeout_ms = document.getElementById("cfg-timeout").value;
    }

    fetch("/api/admin/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ settings: payload })
    })
      .then((r) => r.json())
      .then(() => {
        status.className = "status-msg success";
        status.textContent = "Parâmetros do perfil salvos com sucesso!";
        setTimeout(() => (status.textContent = ""), 3000);
      });
  });

  // ----------------- TAB 4: TESTER (REAL-TIME DIAGNOSTIC) ----------------- //
  const testerInput = document.getElementById("tester-input");
  const testerFocusZone = document.getElementById("tester-focus-zone");
  let testKeyTimings = [];
  let testLastCharTime = 0;
  let testBuffer = "";

  testerFocusZone.addEventListener("click", () => {
    testerInput.focus();
  });

  testerInput.addEventListener("focus", () => {
    testerFocusZone.classList.add("focused");
  });
  testerInput.addEventListener("blur", () => {
    testerFocusZone.classList.remove("focused");
  });

  testerInput.addEventListener("keydown", (e) => {
    const now = performance.now();
    const isTerminator = e.key === "Enter" || e.key === "Tab";

    if (testLastCharTime > 0) {
      const delta = Math.round(now - testLastCharTime);
      testKeyTimings.push({ key: e.key, delta: delta });
    } else {
      testKeyTimings = [{ key: e.key, delta: 0 }];
    }
    testLastCharTime = now;

    if (isTerminator) {
      e.preventDefault();
      const raw = testBuffer || testerInput.value;
      renderDiagnosticResults(raw, e.key, testKeyTimings);
      testBuffer = "";
      testerInput.value = "";
      testLastCharTime = 0;
      testKeyTimings = [];
      return;
    }

    if (e.key.length === 1) {
      testBuffer += e.key;
    }
  });

  function renderDiagnosticResults(raw, terminator, timings) {
    document.getElementById("res-raw").textContent = raw || "(vazio)";
    document.getElementById("res-term").textContent = terminator;

    // Clean prefix/suffix
    let clean = raw;
    const prefix = document.getElementById("cfg-prefix").value;
    const suffix = document.getElementById("cfg-suffix").value;
    if (prefix && clean.startsWith(prefix)) clean = clean.substring(prefix.length);
    if (suffix && clean.endsWith(suffix)) clean = clean.substring(0, clean.length - suffix.length);
    document.getElementById("res-clean").textContent = clean;

    // Calculate timings
    const deltas = timings.slice(1).map((t) => t.delta);
    if (deltas.length > 0) {
      const avg = Math.round(deltas.reduce((a, b) => a + b, 0) / deltas.length);
      const max = Math.max(...deltas);
      document.getElementById("res-timing").textContent = `${avg} ms méd / ${max} ms máx`;

      // Diagnosis Badge
      const badge = document.getElementById("tester-diagnosis-badge");
      if (max <= 100) {
        badge.className = "diagnosis-badge good";
        badge.textContent = `Status: Excelente! Leitura ultrarrápida (máx ${max}ms). Perfeito para USB ou 2.4G.`;
      } else if (max <= 300) {
        badge.className = "diagnosis-badge good";
        badge.textContent = `Status: Bom! Leitura em ${max}ms. Compatível com perfil Bluetooth.`;
      } else {
        badge.className = "diagnosis-badge warning";
        badge.textContent = `Status: Intervalo longo detectado (${max}ms). Aumente o "Tempo Máximo Entre Caracteres" se houver falhas.`;
      }
    } else {
      document.getElementById("res-timing").textContent = "N/A";
    }

    // Render key log pills
    const logContainer = document.getElementById("tester-key-log");
    logContainer.innerHTML = timings
      .map(
        (t) => `
        <span class="key-pill">
          ${t.key === "Enter" ? "↵ Enter" : t.key === "Tab" ? "⇥ Tab" : t.key}
          <span class="delta">${t.delta}ms</span>
        </span>
      `
      )
      .join("");
  }

  // ----------------- TAB 5: STATS ----------------- //

  function loadStats() {
    fetch("/api/admin/stats")
      .then((r) => r.json())
      .then((stats) => {
        document.getElementById("stat-total-items").textContent = stats.total_items;
        document.getElementById("stat-total-views").textContent = stats.total_views;

        const favList = document.getElementById("favorites-list");
        if (!stats.favorites || stats.favorites.length === 0) {
          favList.innerHTML =
            "<p style='color: #64748b; font-size: 14px;'>Nenhum desenho foi visto ainda.</p>";
          return;
        }

        favList.innerHTML = stats.favorites
          .map((fav, idx) => `
            <div class="favorite-row">
              <span class="fav-rank">#${idx + 1}</span>
              <img src="/media/thumbs/${fav.thumb_filename}" class="fav-thumb" alt="${fav.title}" onerror="this.style.display='none'">
              <div class="fav-title">${fav.title} <small style="color: #64748b">(${fav.code})</small></div>
              <div class="fav-views">${fav.view_count} visualizações</div>
            </div>
          `)
          .join("");
      });
  }

  document.getElementById("btn-reset-session").addEventListener("click", () => {
    if (!confirm("Deseja realmente zerar a sessão e as estrelas na TV agora?")) return;
    fetch("/api/admin/reset-session", { method: "POST" })
      .then((r) => r.json())
      .then(() => {
        alert("Sessão da TV reiniciada com sucesso!");
      });
  });

  // ----------------- TAB: DIAGNOSTICS ----------------- //
  function loadDiagnostics() {
    fetch("/api/admin/diagnostics")
      .then((r) => r.json())
      .then((d) => {
        document.getElementById("diag-bipinho-version").textContent = d.version || "1.1.0";
        document.getElementById("diag-disk-free").textContent = `${d.disk.free_gb} GB (${d.disk.percent_free}%)`;
        document.getElementById("diag-db-status").textContent = d.database.ok ? "Saudável (OK)" : "Erro";
        document.getElementById("diag-db-size").textContent = `${d.database.size_kb} KB`;
        
        const ffmpegAlert = document.getElementById("diag-ffmpeg-alert");
        const ffmpegDetail = document.getElementById("diag-ffmpeg-detail");
        if (d.ffmpeg.found) {
          ffmpegAlert.style.display = "none";
          ffmpegDetail.innerHTML = `<span style="color:#10b981;">✅ Instalado</span> — ${d.ffmpeg.version} (<code>${d.ffmpeg.path}</code>)`;
        } else {
          ffmpegAlert.className = "alert-error";
          ffmpegAlert.style.display = "block";
          ffmpegAlert.innerHTML = `⚠️ <strong>FFmpeg não encontrado!</strong> Vídeos que não sejam MP4 H.264 direto não poderão ser convertidos e miniaturas de vídeo podem falhar. Instale o FFmpeg ou coloque o executável no PATH do Windows.`;
          ffmpegDetail.innerHTML = `<span style="color:#ef4444;">❌ Não encontrado</span> — ${d.ffmpeg.error || "Ausente no PATH"}`;
        }

        const sleepEl = document.getElementById("diag-sleep-status");
        if (d.sleep.warning) {
          sleepEl.innerHTML = `<span style="color:#f59e0b;">⚠️ ${d.sleep.message}</span>`;
        } else {
          sleepEl.innerHTML = `<span style="color:#10b981;">✅ ${d.sleep.message}</span>`;
        }

        document.getElementById("diag-tv-url").textContent = d.network.tv_url;
      })
      .catch((err) => console.error("Error loading diagnostics:", err));
  }

  const btnRefreshDiag = document.getElementById("btn-refresh-diag");
  if (btnRefreshDiag) {
    btnRefreshDiag.addEventListener("click", loadDiagnostics);
  }

  // Helpers
  function formatDate(d) {
    if (!d) return "";
    const p = d.split("-");
    return p.length === 3 ? `${p[2]}/${p[1]}/${p[0]}` : d;
  }

  function escapeHtml(str) {
    return (str || "")
      .replace(/&/g, "&amp;")
      .replace(/'/g, "\\'")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  // ----------------- BACKUP & RESTORE ----------------- //

  const formRestoreBackup = document.getElementById("form-restore-backup");
  if (formRestoreBackup) {
    formRestoreBackup.addEventListener("submit", (e) => {
      e.preventDefault();
      const status = document.getElementById("restore-status");
      const fileInput = document.getElementById("restore-zip-input") || document.getElementById("backup-file");
      if (!fileInput || !fileInput.files.length) {
        status.className = "status-msg error";
        status.textContent = "Selecione um arquivo .zip de backup.";
        return;
      }
      if (!confirm("⚠️ ATENÇÃO: Restaurar o backup substituirá TODOS os dados atuais (desenhos, configurações e mídias). Deseja continuar?")) {
        return;
      }
      const formData = new FormData();
      formData.append("file", fileInput.files[0]);
      status.className = "status-msg";
      status.textContent = "Restaurando backup, aguarde...";
      fetch("/api/admin/backup/restore", {
        method: "POST",
        body: formData
      })
        .then((r) => r.json().then((d) => ({ ok: r.ok, body: d })))
        .then(({ ok, body }) => {
          if (ok) {
            status.className = "status-msg success";
            status.textContent = "✅ " + (body.message || "Backup restaurado com sucesso!");
            loadItems();
            loadSettings();
          } else {
            status.className = "status-msg error";
            status.textContent = "❌ " + (body.detail || "Erro ao restaurar backup.");
          }
        })
        .catch((err) => {
          status.className = "status-msg error";
          status.textContent = "❌ Erro inesperado: " + err;
        });
    });
  }

  // ----------------- ETAPA 3: PARENTAL SETTINGS ----------------- //

  function loadParentalSettings() {
    fetch("/api/admin/settings")
      .then((r) => r.json())
      .then((s) => {
        const scheduleEnabled = document.getElementById("cfg-schedule-enabled");
        if (scheduleEnabled) scheduleEnabled.value = s.schedule_enabled || "0";

        const maxSessions = document.getElementById("cfg-max-sessions");
        if (maxSessions) maxSessions.value = s.max_sessions_per_day || "0";

        const startTime = document.getElementById("cfg-start-time");
        if (startTime) startTime.value = s.allowed_start_time || "07:00";

        const endTime = document.getElementById("cfg-end-time");
        if (endTime) endTime.value = s.allowed_end_time || "21:00";

        const mascotEnabled = document.getElementById("cfg-mascot-enabled");
        if (mascotEnabled) mascotEnabled.value = s.mascot_enabled !== undefined ? s.mascot_enabled : "1";

        const challengesEnabled = document.getElementById("cfg-challenges-enabled");
        if (challengesEnabled) challengesEnabled.value = s.movement_challenges_enabled !== undefined ? s.movement_challenges_enabled : "1";

        // Days of week checkboxes
        const allowedDays = (s.allowed_days || "0,1,2,3,4,5,6").split(",").map((d) => d.trim());
        document.querySelectorAll(".day-checkbox").forEach((cb) => {
          cb.checked = allowedDays.includes(cb.value);
        });
      })
      .catch((e) => console.error("Error loading parental settings:", e));
  }

  const formParentalSettings = document.getElementById("form-parental-settings");
  if (formParentalSettings) {
    formParentalSettings.addEventListener("submit", (e) => {
      e.preventDefault();
      const statusEl = document.getElementById("parental-settings-status");
      statusEl.className = "status-msg";
      statusEl.textContent = "Salvando...";

      const selectedDays = [];
      document.querySelectorAll(".day-checkbox:checked").forEach((cb) => {
        selectedDays.push(cb.value);
      });

      const payload = {
        schedule_enabled: document.getElementById("cfg-schedule-enabled").value,
        max_sessions_per_day: document.getElementById("cfg-max-sessions").value,
        allowed_start_time: document.getElementById("cfg-start-time").value,
        allowed_end_time: document.getElementById("cfg-end-time").value,
        allowed_days: selectedDays.join(","),
        mascot_enabled: document.getElementById("cfg-mascot-enabled").value,
        movement_challenges_enabled: document.getElementById("cfg-challenges-enabled").value
      };

      fetch("/api/admin/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ settings: payload })
      })
        .then((r) => r.json())
        .then((res) => {
          if (res.status === "success") {
            statusEl.className = "status-msg success";
            statusEl.textContent = "Configurações dos pais salvas com sucesso!";
            setTimeout(() => (statusEl.textContent = ""), 3000);
          } else {
            statusEl.className = "status-msg error";
            statusEl.textContent = "Erro ao salvar.";
          }
        })
        .catch((err) => {
          statusEl.className = "status-msg error";
          statusEl.textContent = "Erro: " + err;
        });
    });
  }

  // ----------------- ETAPA 3: MOVEMENT CHALLENGES ----------------- //

  let challengesData = [];

  function loadChallenges() {
    fetch("/api/admin/challenges")
      .then((r) => r.json())
      .then((d) => {
        challengesData = d.challenges || [];
        renderChallengesList();
      })
      .catch((e) => console.error("Error loading challenges:", e));
  }

  function renderChallengesList() {
    const listEl = document.getElementById("challenges-list");
    if (!listEl) return;

    if (challengesData.length === 0) {
      listEl.innerHTML = "<p style='color:#64748b; font-size:13px;'>Nenhum desafio cadastrado. Clique em '+ Adicionar Desafio'.</p>";
      return;
    }

    listEl.innerHTML = challengesData
      .map(
        (c, idx) => `
        <div class="challenge-row" data-idx="${idx}">
          <input type="checkbox" ${c.enabled ? "checked" : ""} class="ch-enabled" title="Ativar/desativar">
          <input type="text" value="${escapeHtml(c.challenge)}" class="ch-text" placeholder="Sugestão de movimento...">
          <button type="button" class="btn btn-danger btn-xs btn-remove-ch" data-idx="${idx}">🗑️</button>
        </div>
      `
      )
      .join("");

    listEl.querySelectorAll(".btn-remove-ch").forEach((btn) => {
      btn.addEventListener("click", () => {
        const idx = parseInt(btn.getAttribute("data-idx"), 10);
        challengesData.splice(idx, 1);
        renderChallengesList();
      });
    });
  }

  const btnAddChallenge = document.getElementById("btn-add-challenge");
  if (btnAddChallenge) {
    btnAddChallenge.addEventListener("click", () => {
      challengesData.push({ challenge: "Novo desafio de movimento!", enabled: 1 });
      renderChallengesList();
      const inputs = document.querySelectorAll(".challenge-row .ch-text");
      if (inputs.length) inputs[inputs.length - 1].focus();
    });
  }

  const btnSaveChallenges = document.getElementById("btn-save-challenges");
  if (btnSaveChallenges) {
    btnSaveChallenges.addEventListener("click", () => {
      const rows = document.querySelectorAll(".challenge-row");
      const listToSave = [];
      rows.forEach((row) => {
        const text = row.querySelector(".ch-text").value.trim();
        const enabled = row.querySelector(".ch-enabled").checked;
        if (text) {
          listToSave.push({ challenge: text, enabled: enabled ? 1 : 0 });
        }
      });

      const statusEl = document.getElementById("challenges-status");
      statusEl.className = "status-msg";
      statusEl.textContent = "Salvando lista...";

      fetch("/api/admin/challenges", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ challenges: listToSave })
      })
        .then((r) => r.json())
        .then((res) => {
          if (res.status === "success") {
            statusEl.className = "status-msg success";
            statusEl.textContent = `Salvo com sucesso! (${res.count} desafios)`;
            loadChallenges();
            setTimeout(() => (statusEl.textContent = ""), 3000);
          } else {
            statusEl.className = "status-msg error";
            statusEl.textContent = "Erro ao salvar lista.";
          }
        })
        .catch((err) => {
          statusEl.className = "status-msg error";
          statusEl.textContent = "Erro: " + err;
        });
    });
  }

  // ----------------- ETAPA 3: BULK IMPORT ----------------- //

  const btnBulkImport = document.getElementById("btn-bulk-import");
  if (btnBulkImport) {
    btnBulkImport.addEventListener("click", () => {
      const folderInput = document.getElementById("bulk-folder-path");
      const authorInput = document.getElementById("bulk-author");
      const statusEl = document.getElementById("bulk-import-status");
      const resultsEl = document.getElementById("bulk-import-results");

      const folderPath = folderInput ? folderInput.value.trim() : "";
      const author = authorInput ? authorInput.value.trim() || "Família" : "Família";

      if (!folderPath) {
        alert("Por favor, informe o caminho completo da pasta no servidor.");
        return;
      }

      btnBulkImport.disabled = true;
      btnBulkImport.textContent = "Importando arquivos, aguarde...";
      statusEl.className = "status-msg";
      statusEl.textContent = "Lendo e processando arquivos...";
      resultsEl.style.display = "none";
      resultsEl.innerHTML = "";

      fetch("/api/admin/bulk-import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ folder_path: folderPath, author: author })
      })
        .then((r) => r.json().then((d) => ({ ok: r.ok, body: d })))
        .then(({ ok, body }) => {
          btnBulkImport.disabled = false;
          btnBulkImport.textContent = "📂 Importar Pasta";

          if (ok && body.status === "success") {
            statusEl.className = "status-msg success";
            statusEl.textContent = `Importação concluída! ${body.imported_count} item(ns) importado(s).`;
            loadItems();

            let detailsHtml = "<div class='card' style='background:#f8fafc; border:1px solid #cbd5e1; padding:16px;'>";
            detailsHtml += `<h4>Resultado da Importação: ${body.imported_count} sucesso, ${body.error_count} erro(s)</h4>`;

            if (body.imported.length) {
              detailsHtml += "<ul style='margin-top:8px; padding-left:20px; font-size:13px;'>";
              body.imported.forEach((it) => {
                const warn = it.warning ? ` <span style='color:#f59e0b;'>⚠️ ${it.warning}</span>` : "";
                detailsHtml += `<li><strong>${it.code}</strong> — ${it.title} (${it.file})${warn}</li>`;
              });
              detailsHtml += "</ul>";
            }

            if (body.errors.length) {
              detailsHtml += "<div style='color:#ef4444; margin-top:10px; font-size:13px;'><strong>Falhas:</strong><ul>";
              body.errors.forEach((err) => {
                detailsHtml += `<li>${err.file}: ${err.error}</li>`;
              });
              detailsHtml += "</ul></div>";
            }
            detailsHtml += "</div>";

            resultsEl.innerHTML = detailsHtml;
            resultsEl.style.display = "block";
          } else {
            statusEl.className = "status-msg error";
            statusEl.textContent = "Erro: " + (body.detail || "Falha na importação.");
          }
        })
        .catch((err) => {
          btnBulkImport.disabled = false;
          btnBulkImport.textContent = "📂 Importar Pasta";
          statusEl.className = "status-msg error";
          statusEl.textContent = "Erro inesperado: " + err;
        });
    });
  }

  // ----------------- ETAPA 3: LIVE PANEL ----------------- //

  function loadLiveStatus() {
    fetch("/api/admin/live-status")
      .then((r) => r.json())
      .then((st) => {
        renderLiveStatus(st);
      })
      .catch((e) => console.error("Error loading live status:", e));
  }

  function renderLiveStatus(st) {
    const curItemEl = document.getElementById("live-current-item");
    if (curItemEl) {
      if (st.current_item) {
        curItemEl.textContent = `🎬 ${st.current_item.title} (${st.current_item.code})`;
      } else {
        curItemEl.textContent = "— Aguardando bipe";
      }
    }

    const starsEl = document.getElementById("live-stars");
    if (starsEl) {
      starsEl.textContent = `⭐ ${st.current_scans || 0} / ${st.max_scans || 3}`;
    }

    const watchTimeEl = document.getElementById("live-watch-time");
    if (watchTimeEl) {
      const mins = Math.floor((st.watched_seconds || 0) / 60);
      const secs = Math.floor((st.watched_seconds || 0) % 60);
      watchTimeEl.textContent = `${mins}m ${secs}s (Limite: ${st.watch_time_limit_minutes || 15}m)`;
    }

    const pauseEl = document.getElementById("live-pause-info");
    if (pauseEl) {
      if (st.is_paused) {
        const remMins = Math.ceil((st.remaining_pause_seconds || 0) / 60);
        pauseEl.innerHTML = `<span style="color:#f59e0b;">⏸️ Em Pausa (${remMins} min restantes)</span>`;
      } else {
        pauseEl.innerHTML = `<span style="color:#10b981;">▶️ TV Liberada para assistir</span>`;
      }
    }

    const schedEl = document.getElementById("live-schedule-info");
    if (schedEl) {
      if (st.tv_blocked) {
        schedEl.innerHTML = `<span style="color:#ef4444;">🔒 TV Bloqueada Manualmente</span>`;
      } else if (st.schedule && !st.schedule.allowed) {
        schedEl.innerHTML = `<span style="color:#818cf8;">😴 Bipinho Dormindo (${st.schedule.reason})</span>`;
      } else {
        schedEl.innerHTML = `<span style="color:#10b981;">✅ Horário Permitido</span>`;
      }
    }
  }

  // Live control buttons
  const btnLiveRefresh = document.getElementById("btn-live-refresh");
  if (btnLiveRefresh) btnLiveRefresh.addEventListener("click", loadLiveStatus);

  const btnLiveEndPause = document.getElementById("btn-live-end-pause");
  if (btnLiveEndPause) {
    btnLiveEndPause.addEventListener("click", () => {
      fetch("/api/admin/session/end-pause", { method: "POST" })
        .then((r) => r.json())
        .then(() => {
          showLiveStatusMsg("Pausa encerrada!", "success");
          loadLiveStatus();
        });
    });
  }

  const btnLiveBlockTv = document.getElementById("btn-live-block-tv");
  if (btnLiveBlockTv) {
    btnLiveBlockTv.addEventListener("click", () => {
      fetch("/api/admin/tv/block", { method: "POST" })
        .then((r) => r.json())
        .then(() => {
          showLiveStatusMsg("TV bloqueada com sucesso!", "error");
          loadLiveStatus();
        });
    });
  }

  const btnLiveReleaseTv = document.getElementById("btn-live-release-tv");
  if (btnLiveReleaseTv) {
    btnLiveReleaseTv.addEventListener("click", () => {
      fetch("/api/admin/tv/release", { method: "POST" })
        .then((r) => r.json())
        .then(() => {
          showLiveStatusMsg("TV liberada com sucesso!", "success");
          loadLiveStatus();
        });
    });
  }

  const btnLiveResetSession = document.getElementById("btn-live-reset-session");
  if (btnLiveResetSession) {
    btnLiveResetSession.addEventListener("click", () => {
      fetch("/api/admin/reset-session", { method: "POST" })
        .then((r) => r.json())
        .then(() => {
          showLiveStatusMsg("Sessão reiniciada!", "success");
          loadLiveStatus();
        });
    });
  }

  function showLiveStatusMsg(msg, type) {
    const el = document.getElementById("live-control-status");
    if (!el) return;
    el.className = `status-msg ${type}`;
    el.textContent = msg;
    setTimeout(() => (el.textContent = ""), 3000);
  }

  // Auto-refresh live panel when active
  setInterval(() => {
    const liveTab = document.getElementById("tab-live");
    if (liveTab && liveTab.classList.contains("active")) {
      loadLiveStatus();
    }
  }, 4000);

  // ----------------- ETAPA 3: HISTORY & SVG CHART ----------------- //

  function loadHistory() {
    fetch("/api/admin/history?days=7")
      .then((r) => r.json())
      .then((data) => {
        renderHistoryChart(data.history || []);
        renderHistoryTable(data.history || []);
      })
      .catch((e) => console.error("Error loading history:", e));
  }

  const btnHistoryRefresh = document.getElementById("btn-history-refresh");
  if (btnHistoryRefresh) btnHistoryRefresh.addEventListener("click", loadHistory);

  function renderHistoryChart(history) {
    const svg = document.getElementById("history-chart");
    if (!svg) return;

    if (!history || history.length === 0) {
      svg.innerHTML = "<text x='350' y='100' text-anchor='middle' fill='#94a3b8'>Sem histórico disponível</text>";
      return;
    }

    // Convert seconds to minutes for each day
    const dayData = history.map((h) => {
      const mins = Math.round((h.total_watched_seconds || 0) / 60);
      const parts = (h.date || "").split("-");
      const label = parts.length === 3 ? `${parts[2]}/${parts[1]}` : h.date;
      return { date: h.date, label: label, minutes: mins, sessions: h.session_count || 0 };
    });

    const maxMinutes = Math.max(...dayData.map((d) => d.minutes), 30); // at least 30 min scale

    const svgWidth = 700;
    const svgHeight = 200;
    const paddingLeft = 50;
    const paddingBottom = 30;
    const paddingTop = 20;
    const chartWidth = svgWidth - paddingLeft - 20;
    const chartHeight = svgHeight - paddingTop - paddingBottom;

    const barWidth = Math.floor(chartWidth / dayData.length) - 20;

    let svgHtml = "";

    // Background horizontal grid lines
    const gridLines = [0, 0.5, 1];
    gridLines.forEach((pct) => {
      const y = paddingTop + chartHeight * (1 - pct);
      const val = Math.round(maxMinutes * pct);
      svgHtml += `<line x1="${paddingLeft}" y1="${y}" x2="${svgWidth - 20}" y2="${y}" stroke="#e2e8f0" stroke-dasharray="4,4" />`;
      svgHtml += `<text x="${paddingLeft - 8}" y="${y + 4}" font-size="11" fill="#94a3b8" text-anchor="end">${val}m</text>`;
    });

    // Bars
    dayData.forEach((d, idx) => {
      const x = paddingLeft + idx * (barWidth + 20) + 10;
      const h = (d.minutes / maxMinutes) * chartHeight;
      const y = paddingTop + (chartHeight - h);

      // Bar
      const barColor = d.minutes > 0 ? "#3b82f6" : "#e2e8f0";
      svgHtml += `
        <rect x="${x}" y="${y}" width="${barWidth}" height="${Math.max(2, h)}" rx="6" fill="${barColor}">
          <title>${d.label}: ${d.minutes} min (${d.sessions} sessões)</title>
        </rect>
      `;

      // Value on top of bar
      if (d.minutes > 0) {
        svgHtml += `<text x="${x + barWidth / 2}" y="${Math.max(14, y - 6)}" font-size="11" font-weight="bold" fill="#1e293b" text-anchor="middle">${d.minutes}m</text>`;
      }

      // Day label at bottom
      svgHtml += `<text x="${x + barWidth / 2}" y="${svgHeight - 10}" font-size="12" fill="#64748b" text-anchor="middle">${d.label}</text>`;
    });

    svg.innerHTML = svgHtml;
  }

  function renderHistoryTable(history) {
    const tbody = document.getElementById("history-table-body");
    if (!tbody) return;

    if (!history || history.length === 0) {
      tbody.innerHTML = "<tr><td colspan='4' style='text-align:center; color:#94a3b8;'>Nenhum histórico registrado ainda.</td></tr>";
      return;
    }

    tbody.innerHTML = history
      .slice()
      .reverse()
      .map((h) => {
        const totalSec = h.total_watched_seconds || 0;
        const mins = Math.floor(totalSec / 60);
        const secs = Math.floor(totalSec % 60);
        const timeFormatted = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;

        const topDrawings = (h.top_items || [])
          .map((t) => `${t.item_title} (${t.plays}x)`)
          .join(", ") || "—";

        return `
          <tr>
            <td><strong>${formatDate(h.date)}</strong></td>
            <td>${h.session_count || 0}</td>
            <td>${timeFormatted}</td>
            <td style="color:#64748b; font-size:13px;">${topDrawings}</td>
          </tr>
        `;
      })
      .join("");
  }

  // Boot
  document.addEventListener("DOMContentLoaded", () => {
    loadAdminInfo();
    loadItems();
    loadSettings();
    loadDiagnostics();
  });
})();
