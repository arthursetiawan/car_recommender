(() => {
  const COLORS = ["#c45c26", "#1a7a6c", "#3d6ea8", "#8a4f2b", "#5b7c5a", "#b45309"];

  const STEP_META = [
    { id: "budget", label: "Budget", short: "1" },
    { id: "body", label: "Type", short: "2" },
    { id: "priority", label: "Priority", short: "3" },
    { id: "condition", label: "New/used", short: "4" },
    { id: "compare", label: "Compare", short: "5" },
    { id: "decide", label: "Best match", short: "6" },
  ];

  const STEP_TITLES = {
    budget: "Step 1 · Budget",
    body: "Step 2 · Vehicle type",
    priority: "Step 3 · What matters most",
    condition: "Step 4 · New or used",
    compare: "Step 5 · Compare options",
    decide: "Step 6 · Your best match",
  };

  const els = {
    messages: document.getElementById("messages"),
    choices: document.getElementById("choices"),
    choiceHint: document.getElementById("choice-hint"),
    form: document.getElementById("chat-form"),
    input: document.getElementById("chat-input"),
    modeBadge: document.getElementById("mode-badge"),
    resetBtn: document.getElementById("reset-btn"),
    askEvBtn: document.getElementById("ask-ev-btn"),
    canvas: document.getElementById("hex-radar"),
    legend: document.getElementById("legend"),
    radarSub: document.getElementById("radar-sub"),
    bestCard: document.getElementById("best-card"),
    gallery: document.getElementById("contender-gallery"),
    emptyCompare: document.getElementById("empty-compare"),
    compareLive: document.getElementById("compare-live"),
    questSteps: document.getElementById("quest-steps"),
    stepLabel: document.getElementById("step-label"),
    roiForm: document.getElementById("roi-form"),
    roiPair: document.getElementById("roi-pair"),
    customPrices: document.getElementById("custom-prices"),
    roiResult: document.getElementById("roi-result"),
    roiToggle: document.getElementById("roi-toggle"),
    roiPanel: document.querySelector(".roi-panel"),
  };

  function carImage(car) {
    return car.image || `/static/cars/${car.id}.jpg`;
  }

  function resolveGroupId() {
    if (window.__DQ_GROUP__) return window.__DQ_GROUP__;
    if (window.__DQ_DEALER__) return window.__DQ_DEALER__;
    const params = new URLSearchParams(window.location.search);
    if (params.get("group")) return params.get("group");
    if (params.get("dealer")) return params.get("dealer");
    const parts = window.location.pathname.split("/").filter(Boolean);
    if ((parts[0] === "embed" || parts[0] === "admin") && parts[1]) return parts[1];
    return null;
  }

  function resolveLocationId() {
    if (window.__DQ_LOCATION__) return window.__DQ_LOCATION__;
    const params = new URLSearchParams(window.location.search);
    if (params.get("location")) return params.get("location");
    const parts = window.location.pathname.split("/").filter(Boolean);
    if (parts[0] === "embed" && parts[2]) return parts[2];
    return null;
  }

  let sessionId = null;
  let lastContenders = [];
  let dealerId = resolveGroupId(); // group id (alias kept for API payloads)
  let locationId = resolveLocationId();
  let dealerMeta = null;

  function tenantQuery() {
    const parts = [];
    if (dealerId) parts.push(`group_id=${encodeURIComponent(dealerId)}`);
    if (locationId) parts.push(`location_id=${encodeURIComponent(locationId)}`);
    return parts.length ? `?${parts.join("&")}` : "";
  }

  function tenantBody(extra) {
    const body = Object.assign({}, extra || {});
    if (dealerId) {
      body.group_id = dealerId;
      body.dealer_id = dealerId;
    }
    if (locationId) body.location_id = locationId;
    return body;
  }

  function applyBranding(dealer) {
    if (!dealer) return;
    dealerMeta = dealer;
    dealerId = dealer.group_id || dealer.id || dealerId;
    locationId = dealer.location_id || locationId;
    const title = document.getElementById("dealer-title");
    const tagline = document.getElementById("dealer-tagline");
    if (title) title.textContent = dealer.name || "DriveQuest";
    if (tagline) {
      const scope =
        dealer.scope === "location" && dealer.group_name
          ? `${dealer.tagline || ""} · part of ${dealer.group_name}`
          : dealer.tagline || tagline.textContent;
      tagline.textContent = scope;
    }
    const b = dealer.branding || {};
    if (b.primary) document.documentElement.style.setProperty("--copper", b.primary);
    if (b.primary_deep) document.documentElement.style.setProperty("--copper-deep", b.primary_deep);
    if (b.accent) {
      document.documentElement.style.setProperty("--teal", b.accent);
      document.documentElement.style.setProperty("--teal-deep", b.accent);
    }
    document.title = `${dealer.name || "DriveQuest"} — Find your best car`;
  }

  async function loadRoiPairs() {
    if (!els.roiPair) return;
    const res = await fetch(`/api/roi/defaults${tenantQuery()}`);
    if (!res.ok) return;
    const data = await res.json();
    const pairs = data.sample_pairs || [];
    if (!pairs.length) return;
    els.roiPair.innerHTML = pairs
      .map((p) => `<option value="${p.ev_car_id}|${p.gas_car_id}">${p.label}</option>`)
      .concat(['<option value="custom">Enter my own prices…</option>'])
      .join("");
  }

  function formatReply(text) {
    const escaped = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
    return escaped.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  }

  function addBubble(role, text) {
    const div = document.createElement("div");
    div.className = `bubble ${role}`;
    div.innerHTML = formatReply(text);
    els.messages.appendChild(div);
    els.messages.scrollTop = els.messages.scrollHeight;
  }

  function renderSteps(stageId) {
    const idx = STEP_META.findIndex((s) => s.id === stageId);
    const active = idx < 0 ? 0 : idx;
    els.questSteps.innerHTML = STEP_META.map((step, i) => {
      const state = i < active ? "is-done" : i === active ? "is-active" : "";
      return `<li class="${state}"><span class="num">${step.short}</span><span class="label-full">${step.label}</span></li>`;
    }).join("");
    els.stepLabel.textContent = STEP_TITLES[stageId] || STEP_TITLES.budget;
  }

  function renderChoices(stage) {
    els.choices.innerHTML = "";
    const hasChoices = stage && stage.choices && stage.choices.length;
    els.choiceHint.textContent = hasChoices
      ? "Tap a choice to continue"
      : "Type a reply below, or ask about EV savings";
    els.choiceHint.classList.toggle("is-quiet", !hasChoices);
    if (!hasChoices) return;

    stage.choices.forEach((choice, i) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "choice-chip" + (i === 0 && stage.stage === "decide" ? " is-primary" : "");
      // Highlight primary actions on compare/decide
      const val = String(choice.value);
      if (val === "best" || val === "done" || (stage.stage === "budget" && i === 1)) {
        btn.classList.add("is-primary");
      }
      btn.textContent = choice.label;
      btn.addEventListener("click", () => sendChoice(stage.stage, choice.value, choice.label));
      els.choices.appendChild(btn);
    });
  }

  function setModeBadge(payload) {
    const mode = payload.mode === "langchain" ? "Live advisor" : "Demo advisor";
    const key = payload.openai_configured ? "" : " · works without an API key";
    els.modeBadge.hidden = false;
    els.modeBadge.textContent = mode + key;
  }

  function setCompareVisibility(hasCars) {
    els.emptyCompare.classList.toggle("hidden", hasCars);
    els.compareLive.classList.toggle("hidden", !hasCars);
  }

  function renderBest(contenders, prefs) {
    if (!contenders.length || (prefs && prefs.stage !== "decide")) {
      els.bestCard.classList.add("hidden");
      els.bestCard.innerHTML = "";
      return;
    }
    const best = contenders[0];
    const label = `${best.year} ${best.make} ${best.model}`;
    els.bestCard.classList.remove("hidden");
    els.bestCard.innerHTML = `
      <img src="${carImage(best)}" alt="${label}" loading="lazy" />
      <div class="best-body">
        <span class="best-eyebrow">Best match for you</span>
        <h3>${label}</h3>
        <p>$${Number(best.price).toLocaleString()} · score ${best.overall}/10 · ${best.summary || ""}</p>
      </div>
    `;
  }

  function renderGallery(contenders) {
    els.gallery.innerHTML = "";
    contenders.slice(0, 4).forEach((car, idx) => {
      const card = document.createElement("article");
      card.className = "contender-card";
      card.style.borderColor = COLORS[idx % COLORS.length];
      const label = `${car.year} ${car.make} ${car.model}`;
      card.innerHTML = `
        <img src="${carImage(car)}" alt="${label}" loading="lazy" />
        <div class="cap">${label}<br>$${Number(car.price).toLocaleString()} · ${car.overall}/10</div>
      `;
      els.gallery.appendChild(card);
    });
  }

  function polygonPoints(cx, cy, radius, sides, values) {
    const pts = [];
    for (let i = 0; i < sides; i++) {
      const angle = -Math.PI / 2 + (i * 2 * Math.PI) / sides;
      const r = radius * (values ? values[i] / 10 : 1);
      pts.push([cx + Math.cos(angle) * r, cy + Math.sin(angle) * r]);
    }
    return pts;
  }

  function drawPath(ctx, pts, { fill, stroke, width = 2, alpha = 1 } = {}) {
    if (!pts.length) return;
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);
    for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
    ctx.closePath();
    if (fill) {
      ctx.fillStyle = fill;
      ctx.fill();
    }
    if (stroke) {
      ctx.strokeStyle = stroke;
      ctx.lineWidth = width;
      ctx.stroke();
    }
    ctx.restore();
  }

  function drawRadar(contenders) {
    const canvas = els.canvas;
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const size = 420;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, size, size);

    const cx = size / 2;
    const cy = size / 2;
    const radius = 145;
    const labels =
      (contenders[0] && contenders[0].hex_labels) ||
      ["Value", "Budget Fit", "Reliability", "Efficiency", "Safety", "Practicality"];
    const sides = labels.length;

    for (let ring = 1; ring <= 5; ring++) {
      const pts = polygonPoints(cx, cy, (radius * ring) / 5, sides);
      drawPath(ctx, pts, { stroke: "rgba(16,24,32,0.1)", width: 1 });
    }
    for (let i = 0; i < sides; i++) {
      const angle = -Math.PI / 2 + (i * 2 * Math.PI) / sides;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + Math.cos(angle) * radius, cy + Math.sin(angle) * radius);
      ctx.strokeStyle = "rgba(16,24,32,0.12)";
      ctx.stroke();
    }
    ctx.fillStyle = "#4a5d6e";
    ctx.font = "650 12px Manrope, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    for (let i = 0; i < sides; i++) {
      const angle = -Math.PI / 2 + (i * 2 * Math.PI) / sides;
      const lx = cx + Math.cos(angle) * (radius + 28);
      const ly = cy + Math.sin(angle) * (radius + 28);
      ctx.fillText(labels[i], lx, ly);
    }

    contenders.slice(0, 4).forEach((car, idx) => {
      const values = car.hex_values || Object.values(car.metrics || {});
      const pts = polygonPoints(cx, cy, radius, sides, values);
      const color = COLORS[idx % COLORS.length];
      drawPath(ctx, pts, { fill: color, stroke: color, width: 2.2, alpha: 0.2 });
      drawPath(ctx, pts, { stroke: color, width: 2.2, alpha: 0.95 });
      pts.forEach(([x, y]) => {
        ctx.beginPath();
        ctx.arc(x, y, 3.2, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
      });
    });
  }

  function renderLegend(contenders) {
    els.legend.innerHTML = "";
    contenders.slice(0, 4).forEach((car, idx) => {
      const li = document.createElement("li");
      const label = `${car.year} ${car.make} ${car.model}`;
      li.innerHTML = `
        <img class="legend-thumb" src="${carImage(car)}" alt="" />
        <span class="swatch" style="background:${COLORS[idx % COLORS.length]}"></span>
        <span>${label} · $${Number(car.price).toLocaleString()} · ${car.overall}/10</span>`;
      els.legend.appendChild(li);
    });
  }

  function applyPayload(payload) {
    sessionId = payload.session_id;
    if (payload.group || payload.dealer) applyBranding(payload.group || payload.dealer);
    setModeBadge(payload);
    if (payload.reply) addBubble("assistant", payload.reply);
    const stageId = (payload.stage && payload.stage.stage) || (payload.prefs && payload.prefs.stage) || "budget";
    renderSteps(stageId);
    renderChoices(payload.stage);
    lastContenders = payload.contenders || [];
    const hasCars = lastContenders.length > 0;
    setCompareVisibility(hasCars);
    if (hasCars) {
      els.radarSub.textContent =
        lastContenders.length === 1
          ? "Here’s your top match on the chart."
          : `${lastContenders.length} options scored on six traits.`;
      drawRadar(lastContenders);
      renderGallery(lastContenders);
      renderLegend(lastContenders);
      renderBest(lastContenders, payload.prefs);
    } else {
      els.radarSub.textContent = "Answer a few questions — matches show up here.";
    }
    if (payload.roi) renderRoi(payload.roi);
  }

  function money(n) {
    return `$${Number(n).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
  }

  function renderRoi(roi) {
    if (!roi) return;
    const payback =
      roi.years_to_roi == null
        ? "Doesn’t break even"
        : roi.years_to_roi === 0
          ? "Pays off day one"
          : `${roi.years_to_roi} years`;
    const evLabel = (roi.ev_car && roi.ev_car.label) || "Electric";
    const gasLabel = (roi.gas_car && roi.gas_car.label) || "Gas";
    const evImg = (roi.ev_car && roi.ev_car.image) || "";
    const gasImg = (roi.gas_car && roi.gas_car.image) || "";
    const photos =
      evImg || gasImg
        ? `<div class="roi-pair-photos">
            <figure>${evImg ? `<img src="${evImg}" alt="${evLabel}" />` : ""}<figcaption>${evLabel}</figcaption></figure>
            <figure>${gasImg ? `<img src="${gasImg}" alt="${gasLabel}" />` : ""}<figcaption>${gasLabel}</figcaption></figure>
          </div>`
        : "";
    els.roiResult.innerHTML = `
      ${photos}
      <h3>Time to break even</h3>
      <div class="payback">${payback}</div>
      <ul class="roi-metrics">
        <li>Extra you pay upfront<strong>${money(roi.upfront_premium)}</strong></li>
        <li>You save each year<strong>${money(roi.annual_total_savings)}</strong></li>
        <li>Fuel / energy<strong>${money(roi.annual_fuel_savings)}</strong></li>
        <li>Maintenance<strong>${money(roi.annual_maintenance_savings)}</strong></li>
        <li>After 5 years<strong>${roi.savings_at_5_years == null ? "—" : money(roi.savings_at_5_years)}</strong></li>
        <li>EV energy / year<strong>${money(roi.annual_ev_energy_cost)}</strong></li>
      </ul>
      <p class="roi-verdict">${roi.verdict || ""}</p>
    `;
  }

  async function runRoiCalculator(e) {
    e.preventDefault();
    const pair = els.roiPair.value;
    const body = {
      miles_per_year: Number(document.getElementById("roi-miles").value),
      gas_price_per_gallon: Number(document.getElementById("roi-gas-rate").value),
      electricity_rate_per_kwh: Number(document.getElementById("roi-elec").value),
      incentive: Number(document.getElementById("roi-incentive").value),
      home_charger_cost: Number(document.getElementById("roi-charger").value),
      annual_maintenance_delta: Number(document.getElementById("roi-maint").value),
    };
    Object.assign(body, tenantBody());
    if (pair === "custom") {
      body.ev_price = Number(document.getElementById("roi-ev-price").value);
      body.gas_price = Number(document.getElementById("roi-gas-price").value);
      body.gas_mpg = 30;
      body.ev_kwh_per_100mi = 30;
    } else {
      const [evId, gasId] = pair.split("|");
      body.ev_car_id = evId;
      body.gas_car_id = gasId;
    }
    const res = await fetch("/api/roi", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) {
      els.roiResult.innerHTML = `<div class="roi-empty"><h3>Couldn’t calculate</h3><p>${data.detail || "Check the numbers and try again."}</p></div>`;
      return;
    }
    renderRoi(data);
  }

  async function startSession() {
    els.messages.innerHTML = "";
    const res = await fetch("/api/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(tenantBody()),
    });
    const data = await res.json();
    applyPayload(data);
    loadRoiPairs().catch(() => {});
  }

  async function sendChat(message) {
    addBubble("user", message);
    els.input.value = "";
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(tenantBody({ message, session_id: sessionId })),
    });
    const data = await res.json();
    applyPayload(data);
  }

  async function sendChoice(stage, value, label) {
    addBubble("user", label || String(value));
    const res = await fetch("/api/choice", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(tenantBody({ session_id: sessionId, stage, value })),
    });
    const data = await res.json();
    applyPayload(data);
  }

  els.form.addEventListener("submit", (e) => {
    e.preventDefault();
    const msg = els.input.value.trim();
    if (!msg) return;
    sendChat(msg);
  });

  els.resetBtn.addEventListener("click", () => startSession());
  els.askEvBtn.addEventListener("click", () => {
    sendChat(
      "Honest take: EV vs gas for someone like me — charging, running costs, upkeep, incentives, cold weather, and resale. Then estimate break-even for Model 3 vs Camry at 12,000 miles/year."
    );
  });
  els.roiPair.addEventListener("change", () => {
    els.customPrices.classList.toggle("hidden", els.roiPair.value !== "custom");
  });
  els.roiForm.addEventListener("submit", runRoiCalculator);
  els.roiToggle.addEventListener("click", () => {
    const collapsed = els.roiPanel.classList.toggle("is-collapsed");
    els.roiToggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
  });

  startSession().catch((err) => {
    addBubble("assistant", `Couldn’t start — ${err.message}. Refresh and try again.`);
  });
})();
