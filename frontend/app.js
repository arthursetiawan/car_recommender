(() => {
  const COLORS = ["#c45c26", "#1f7a6c", "#3d6ea8", "#8a4f2b", "#5b7c5a", "#b45309"];

  const els = {
    messages: document.getElementById("messages"),
    choices: document.getElementById("choices"),
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
    roiForm: document.getElementById("roi-form"),
    roiPair: document.getElementById("roi-pair"),
    customPrices: document.getElementById("custom-prices"),
    roiResult: document.getElementById("roi-result"),
  };

  function carImage(car) {
    return car.image || `/static/cars/${car.id}.jpg`;
  }

  let sessionId = null;
  let lastContenders = [];

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

  function renderChoices(stage) {
    els.choices.innerHTML = "";
    if (!stage || !stage.choices || !stage.choices.length) return;
    stage.choices.forEach((choice) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "choice-chip";
      btn.textContent = choice.label;
      btn.addEventListener("click", () => sendChoice(stage.stage, choice.value, choice.label));
      els.choices.appendChild(btn);
    });
  }

  function setModeBadge(payload) {
    const mode = payload.mode === "langchain" ? "LangChain agent" : "Demo advisor";
    const key = payload.openai_configured ? " · OpenAI on" : " · no API key";
    els.modeBadge.textContent = mode + key;
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
        <h3>Best pick: ${label}</h3>
        <p>$${Number(best.price).toLocaleString()} · overall ${best.overall}/10 · ${best.summary || ""}</p>
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

    // Grid rings
    for (let ring = 1; ring <= 5; ring++) {
      const pts = polygonPoints(cx, cy, (radius * ring) / 5, sides);
      drawPath(ctx, pts, { stroke: "rgba(19,32,44,0.12)", width: 1 });
    }
    // Axes
    for (let i = 0; i < sides; i++) {
      const angle = -Math.PI / 2 + (i * 2 * Math.PI) / sides;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + Math.cos(angle) * radius, cy + Math.sin(angle) * radius);
      ctx.strokeStyle = "rgba(19,32,44,0.15)";
      ctx.stroke();
    }
    // Labels
    ctx.fillStyle = "#3d5163";
    ctx.font = "600 12px Manrope, sans-serif";
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
      drawPath(ctx, pts, { fill: color, stroke: color, width: 2.2, alpha: 0.22 });
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

  function applyPayload(payload, { silentUser } = {}) {
    sessionId = payload.session_id;
    setModeBadge(payload);
    if (!silentUser && payload.reply) addBubble("assistant", payload.reply);
    renderChoices(payload.stage);
    lastContenders = payload.contenders || [];
    if (lastContenders.length) {
      els.radarSub.textContent = `${lastContenders.length} contender${lastContenders.length === 1 ? "" : "s"} on the hex board.`;
    } else {
      els.radarSub.textContent = "Contenders appear as you narrow the field.";
    }
    drawRadar(lastContenders);
    renderGallery(lastContenders);
    renderLegend(lastContenders);
    renderBest(lastContenders, payload.prefs);
    if (payload.roi) renderRoi(payload.roi);
  }

  function money(n) {
    return `$${Number(n).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
  }

  function renderRoi(roi) {
    if (!roi) return;
    const payback =
      roi.years_to_roi == null
        ? "Does not break even"
        : roi.years_to_roi === 0
          ? "Day-one win"
          : `${roi.years_to_roi} yrs · ${roi.months_to_roi} mo`;
    const evLabel = (roi.ev_car && roi.ev_car.label) || "EV";
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
      <h3>Break-even</h3>
      <div class="payback">${payback}</div>
      <ul class="roi-metrics">
        <li>Upfront premium<strong>${money(roi.upfront_premium)}</strong></li>
        <li>Annual savings<strong>${money(roi.annual_total_savings)}</strong></li>
        <li>Fuel/energy save<strong>${money(roi.annual_fuel_savings)}</strong></li>
        <li>Maint. save<strong>${money(roi.annual_maintenance_savings)}</strong></li>
        <li>5-year net<strong>${roi.savings_at_5_years == null ? "—" : money(roi.savings_at_5_years)}</strong></li>
        <li>EV energy/yr<strong>${money(roi.annual_ev_energy_cost)}</strong></li>
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
      els.roiResult.innerHTML = `<p class="roi-placeholder">${data.detail || "ROI failed"}</p>`;
      return;
    }
    renderRoi(data);
  }

  async function startSession() {
    els.messages.innerHTML = "";
    const res = await fetch("/api/session", { method: "POST" });
    const data = await res.json();
    applyPayload(data);
  }

  async function sendChat(message) {
    addBubble("user", message);
    els.input.value = "";
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: sessionId }),
    });
    const data = await res.json();
    applyPayload(data);
  }

  async function sendChoice(stage, value, label) {
    addBubble("user", label || String(value));
    const res = await fetch("/api/choice", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, stage, value }),
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
    sendChat("EV vs gas tradeoffs — charging, fuel cost, maintenance, incentives, cold weather, and resale. Then give an ROI estimate for Model 3 vs Camry at 12,000 miles/year.");
  });
  els.roiPair.addEventListener("change", () => {
    els.customPrices.classList.toggle("hidden", els.roiPair.value !== "custom");
  });
  els.roiForm.addEventListener("submit", runRoiCalculator);

  startSession().catch((err) => {
    addBubble("assistant", `Could not start session: ${err.message}`);
  });
})();
