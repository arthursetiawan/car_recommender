(() => {
  const COLORS = ["#c45c26", "#1a7a6c", "#3d6ea8", "#8a4f2b"];
  const HEX_LABELS = ["Value", "Budget", "Reliability", "Efficiency", "Safety", "Practicality"];
  const LOCATIONS = {
    "northstar-motors": [
      { id: "downtown", name: "Downtown" },
      { id: "westside", name: "Westside" },
    ],
    "lakeside-ev": [
      { id: "harbor", name: "Harbor" },
      { id: "lakefront", name: "Lakefront" },
    ],
  };
  const META = {
    "northstar-motors": {
      name: "Northstar Motors",
      tagline: "Honest picks from our lot — no pressure.",
    },
    "lakeside-ev": {
      name: "Lakeside EV & Hybrid",
      tagline: "Find the right electric or hybrid — for your life, not our quota.",
    },
  };

  const els = {
    group: document.getElementById("group"),
    location: document.getElementById("location"),
    reset: document.getElementById("reset"),
    messages: document.getElementById("messages"),
    choices: document.getElementById("choices"),
    title: document.getElementById("dealer-title"),
    tagline: document.getElementById("dealer-tagline"),
    canvas: document.getElementById("hex"),
    legend: document.getElementById("legend"),
    best: document.getElementById("best"),
  };

  let inventory = [];
  let prefs = { stage: "budget", budget: null, body: null, priority: null, condition: null };

  function clamp(n, lo, hi) {
    return Math.max(lo, Math.min(hi, n));
  }

  function scoreCar(car, budget) {
    const price = Number(car.price) || 0;
    const market = Number(car.market_value) || price;
    const value = clamp(10 - Math.abs(price - market) / Math.max(market, 1) * 20, 1, 10);
    const budgetFit = budget
      ? clamp(10 - Math.max(0, price - budget) / budget * 18, 1, 10)
      : 6;
    const reliability = clamp(Number(car.reliability) || 7, 1, 10);
    const mpg = Number(car.mpg) || 28;
    const efficiency = car.fuel_type === "electric" ? clamp(mpg / 12, 1, 10) : clamp(mpg / 4, 1, 10);
    const safety = clamp((Number(car.safety_rating) || 4) * 2, 1, 10);
    const practicality = clamp(
      (car.seats >= 7 ? 2 : 0) +
        (["suv", "wagon", "truck"].includes(car.body_type) ? 2 : 1) +
        (car.mileage < 40000 ? 2 : 1) +
        3,
      1,
      10
    );
    const metrics = { value, budget: budgetFit, reliability, efficiency, safety, practicality };
    let overall =
      (value + budgetFit + reliability + efficiency + safety + practicality) / 6;
    if (prefs.priority === "reliability") overall = overall * 0.7 + reliability * 0.3;
    if (prefs.priority === "value") overall = overall * 0.7 + value * 0.3;
    if (prefs.priority === "efficiency") overall = overall * 0.7 + efficiency * 0.3;
    if (prefs.body && car.body_type !== prefs.body) overall -= 1.5;
    if (prefs.condition && car.condition !== prefs.condition) overall -= 0.8;
    if (budget && price > budget) overall -= 2;
    return {
      ...car,
      metrics,
      hex_values: HEX_LABELS.map((k) => metrics[k.toLowerCase()] ?? metrics[k] ?? 5),
      overall: Math.round(clamp(overall, 1, 10) * 10) / 10,
    };
  }

  // Fix hex_values mapping - metrics keys are value, budget, reliability...
  function enrich(car, budget) {
    const scored = scoreCar(car, budget);
    scored.hex_values = [
      scored.metrics.value,
      scored.metrics.budget,
      scored.metrics.reliability,
      scored.metrics.efficiency,
      scored.metrics.safety,
      scored.metrics.practicality,
    ];
    return scored;
  }

  function filteredInventory() {
    const loc = els.location.value;
    return inventory.filter((c) => !loc || c.location_id === loc || !c.location_id);
  }

  function rank(limit = 4) {
    return filteredInventory()
      .map((c) => enrich(c, prefs.budget))
      .sort((a, b) => b.overall - a.overall)
      .slice(0, limit);
  }

  function addBubble(role, text) {
    const div = document.createElement("div");
    div.className = `bubble ${role}`;
    div.textContent = text;
    els.messages.appendChild(div);
    els.messages.scrollTop = els.messages.scrollHeight;
  }

  function setChoices(items) {
    els.choices.innerHTML = "";
    items.forEach((item, i) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = item.label;
      if (i === 0 || item.primary) btn.classList.add("primary");
      btn.addEventListener("click", () => onChoice(item));
      els.choices.appendChild(btn);
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
    const sides = HEX_LABELS.length;
    for (let ring = 1; ring <= 5; ring++) {
      drawPath(ctx, polygonPoints(cx, cy, (radius * ring) / 5, sides), {
        stroke: "rgba(16,24,32,0.1)",
        width: 1,
      });
    }
    ctx.fillStyle = "#4a5d6e";
    ctx.font = "650 12px Manrope, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    for (let i = 0; i < sides; i++) {
      const angle = -Math.PI / 2 + (i * 2 * Math.PI) / sides;
      ctx.fillText(
        HEX_LABELS[i],
        cx + Math.cos(angle) * (radius + 28),
        cy + Math.sin(angle) * (radius + 28)
      );
    }
    contenders.forEach((car, idx) => {
      const color = COLORS[idx % COLORS.length];
      const pts = polygonPoints(cx, cy, radius, sides, car.hex_values);
      drawPath(ctx, pts, { fill: color, stroke: color, width: 2.2, alpha: 0.2 });
      drawPath(ctx, pts, { stroke: color, width: 2.2, alpha: 0.95 });
    });
  }

  function renderLegend(contenders) {
    els.legend.innerHTML = contenders
      .map((car, idx) => {
        const label = `${car.year} ${car.make} ${car.model}`;
        return `<li><img src="${car.image}" alt="" /><span class="swatch" style="background:${COLORS[idx % COLORS.length]}"></span><span>${label} · $${Number(car.price).toLocaleString()} · ${car.overall}/10</span></li>`;
      })
      .join("");
  }

  function renderBest(car) {
    if (!car) {
      els.best.classList.add("hidden");
      return;
    }
    els.best.classList.remove("hidden");
    els.best.innerHTML = `
      <img src="${car.image}" alt="" />
      <div>
        <h3>${car.year} ${car.make} ${car.model}</h3>
        <p>$${Number(car.price).toLocaleString()} · score ${car.overall}/10 · ${car.summary || ""}</p>
      </div>`;
  }

  function stagePrompt() {
    const n = filteredInventory().length;
    if (prefs.stage === "budget") {
      addBubble(
        "assistant",
        `Welcome — static DriveQuest demo for ${META[els.group.value].name}. ${n} vehicles on this scope. I’m not paid to close: what’s your max budget?`
      );
      setChoices([
        { label: "Under $20k", value: 20000, stage: "budget" },
        { label: "Around $25k", value: 25000, stage: "budget", primary: true },
        { label: "Up to $35k", value: 35000, stage: "budget" },
        { label: "$45k+", value: 45000, stage: "budget" },
      ]);
      return;
    }
    if (prefs.stage === "body") {
      addBubble("assistant", "What body style fits your life?");
      setChoices([
        { label: "Sedan", value: "sedan", stage: "body" },
        { label: "SUV", value: "suv", stage: "body", primary: true },
        { label: "Hatch / wagon", value: "wagon", stage: "body" },
        { label: "Any", value: "", stage: "body" },
      ]);
      return;
    }
    if (prefs.stage === "priority") {
      addBubble("assistant", "What should we weight most on the hex chart?");
      setChoices([
        { label: "Reliability", value: "reliability", stage: "priority", primary: true },
        { label: "Value / deal", value: "value", stage: "priority" },
        { label: "Efficiency", value: "efficiency", stage: "priority" },
      ]);
      return;
    }
    if (prefs.stage === "condition") {
      addBubble("assistant", "New or used?");
      setChoices([
        { label: "Used OK", value: "used", stage: "condition", primary: true },
        { label: "Prefer new", value: "new", stage: "condition" },
        { label: "Either", value: "", stage: "condition" },
      ]);
      return;
    }
    if (prefs.stage === "compare" || prefs.stage === "decide") {
      const top = rank(4);
      drawRadar(top);
      renderLegend(top);
      if (!top.length) {
        addBubble("assistant", "No cars matched this filter on the sample lot. Restart or widen location.");
        setChoices([{ label: "Restart", value: "reset", stage: "reset", primary: true }]);
        return;
      }
      const lines = top
        .map(
          (c, i) =>
            `${i + 1}. ${c.year} ${c.make} ${c.model} — $${Number(c.price).toLocaleString()} (score ${c.overall})`
        )
        .join("\n");
      addBubble("assistant", `Here are strong options from this lot:\n${lines}`);
      if (prefs.stage === "decide") {
        renderBest(top[0]);
        addBubble(
          "assistant",
          `Best match for you right now: ${top[0].year} ${top[0].make} ${top[0].model}. Full LangChain chat, Excel ingest, and ROI live in the FastAPI app — this Pages build is the thin static slice.`
        );
        setChoices([{ label: "Restart quest", value: "reset", stage: "reset", primary: true }]);
      } else {
        renderBest(null);
        setChoices([
          { label: "Show best match", value: "best", stage: "decide", primary: true },
          { label: "Restart", value: "reset", stage: "reset" },
        ]);
      }
    }
  }

  function onChoice(item) {
    if (item.stage === "reset" || item.value === "reset") {
      startQuest();
      return;
    }
    addBubble("user", item.label);
    if (item.stage === "budget") {
      prefs.budget = item.value;
      prefs.stage = "body";
    } else if (item.stage === "body") {
      prefs.body = item.value || null;
      prefs.stage = "priority";
    } else if (item.stage === "priority") {
      prefs.priority = item.value;
      prefs.stage = "condition";
    } else if (item.stage === "condition") {
      prefs.condition = item.value || null;
      prefs.stage = "compare";
    } else if (item.stage === "decide") {
      prefs.stage = "decide";
    }
    stagePrompt();
  }

  function fillLocations() {
    const locs = LOCATIONS[els.group.value] || [];
    els.location.innerHTML =
      `<option value="">All rooftops</option>` +
      locs.map((l) => `<option value="${l.id}">${l.name}</option>`).join("");
  }

  async function loadGroup() {
    const id = els.group.value;
    const meta = META[id];
    els.title.textContent = meta.name;
    els.tagline.textContent = meta.tagline;
    fillLocations();
    const res = await fetch(`data/${id}.json`);
    inventory = await res.json();
    startQuest();
  }

  function startQuest() {
    prefs = { stage: "budget", budget: null, body: null, priority: null, condition: null };
    els.messages.innerHTML = "";
    els.choices.innerHTML = "";
    renderBest(null);
    drawRadar([]);
    els.legend.innerHTML = "";
    stagePrompt();
  }

  els.group.addEventListener("change", () => loadGroup().catch(console.error));
  els.location.addEventListener("change", () => startQuest());
  els.reset.addEventListener("click", () => startQuest());
  loadGroup().catch((err) => {
    addBubble("assistant", `Couldn’t load sample inventory: ${err.message}`);
  });
})();
