/* ═══════════════════════════════════════════════════════════════════════════
   Pro Stock Analyzer — Frontend Logic
   Fetches from /api, renders scorecard + tabs + ratio grid + chart
   ═══════════════════════════════════════════════════════════════════════════ */

const API = ""; // same-origin (FastAPI serves both API and static)

const $ = (id) => document.getElementById(id);
const el = (tag, cls, txt) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (txt !== undefined) e.textContent = txt;
  return e;
};

// ═══════════════════════════════════════════════════════════════════════
// State
// ═══════════════════════════════════════════════════════════════════════
const state = {
  categories: [],
  symbols: [],
  currentResult: null,
  activeTab: null,
  trendChart: null,
};

// ═══════════════════════════════════════════════════════════════════════
// Boot
// ═══════════════════════════════════════════════════════════════════════
async function boot() {
  await checkHealth();
  await loadCategories();
  await loadSymbols();
  wireEvents();
}

async function checkHealth() {
  try {
    const res = await fetch(`${API}/api/health`);
    if (res.ok) {
      $("statusDot").classList.add("ok");
      $("statusText").textContent = "Connected";
      return;
    }
  } catch (_) {}
  $("statusDot").classList.add("err");
  $("statusText").textContent = "Disconnected";
}

async function loadCategories() {
  try {
    const res = await fetch(`${API}/api/categories`);
    const data = await res.json();
    state.categories = data.categories;

    // Render preview grid on empty view
    const preview = $("categoriesPreview");
    preview.innerHTML = "";
    state.categories.forEach((c) => {
      const card = el("div", "cat-preview-item");
      card.appendChild(el("div", "cat-preview-en", c.label_en));
      card.appendChild(el("div", "cat-preview-th", c.label_th));
      preview.appendChild(card);
    });
  } catch (err) {
    console.error("loadCategories failed", err);
  }
}

async function loadSymbols() {
  try {
    const res = await fetch(`${API}/api/symbols`);
    const data = await res.json();
    state.symbols = data.symbols || [];

    const chips = $("symbolChips");
    chips.innerHTML = "";
    // show up to 12 popular chips
    const display = state.symbols.slice(0, 12);
    if (display.length === 0) {
      // Show suggested symbols even when none cached
      ["AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "AMD"].forEach((s) => {
        const chip = el("div", "symbol-chip", s);
        chip.onclick = () => { $("symbolInput").value = s; runAnalysis(); };
        chips.appendChild(chip);
      });
    } else {
      display.forEach((s) => {
        const chip = el("div", "symbol-chip", s);
        chip.onclick = () => { $("symbolInput").value = s; runAnalysis(); };
        chips.appendChild(chip);
      });
    }
  } catch (err) {
    console.error("loadSymbols failed", err);
  }
}

function wireEvents() {
  $("analyzeBtn").onclick = runAnalysis;
  $("symbolInput").addEventListener("keypress", (e) => {
    if (e.key === "Enter") runAnalysis();
  });
}

// ═══════════════════════════════════════════════════════════════════════
// Analysis
// ═══════════════════════════════════════════════════════════════════════
async function runAnalysis() {
  const symbol = $("symbolInput").value.trim().toUpperCase();
  if (!symbol) return;

  showView("loading");

  try {
    const res = await fetch(`${API}/api/analyze/${symbol}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    const data = await res.json();
    state.currentResult = data;
    renderResults(data);
    showView("results");
  } catch (err) {
    $("errorMessage").textContent = err.message || String(err);
    showView("error");
  }
}

function showView(name) {
  ["empty", "loading", "results", "error"].forEach((v) => {
    const node = $(`${v}View`);
    if (node) node.classList.toggle("hidden", v !== name);
  });
}

// ═══════════════════════════════════════════════════════════════════════
// Render
// ═══════════════════════════════════════════════════════════════════════
function renderResults(r) {
  // Scorecard
  $("stockSymbol").textContent = r.symbol;
  $("stockName").textContent = r.name || r.symbol;
  $("stockSector").textContent = r.sector || "—";
  $("stockIndustry").textContent = r.industry || "—";
  $("stockPrice").textContent = r.current_price
    ? `$${Number(r.current_price).toLocaleString(undefined, { maximumFractionDigits: 2 })}`
    : "—";

  // Signal
  const sig = $("signalValue");
  sig.textContent = (r.signal || "HOLD").replace("_", " ");
  sig.className = "signal-value " + (r.signal || "HOLD");
  $("signalValueTh").textContent = r.signal_th || "";

  // Composite score (animate the circle)
  const score = Number(r.composite_score) || 0;
  $("scoreNumber").textContent = score.toFixed(1);
  const scoreFg = $("scoreFg");
  const circumference = 282.7;   // 2π × 45
  const offset = circumference * (1 - score / 100);
  requestAnimationFrame(() => {
    scoreFg.style.strokeDashoffset = offset;
  });

  // Narrative
  $("narrativeEn").textContent = r.narrative_en || "—";
  $("narrativeTh").textContent = r.narrative_th || "—";

  // Sub-scores
  renderSubScores(r.sub_scores || {});

  // Summary stats
  $("totalRatios").textContent = r.total_ratios || 0;
  $("totalCategories").textContent = (r.categories_computed || []).length;
  $("totalYears").textContent = Object.keys(r.years || {}).length;
  $("latestYear").textContent = r.latest_year || "—";

  // Tabs + first category
  renderTabs(r);

  // Chart
  renderChart(r);
}

function renderSubScores(subs) {
  Object.entries(subs).forEach(([key, val]) => {
    const bar = $(`score-${key}`);
    const valEl = $(`score-${key}-val`);
    if (bar) {
      setTimeout(() => { bar.style.width = `${Math.max(0, Math.min(100, val))}%`; }, 100);
    }
    if (valEl) valEl.textContent = val.toFixed(1);
  });
}

// ═══════════════════════════════════════════════════════════════════════
// Tabs + Ratio Grid
// ═══════════════════════════════════════════════════════════════════════
function renderTabs(r) {
  const tabs = $("categoryTabs");
  tabs.innerHTML = "";

  const active = state.activeTab || (r.categories_computed || [])[0];
  state.activeTab = active;

  (r.categories_computed || []).forEach((cat) => {
    const catInfo = state.categories.find((c) => c.id === cat);
    if (!catInfo) return;

    const ratios = r.latest_by_category?.[cat] || {};
    const nonNull = Object.values(ratios).filter((v) => v !== null && v !== undefined).length;

    const tab = el("div", "tab" + (cat === active ? " active" : ""));
    tab.innerHTML = `
      ${catInfo.label_en} <span style="opacity:.5;font-family:var(--font-mono);font-size:11px">${nonNull}</span>
      <span class="tab-th">${catInfo.label_th}</span>
    `;
    tab.onclick = () => {
      state.activeTab = cat;
      renderTabs(r);
      renderRatioGrid(cat, r);
    };
    tabs.appendChild(tab);
  });

  renderRatioGrid(active, r);
}

function renderRatioGrid(category, r) {
  const grid = $("ratioGrid");
  grid.innerHTML = "";

  const ratios = r.latest_by_category?.[category] || {};
  const keys = Object.keys(ratios).filter((k) => !k.startsWith("_"));  // skip metadata

  if (keys.length === 0) {
    grid.innerHTML = `<div class="ratio-card"><div class="ratio-name">No ratios in this category</div></div>`;
    return;
  }

  keys.forEach((name) => {
    const value = ratios[name];
    const card = el("div", "ratio-card");
    card.appendChild(el("div", "ratio-name", name));

    let valTxt, cls = "ratio-value";
    if (value === null || value === undefined) {
      valTxt = "N/A";
      cls += " null";
    } else if (typeof value === "number") {
      valTxt = formatValue(value, name);
      // Positive/negative coloring for growth/margin fields
      if (/margin|growth|return|yield|roe|roa|roic/i.test(name)) {
        cls += value >= 0 ? " positive" : " negative";
      }
    } else {
      valTxt = String(value);
    }
    card.appendChild(el("div", cls, valTxt));
    grid.appendChild(card);
  });
}

function formatValue(v, name) {
  // Big numbers get thousand separators
  const abs = Math.abs(v);
  if (abs >= 1_000_000_000) return (v / 1_000_000_000).toFixed(2) + "B";
  if (abs >= 1_000_000) return (v / 1_000_000).toFixed(2) + "M";
  if (abs >= 10_000) return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
  if (abs < 0.01 && v !== 0) return v.toExponential(2);
  return v.toFixed(2);
}

// ═══════════════════════════════════════════════════════════════════════
// Trend Chart
// ═══════════════════════════════════════════════════════════════════════
function renderChart(r) {
  // Get all unique ratio names from the current active tab
  const active = state.activeTab;
  const years = Object.keys(r.years || {}).sort();
  if (!years.length) return;

  // Collect available ratios for the active tab
  const ratioSet = new Set();
  years.forEach((y) => {
    const cats = r.years[y].categories || {};
    Object.keys(cats[active] || {}).forEach((k) => {
      if (!k.startsWith("_")) ratioSet.add(k);
    });
  });

  const ratios = Array.from(ratioSet).sort();
  const selector = $("chartRatioSelector");
  selector.innerHTML = "";
  ratios.forEach((name) => {
    const opt = el("option", "", name);
    opt.value = name;
    selector.appendChild(opt);
  });

  const drawChart = (ratioName) => {
    const values = years.map((y) => {
      const v = r.years[y]?.categories?.[active]?.[ratioName];
      return v === null || v === undefined ? null : Number(v);
    });

    if (state.trendChart) state.trendChart.destroy();
    const ctx = document.getElementById("trendChart").getContext("2d");

    // Gradient
    const grad = ctx.createLinearGradient(0, 0, 0, 300);
    grad.addColorStop(0, "rgba(201, 168, 108, 0.4)");
    grad.addColorStop(1, "rgba(201, 168, 108, 0)");

    state.trendChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: years,
        datasets: [{
          label: ratioName,
          data: values,
          borderColor: "#c9a86c",
          borderWidth: 2.5,
          backgroundColor: grad,
          fill: true,
          tension: 0.35,
          pointBackgroundColor: "#e5c98a",
          pointBorderColor: "#0a0e1a",
          pointBorderWidth: 2,
          pointRadius: 5,
          pointHoverRadius: 7,
          spanGaps: true,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: {
              color: "#f2eee5",
              font: { family: "Inter", size: 12, weight: "500" },
              padding: 12,
            },
          },
          tooltip: {
            backgroundColor: "rgba(5, 7, 13, 0.95)",
            titleColor: "#c9a86c",
            bodyColor: "#f2eee5",
            borderColor: "rgba(201, 168, 108, 0.3)",
            borderWidth: 1,
            padding: 12,
            titleFont: { family: "Inter", size: 12, weight: "600" },
            bodyFont: { family: "JetBrains Mono", size: 13 },
          },
        },
        scales: {
          x: {
            ticks: { color: "#a8a598", font: { family: "JetBrains Mono", size: 11 } },
            grid: { color: "rgba(201, 168, 108, 0.05)" },
          },
          y: {
            ticks: { color: "#a8a598", font: { family: "JetBrains Mono", size: 11 } },
            grid: { color: "rgba(201, 168, 108, 0.05)" },
          },
        },
      },
    });
  };

  if (ratios.length > 0) {
    selector.value = ratios[0];
    drawChart(ratios[0]);
    selector.onchange = () => drawChart(selector.value);
  }
}

// ═══════════════════════════════════════════════════════════════════════
// Kickoff
// ═══════════════════════════════════════════════════════════════════════
boot();

// ═══════════════════════════════════════════════════════════════════════
// Deep Analysis
// ═══════════════════════════════════════════════════════════════════════
let currentDeep = null;
let currentLang = "th";

// Reset deep analysis when new symbol is analyzed
function resetDeepAnalysis() {
  currentDeep = null;
  $("deepContent").classList.add("hidden");
  $("deepLoading").classList.add("hidden");
  $("loadDeepBtn").classList.remove("hidden");
  $("copyDeepBtn").classList.add("hidden");
  $("downloadDeepBtn").classList.add("hidden");
}

async function loadDeepAnalysis() {
  const symbol = state.currentResult?.symbol;
  if (!symbol) return;

  $("loadDeepBtn").classList.add("hidden");
  $("deepLoading").classList.remove("hidden");

  try {
    const res = await fetch(`${API}/api/analyze/${symbol}/deep`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    currentDeep = await res.json();
    renderDeepAnalysis(currentDeep);
    $("deepLoading").classList.add("hidden");
    $("deepContent").classList.remove("hidden");
    $("copyDeepBtn").classList.remove("hidden");
    $("downloadDeepBtn").classList.remove("hidden");
  } catch (err) {
    $("deepLoading").classList.add("hidden");
    $("loadDeepBtn").classList.remove("hidden");
    alert(`Failed to load deep analysis: ${err.message}`);
  }
}

function renderDeepAnalysis(deep) {
  // Stats bar
  const stats = $("deepStats");
  const isThai = currentLang === "th";
  stats.innerHTML = `
    <div class="deep-stat">
      <div class="deep-stat-value">${deep.sections.length}</div>
      <div class="deep-stat-label">${isThai ? "หมวดการวิเคราะห์" : "Sections"}</div>
    </div>
    <div class="deep-stat">
      <div class="deep-stat-value">${deep.ratios_used_in_analysis}</div>
      <div class="deep-stat-label">${isThai ? "อัตราส่วนที่ใช้" : "Ratios Used"}</div>
    </div>
    <div class="deep-stat">
      <div class="deep-stat-value">${deep.total_available_ratios}</div>
      <div class="deep-stat-label">${isThai ? "อัตราส่วนที่มี" : "Total Available"}</div>
    </div>
  `;

  // Sections
  const container = $("deepSections");
  container.innerHTML = "";

  deep.sections.forEach((sec, i) => {
    const box = el("div", "deep-sec");

    // Header
    const header = el("div", "deep-sec-header");
    const titleWrap = el("div");
    titleWrap.style.display = "flex";
    titleWrap.style.alignItems = "baseline";

    const idx = el("span", "deep-sec-index", `#${i + 1}`);
    titleWrap.appendChild(idx);
    const title = el("div", "deep-sec-title",
                     isThai ? sec.title_th : sec.title_en);
    titleWrap.appendChild(title);
    header.appendChild(titleWrap);

    if (sec.score !== undefined) {
      const scoreBadge = el("div", "deep-sec-score",
                            `${sec.score}/100`);
      header.appendChild(scoreBadge);
    }
    box.appendChild(header);

    // Content (special handling for bull/bear)
    if (sec.id === "bull_bear") {
      const grid = el("div", "bull-bear-grid");
      const bulls = el("div", "bull-list");
      bulls.appendChild(el("div", "bull-title",
                           isThai ? "มุมมอง Bull" : "Bull Case"));
      const bullUl = el("ul");
      const bullItems = isThai ? sec.bull_case_th : sec.bull_case_en;
      bullItems.forEach(b => bullUl.appendChild(el("li", "", b)));
      bulls.appendChild(bullUl);
      grid.appendChild(bulls);

      const bears = el("div", "bear-list");
      bears.appendChild(el("div", "bear-title",
                           isThai ? "มุมมอง Bear" : "Bear Case"));
      const bearUl = el("ul");
      const bearItems = isThai ? sec.bear_case_th : sec.bear_case_en;
      bearItems.forEach(b => bearUl.appendChild(el("li", "", b)));
      bears.appendChild(bearUl);
      grid.appendChild(bears);
      box.appendChild(grid);
    } else if (sec.id === "risk_factors") {
      const risk = el("div", "risk-content");
      risk.textContent = isThai ? sec.content_th : sec.content_en;
      box.appendChild(risk);
    } else {
      const content = el("div", "deep-sec-content");
      // Convert **bold** to <strong>
      const raw = isThai ? sec.content_th : sec.content_en;
      content.innerHTML = raw.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
      box.appendChild(content);
    }

    // Metrics used footer
    if (sec.metrics_used && sec.metrics_used.length > 0) {
      const meta = el("div", "deep-sec-meta");
      const shown = sec.metrics_used.slice(0, 10);
      meta.textContent = (isThai ? "อัตราส่วนที่ใช้: " : "Metrics: ") +
                         shown.join(", ") +
                         (sec.metrics_used.length > 10 ? ` (+${sec.metrics_used.length - 10} more)` : "");
      box.appendChild(meta);
    }

    container.appendChild(box);
  });
}

function copyDeepMarkdown() {
  if (!currentDeep) return;
  const md = currentLang === "th"
    ? currentDeep.markdown_th
    : currentDeep.markdown_en;
  navigator.clipboard.writeText(md).then(() => {
    const btn = $("copyDeepBtn");
    btn.classList.add("copied");
    const original = btn.innerHTML;
    btn.innerHTML = "<span>✓</span> Copied!";
    setTimeout(() => {
      btn.classList.remove("copied");
      btn.innerHTML = original;
    }, 2000);
  });
}

function downloadDeepMarkdown() {
  if (!currentDeep) return;
  const md = currentLang === "th"
    ? currentDeep.markdown_th
    : currentDeep.markdown_en;
  const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${currentDeep.symbol}_deep_analysis_${currentLang}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

// Language toggle
function setLanguage(lang) {
  currentLang = lang;
  document.querySelectorAll(".lang-btn").forEach(b => b.classList.remove("active"));
  $("lang" + (lang === "th" ? "Th" : "En")).classList.add("active");
  if (currentDeep) renderDeepAnalysis(currentDeep);
}

// Wire up
document.addEventListener("DOMContentLoaded", () => {
  $("loadDeepBtn")?.addEventListener("click", loadDeepAnalysis);
  $("copyDeepBtn")?.addEventListener("click", copyDeepMarkdown);
  $("downloadDeepBtn")?.addEventListener("click", downloadDeepMarkdown);
  $("langTh")?.addEventListener("click", () => setLanguage("th"));
  $("langEn")?.addEventListener("click", () => setLanguage("en"));
});

// Override runAnalysis to reset deep when new symbol loaded
const _origRunAnalysis = runAnalysis;
window.runAnalysis = async function() {
  resetDeepAnalysis();
  return _origRunAnalysis.apply(this, arguments);
};
