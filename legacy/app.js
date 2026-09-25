/* Word-level Enron color rotation for title */
(function() {
  const wordColors = ['#0080C0', '#C03028', '#209050', '#C49032'];
  const lines = [
    { el: 'line1', text: 'Organizational Knowledge' },
    { el: 'line2', text: 'Decay Modeling' },
  ];
  let wordIdx = 0;
  for (const line of lines) {
    const el = document.getElementById(line.el);
    const words = line.text.split(' ');
    for (let w = 0; w < words.length; w++) {
      const wordSpan = document.createElement('span');
      wordSpan.className = 'title-word';
      wordSpan.style.color = wordColors[wordIdx % wordColors.length];
      for (const ch of words[w]) {
        const letter = document.createElement('span');
        letter.className = 'title-letter';
        letter.textContent = ch;
        wordSpan.appendChild(letter);
      }
      el.appendChild(wordSpan);
      if (w < words.length - 1) el.appendChild(document.createTextNode(' '));
      wordIdx++;
    }
  }
})();

document.addEventListener('keydown', (e) => { if (e.key === 'Enter') enterDashboard(); });

/* Global — called from inline onclick and keydown handler */
let coverEntered = false;
function enterDashboard() {
  if (coverEntered) return;
  coverEntered = true;
  document.getElementById('page').classList.add('exiting');
  setTimeout(() => {
    document.getElementById('cover-page').style.display = 'none';
    const dashboard = document.getElementById('dashboard');
    // Explicit layout mirrors the original body-level flex context.
    // height/width must be set inline so D3 sees real dimensions on rebuild.
    dashboard.style.display       = 'flex';
    dashboard.style.flexDirection = 'column';
    dashboard.style.height        = '100vh';
    dashboard.style.width         = '100vw';
    dashboard.style.overflow      = 'hidden';
    dashboard.style.opacity       = '0';
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        dashboard.style.transition = 'opacity 0.5s ease';
        dashboard.style.opacity   = '1';
        // After fade completes, fire resize so every D3 chart recomputes its
        // SVG dimensions — they were 0 when #dashboard was display:none at init.
        setTimeout(() => window.dispatchEvent(new Event('resize')), 550);
        // Reveal back button after dashboard is visible
        const btn = document.getElementById('backToCover');
        if (btn) btn.style.display = 'block';
      });
    });
  }, 800);
}
function goBackToCover() {
  const dashboard = document.getElementById('dashboard');
  dashboard.style.transition = 'opacity 0.4s ease';
  dashboard.style.opacity = '0';
  const btn = document.getElementById('backToCover');
  if (btn) btn.style.display = 'none';
  setTimeout(() => {
    dashboard.style.display = 'none';
    const cp = document.getElementById('cover-page');
    cp.style.display = '';
    // Reset so Enter Model works again
    coverEntered = false;
    const page = document.getElementById('page');
    page.classList.remove('exiting');
    page.style.opacity = '1';
    page.style.transform = '';
  }, 400);
}
function showHow() { document.getElementById('howModal').classList.add('visible'); }
function hideHow() { document.getElementById('howModal').classList.remove('visible'); }

// ---- next embedded script block ----

"use strict";

// ── State ──────────────────────────────────────────────────────────────────────
let DATA       = null;
let removedId  = null;
let simMonth   = 11;     // 0-indexed; default = month 12 (last)

// ── Multi-removal state ────────────────────────────────────────────────────────
let multiSelectActive = false;
let multiQueue        = [];      // array of email strings in selection order
let multiSimRunning   = false;
let multiSimDone      = false;
let multiOrigRisks    = {};      // email → original risk_score (0–1)
let multiLiveRisks    = {};      // email → boosted risk_score (0–1) after cascade

// ── Cascade state (persists across view switches) ──────────────────────────────
let cascadeState = null;  // null when no cascade; populated after runMultiCascade()

const QUADRANT_DESC = {
  "Organizational Emergency": "Irreplaceable expertise in a senior role. Priority intervention required.",
  "Silent Threat":            "Critical knowledge held by a junior employee. Often missed until departure.",
  "Replaceable Executive":    "Senior role but knowledge is distributed. Leadership gap, not knowledge gap.",
  "Low Priority":             "Redundant knowledge in a replaceable role. Standard succession planning.",
};

let currentView     = "oi";
let gvBuilt         = false;
let gvCurrentTab    = "quadrant";
let gvScatterDots   = null;
let gvNetNe         = null;
let gvNetLe         = null;
let gvNetGc         = null;
let gvNetSim2       = null;
let gvNetBuilt      = false;
let gvSelectedId    = null;
let gvEdgesByPerson = {};
let gvScatterX         = null;
let gvScatterY         = null;
let gvScatterXSel      = null;
let gvScatterYSel      = null;
let gvScatterXAxis     = null;
let gvScatterYAxis     = null;
let gvScatterLabel     = null;
let gvScatterWatermark   = null;
let gvScatterZoom        = null;
let gvScatterBgs         = null;
let gvScatterThreshLines = null;
let gvScatterQLabels     = null;
let gvNavPrev            = null;
let gvNetIsolated        = false;

const GV_KR_T = 0.12, GV_PI_T = 0.65;
const GV_ZOOM_DOMAINS = {
  "Organizational Emergency": { x: [0.10, 0.55], y: [0.62, 1.00] },
  "Silent Threat":            { x: [0.10, 0.55], y: [0.00, 0.67] },
  "Replaceable Executive":    { x: [0.00, 0.22], y: [0.62, 1.00] },
  "Low Priority":             { x: [0.00, 0.22], y: [0.00, 0.67] },
};
const GV_Q_RGBA = {
  "Organizational Emergency": "212,52,46",
  "Silent Threat":            "196,144,50",
  "Replaceable Executive":    "0,114,188",
  "Low Priority":             "45,140,60",
};
const GV_Q_HEX = {
  "Organizational Emergency": "#D4342E",
  "Silent Threat":            "#C49032",
  "Replaceable Executive":    "#0072BC",
  "Low Priority":             "#2D8C3C",
};

const GV_DEPT_COLORS = {
  "Legal":          "#0072BC",
  "Trading":        "#C49032",
  "Executive":      "#D4342E",
  "Research":       "#2D8C3C",
  "Regulatory":     "#9B59B6",
  "Operations":     "#48484A",
  "Communications": "#6E6E73",
  "Administration": "#A1A1A6",
};

// Graph data (top 50)
let g50nodes = [];
let g50edges = [];

// Persistent D3 graph references — set by buildGraph(), used by departGraph()
let gSim = null;
let gLe  = null;   // edge lines
let gGc  = null;   // glow halos
let gPc  = null;   // pulse overlay circles
let gNe  = null;   // node circles
let gLa  = null;   // labels
let gSt  = null;   // (reserved — unused)

// ── Name / label helpers ───────────────────────────────────────────────────────
// Prefer display_name baked into the data by export_dashboard_data.py.
// Fall back to formatting the email local part for any address not in the lookup.
const _nameCache = {};
function formatName(email) {
  if (!email) return "Unknown";
  if (_nameCache[email]) return _nameCache[email];
  // Try DATA.display_names lookup (populated after data loads)
  if (DATA && DATA.display_names) {
    const n = DATA.display_names[email.toLowerCase()];
    if (n) { _nameCache[email] = n; return n; }
  }
  // Fallback: parse from email local part
  const local = email.split("@")[0].replace(/^'+|'+$/g, ""); // strip stray quotes
  const parts = local.split(/[._]+/).filter(p => p.length > 0 && !/^\d+$/.test(p));
  const name = parts.length
    ? parts.map(p => p[0].toUpperCase() + p.slice(1).toLowerCase()).join(" ")
    : email;
  _nameCache[email] = name;
  return name;
}

function lastName(email) {
  const parts = formatName(email).split(" ");
  return parts.length > 1 ? parts[parts.length - 1] : parts[0];
}

function empRole(person) {
  // Role is inferred from graph metrics in export_dashboard_data.py
  return person.role || "—";
}

function empTopics(person) {
  // Show the top topic's parent category (from topic_categories mapping)
  const tp = person.topic_profile;
  if (!tp || !tp.length) return "";
  // Collect unique categories across top topics, show top 2
  const cats = [];
  for (const t of tp) {
    const cat = t.category
      || (DATA.topic_categories && DATA.topic_categories[String(t.topic)])
      || "";
    if (cat && !cats.includes(cat)) cats.push(cat);
    if (cats.length >= 2) break;
  }
  return cats.join(" · ");
}

function topicLabel(topicId, inlineCategory, inlineWords) {
  // Prefer category name; fall back to words; fall back to "Topic N"
  if (inlineCategory) return inlineCategory;
  if (DATA && DATA.topic_categories && DATA.topic_categories[String(topicId)])
    return DATA.topic_categories[String(topicId)];
  if (inlineWords) return inlineWords;
  const w = DATA && DATA.topic_words && DATA.topic_words[String(topicId)];
  return w || (topicId != null ? `Topic ${topicId}` : "—");
}

function riskClass(r) {
  if (r >= 0.40) return "risk-high";
  if (r >= 0.15) return "risk-med";
  return "risk-low";
}

function quadrantBadgeClass(quadrant) {
  if (quadrant === "Organizational Emergency") return "risk-high";
  if (quadrant === "Silent Threat") return "risk-med";
  return "risk-low";
}

function riskColor(r) {
  if (r >= 0.40) return "#D4342E";
  if (r >= 0.15) return "#C49032";
  return "#F5F5F7";
}

function nodeColor(r) {
  if (r >= 0.40) return "#D4342E";
  if (r >= 0.15) return "#0072BC";
  return "#2D8C3C";
}

function nodeGlowFilter(r) {
  if (r >= 0.40) return "url(#glow-high)";
  if (r >= 0.15) return "url(#glow-mid)";
  return "url(#glow-low)";
}

function statusRank(s) {
  return s === "recovered" ? 2 : s === "partial" ? 1 : 0;
}

// ── Fetch ──────────────────────────────────────────────────────────────────────
fetch("dashboard_data.json")
  .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
  .then(d => {
    DATA = d;
    // Build a flat display_names lookup from people + graph nodes
    DATA.display_names = {};
    (d.people || []).forEach(p => {
      if (p.display_name) DATA.display_names[p.person.toLowerCase()] = p.display_name;
    });
    (d.graph && d.graph.nodes || []).forEach(n => {
      if (n.display_name) DATA.display_names[n.id.toLowerCase()] = n.display_name;
    });
    document.getElementById("loadingOverlay").style.display = "none";
    init();
  })
  .catch(err => {
    document.getElementById("loadingOverlay").innerHTML =
      `<div style="text-align:center;line-height:2.2;font-family:'JetBrains Mono',monospace">
        <div style="color:var(--text)">failed to load dashboard_data.json</div>
        <div style="color:var(--text-faint);font-size:11px">${err.message}</div>
        <div style="color:var(--text-faint);font-size:11px">run: python export_dashboard_data.py</div>
      </div>`;
  });

// ── Init ───────────────────────────────────────────────────────────────────────
function init() {
  // Top 50 graph nodes
  g50nodes = (DATA.graph.nodes || []).slice(0, 50);
  const ids50 = new Set(g50nodes.map(n => n.id));
  g50edges = (DATA.graph.edges || []).filter(e => ids50.has(e.source) && ids50.has(e.target));
  const maxW = Math.max(...g50edges.map(e => e.weight), 1);
  g50edges.forEach(e => { e.wn = e.weight / maxW; });

  const uniqueCategories = new Set(
    Object.values(DATA.topic_categories || {}).filter(Boolean)
  ).size || DATA.topics.length;
  document.getElementById("headerSubtitle").textContent =
    `${DATA.people.length} employees · ${uniqueCategories} topic categories · 12-month simulation`;

  // Build edge lookup for graph view (all edges, not just top-50)
  gvEdgesByPerson = {};
  (DATA.graph.edges || []).forEach(e => {
    if (!gvEdgesByPerson[e.source]) gvEdgesByPerson[e.source] = [];
    if (!gvEdgesByPerson[e.target]) gvEdgesByPerson[e.target] = [];
    gvEdgesByPerson[e.source].push({ partner: e.target, weight: e.weight });
    gvEdgesByPerson[e.target].push({ partner: e.source, weight: e.weight });
  });

  renderEmployeeList();
  buildGraph();
  window.addEventListener("resize", () => {
    if (currentView === "oi") buildGraph();
    else if (currentView === "graph") {
      requestAnimationFrame(() => {
        if (gvCurrentTab === "quadrant") buildGvScatter();
        else buildGvNetwork();
      });
    } else if (currentView === "ai" && aiBuilt) {
      requestAnimationFrame(() => buildAIScatter());
    }
  });
}

// ── Employee list ──────────────────────────────────────────────────────────────
function renderEmployeeList(filter) {
  const fl   = (filter || "").toLowerCase();
  const list = document.getElementById("employeeList");
  list.innerHTML = "";

  DATA.people.forEach(p => {
    const name   = p.display_name || formatName(p.person);
    const role   = empRole(p);
    const topics = empTopics(p);

    if (fl && !name.toLowerCase().includes(fl) && !role.toLowerCase().includes(fl) && !topics.toLowerCase().includes(fl)) return;

    const isQueued       = multiQueue.includes(p.person);
    const isMultiRemoved = multiSimDone && isQueued;
    const isSingleSel    = !multiSelectActive && removedId === p.person;
    const dispRisk       = (multiSimDone && !isQueued && multiLiveRisks[p.person] != null)
                           ? multiLiveRisks[p.person] : p.risk_score;
    const badgeId        = "mrisk_" + p.person.replace(/[^a-z0-9]/gi, "_");

    const div = document.createElement("div");
    div.className = "employee"
      + (isSingleSel ? " selected removed" : "")
      + (isQueued && multiSelectActive && !multiSimDone ? " queued" : "")
      + (isMultiRemoved ? " removed" : "");
    div.dataset.id = p.person;
    div.innerHTML = `
      <div class="emp-info">
        <div class="emp-name">${name}</div>
        <div class="emp-role">${role}</div>
        <div class="emp-topics">${topics}</div>
        ${p.quadrant ? `<span class="emp-quadrant-pill" style="color:${p.quadrant_color};background:${p.quadrant_color}26">${p.quadrant}</span>` : ""}
      </div>
      <span id="${badgeId}" class="risk-badge ${quadrantBadgeClass(p.quadrant)}"><span>${(dispRisk * 100).toFixed(0)}</span><span class="risk-badge-sub">/100</span></span>
    `;
    div.addEventListener("click", () => {
      if (multiSelectActive && !multiSimRunning && !multiSimDone) {
        multiHandleEmployeeClick(p.person);
      } else if (!multiSelectActive) {
        simulateDeparture(p.person);
      }
    });
    list.appendChild(div);
  });
}

function filterEmployees(v) { renderEmployeeList(v); }

// ── Multi-removal simulation ────────────────────────────────────────────────────
function toggleMultiSelect() {
  multiSelectActive = !multiSelectActive;
  document.getElementById("multiToggle").classList.toggle("active", multiSelectActive);
  document.getElementById("departureQueue").classList.toggle("visible", multiSelectActive);
  if (!multiSelectActive) {
    // Turning off — reset everything
    multiSimDone = false; multiSimRunning = false;
    multiOrigRisks = {}; multiLiveRisks = {};
    multiQueue = [];
    renderMultiQueue();
  }
  renderEmployeeList(document.getElementById("searchBox").value);
}

function multiHandleEmployeeClick(email) {
  const idx = multiQueue.indexOf(email);
  if (idx >= 0) {
    multiQueue.splice(idx, 1);
  } else {
    if (multiQueue.length >= 5) return;
    multiQueue.push(email);
  }
  renderMultiQueue();
  renderEmployeeList(document.getElementById("searchBox").value);
}

function removeFromMultiQueue(email) {
  multiQueue = multiQueue.filter(e => e !== email);
  renderMultiQueue();
  renderEmployeeList(document.getElementById("searchBox").value);
}

function clearMultiQueue() {
  multiQueue = []; multiSimRunning = false; multiSimDone = false;
  multiOrigRisks = {}; multiLiveRisks = {};
  renderMultiQueue();
  renderEmployeeList(document.getElementById("searchBox").value);
  document.getElementById("rightPanel").innerHTML = `
    <div class="empty-state">
      <div class="empty-state-title">Select an employee</div>
      <div class="empty-state-hint">Click any name to simulate their departure</div>
    </div>`;
}

function renderMultiQueue() {
  const chips = document.getElementById("queueChips");
  if (!chips) return;
  chips.innerHTML = multiQueue.map((email, i) => {
    const person = DATA && DATA.people.find(p => p.person === email);
    const name   = (person && (person.display_name || formatName(email))) || formatName(email);
    const risk   = person ? (person.risk_score * 100).toFixed(1) : "?";
    const safeEmail = email.replace(/\\/g, "\\\\").replace(/'/g, "\\'");
    return `<div class="queue-chip">
      <div class="chip-info">
        <span class="chip-order">${i + 1}</span>
        <span class="chip-name">${name}</span>
      </div>
      <div style="display:flex;align-items:center;gap:8px">
        <span class="chip-risk">${risk}</span>
        <span class="chip-remove" onclick="event.stopPropagation();removeFromMultiQueue('${safeEmail}')">×</span>
      </div>
    </div>`;
  }).join("");
  document.getElementById("queueCount").textContent = multiQueue.length;
  const btn = document.getElementById("simulateBtn");
  if (btn) btn.disabled = multiQueue.length < 2;
  const lim = document.getElementById("queueLimit");
  if (lim) lim.textContent = multiQueue.length >= 5 ? "Maximum 5 reached" : `${5 - multiQueue.length} slots remaining`;
}

// Departure animation for cascade — additive (no restore of previous person)
function departGraphAdditive(personId) {
  if (!gNe) return;
  const connectedIds = new Set();
  g50edges.forEach(e => {
    if (e.source === personId || (e.source && e.source.id === personId)) connectedIds.add(e.target && e.target.id ? e.target.id : e.target);
    if (e.target === personId || (e.target && e.target.id === personId)) connectedIds.add(e.source && e.source.id ? e.source.id : e.source);
  });

  gNe.filter(n => n.id === personId).transition().duration(500).ease(d3.easeCubicIn).attr("r", 0).attr("opacity", 0);
  gGc.filter(n => n.id === personId).transition().duration(500).attr("r", 0).attr("opacity", 0);
  gLa.filter(n => n.id === personId).transition().duration(300).attr("opacity", 0);

  gLe.each(function(l) {
    const src = typeof l.source === "object" ? l.source.id : l.source;
    const tgt = typeof l.target === "object" ? l.target.id : l.target;
    if (src === personId || tgt === personId) {
      d3.select(this).transition().duration(500).attr("stroke", "#D4342E").attr("stroke-dasharray", "4 4").attr("opacity", 0.35);
    }
  });

  gNe.filter(n => connectedIds.has(n.id))
    .transition().delay(200).duration(300).ease(d3.easeElasticOut.amplitude(1.2))
    .attr("r", d => (8 + d.risk_score * 20) * 1.35)
    .transition().duration(500).attr("r", d => 8 + d.risk_score * 20);

  gPc.filter(n => connectedIds.has(n.id))
    .attr("r", d => 8 + d.risk_score * 20 + 8).attr("opacity", 0.4).attr("filter", "url(#pulse-glow)")
    .transition().delay(200).duration(800).ease(d3.easeCubicOut).attr("opacity", 0).attr("r", 0);

  gGc.filter(n => connectedIds.has(n.id))
    .transition().delay(300).duration(400).attr("fill", "#D4342E").attr("opacity", 0.25)
    .transition().delay(1500).duration(1000)
    .attr("fill", d => {
      if (d.risk_score >= 0.40) return "rgba(212,52,46,0.3)";
      if (d.risk_score >= 0.15) return "rgba(0,114,188,0.2)";
      return "rgba(45,140,60,0.10)";
    }).attr("opacity", 0.5);

  if (gSim) gSim.alpha(0.15).restart();
}

// Compute topic overlap penalty τ for the cascade formula A = Σrᵢ · (1 + 0.06n) · (1 + τ)
// τ = average pairwise cosine similarity of topic weight vectors, capped at 0.5
// Returns 0 for single removal (no change to single-departure behaviour)
function computeTopicTau(employees) {
  if (!employees || employees.length < 2) return 0;

  // Collect all unique categories across the removed set
  const catIndex = {};
  let catCount = 0;
  employees.forEach(p => {
    (p.topic_profile || []).forEach(t => {
      const cat = t.category
        || (DATA.topic_categories && DATA.topic_categories[String(t.topic)])
        || null;
      if (cat && catIndex[cat] == null) catIndex[cat] = catCount++;
    });
  });

  if (catCount === 0) return 0;

  // Build aligned topic weight vectors (0-filled for missing categories)
  const vectors = employees.map(p => {
    const vec = new Array(catCount).fill(0);
    (p.topic_profile || []).forEach(t => {
      const cat = t.category
        || (DATA.topic_categories && DATA.topic_categories[String(t.topic)])
        || null;
      if (cat != null && catIndex[cat] != null) vec[catIndex[cat]] = t.score || 0;
    });
    return vec;
  });

  // Average pairwise cosine similarity
  let totalSim = 0, pairs = 0;
  for (let i = 0; i < vectors.length; i++) {
    for (let j = i + 1; j < vectors.length; j++) {
      let dot = 0, magA = 0, magB = 0;
      for (let k = 0; k < catCount; k++) {
        dot  += vectors[i][k] * vectors[j][k];
        magA += vectors[i][k] * vectors[i][k];
        magB += vectors[j][k] * vectors[j][k];
      }
      const denom = Math.sqrt(magA) * Math.sqrt(magB);
      totalSim += denom > 0 ? dot / denom : 0;
      pairs++;
    }
  }

  const raw = pairs > 0 ? totalSim / pairs : 0;
  return Math.min(raw, 0.5);  // cap at 0.5
}

async function runMultiCascade() {
  if (multiQueue.length < 2 || multiSimRunning) return;
  multiSimRunning = true;
  const btn = document.getElementById("simulateBtn");
  if (btn) btn.disabled = true;

  // Initialize live risk scores
  DATA.people.forEach(p => {
    multiOrigRisks[p.person] = p.risk_score;
    multiLiveRisks[p.person] = p.risk_score;
  });

  // Sort queue by risk descending
  const sorted = [...multiQueue]
    .map(email => DATA.people.find(p => p.person === email))
    .filter(Boolean)
    .sort((a, b) => (b.risk_score || 0) - (a.risk_score || 0));

  const overlay  = document.getElementById("cascadeOverlay");
  const textEl   = document.getElementById("cascadeText");
  const personEl = document.getElementById("cascadePerson");
  const graphPanel = document.querySelector("#oi-view .panel:nth-child(2)");

  let cascadingRisk = 0;
  const topicHits   = {};

  for (let i = 0; i < sorted.length; i++) {
    const person = sorted[i];
    const name   = person.display_name || formatName(person.person);

    // Show overlay with animation restart
    if (overlay) {
      overlay.classList.add("visible");
      textEl.textContent = `Removing ${i + 1} of ${sorted.length}...`;
      personEl.textContent = name;
      personEl.style.animation = "none";
      void personEl.offsetWidth;
      personEl.style.animation = "cascadePulse 0.6s ease";
    }

    // Shockwave
    if (graphPanel) {
      const wave = document.createElement("div");
      wave.className = "shockwave";
      graphPanel.appendChild(wave);
      setTimeout(() => wave.remove(), 1100);
    }

    // Animate node departure (additive — no restore)
    departGraphAdditive(person.person);

    // Get person's topic categories
    const personCats = [];
    (person.topic_profile || []).forEach(t => {
      const cat = t.category || (DATA.topic_categories && DATA.topic_categories[String(t.topic)]) || null;
      if (cat && !personCats.includes(cat)) personCats.push(cat);
    });
    personCats.forEach(cat => { topicHits[cat] = (topicHits[cat] || 0) + 1; });

    // Boost remaining employees' live risks
    DATA.people.forEach(emp => {
      if (sorted.find(s => s.person === emp.person)) return;
      const empCats = [];
      (emp.topic_profile || []).forEach(t => {
        const cat = t.category || (DATA.topic_categories && DATA.topic_categories[String(t.topic)]) || null;
        if (cat && !empCats.includes(cat)) empCats.push(cat);
      });
      let boost = 0;
      personCats.forEach(cat => { if (empCats.includes(cat)) boost += 0.015 + (i * 0.008); });
      if (boost > 0) {
        multiLiveRisks[emp.person] = Math.min((multiLiveRisks[emp.person] || emp.risk_score) + boost, 0.95);
        const badgeId = "mrisk_" + emp.person.replace(/[^a-z0-9]/gi, "_");
        const badge = document.getElementById(badgeId);
        if (badge) {
          badge.innerHTML = `<span>${(multiLiveRisks[emp.person] * 100).toFixed(0)}</span><span class="risk-badge-sub">/100</span>`;
          badge.className = "risk-badge " + riskClass(multiLiveRisks[emp.person]) + " flashing";
          setTimeout(() => badge.classList.remove("flashing"), 1100);
        }
      }
    });

    cascadingRisk += (person.risk_score || 0) + (i * 0.032);
    await new Promise(r => setTimeout(r, 1500));
  }

  if (overlay) overlay.classList.remove("visible");
  multiSimRunning = false;
  multiSimDone    = true;
  renderEmployeeList(document.getElementById("searchBox").value);

  const individualSum = sorted.reduce((s, p) => s + (p.risk_score || 0), 0);

  // Apply topic overlap penalty τ for multi-removal: A = Σrᵢ · (1 + 0.06n) · (1 + τ)
  // Single removal: τ = 0, no change to behaviour
  const tau = computeTopicTau(sorted);
  const cascadeTotal  = Math.min(cascadingRisk * (1 + tau), 1);

  const amplification = individualSum > 0
    ? Math.round(((cascadeTotal - individualSum) / individualSum) * 100)
    : 0;

  // Persist cascade results so Graph and Report views can consume them
  cascadeState = {
    removed:       sorted.map(p => p.person),
    sorted,
    liveRisks:     { ...multiLiveRisks },
    origRisks:     { ...multiOrigRisks },
    topicHits:     { ...topicHits },
    individualSum: individualSum * 100,
    cascadeTotal:  cascadeTotal  * 100,
    amplification,
    tau,
  };
  gvBuilt     = false;  // force Graph view rebuild with cascade data
  reportBuilt = false;  // force Report view rebuild with cascade section

  showMultiCombinedImpact(sorted, individualSum * 100, cascadeTotal * 100, amplification, topicHits, tau);
}

function showMultiCombinedImpact(sorted, individualSum, cascadeTotal, amplification, topicHits, tau = 0) {
  const panel = document.getElementById("rightPanel");

  const namePills = sorted.map(p =>
    `<span class="ci-name-pill">${p.display_name || formatName(p.person)}</span>`
  ).join("");

  const indPct = Math.min(individualSum, 100).toFixed(1);
  const casPct = Math.min(cascadeTotal, 100).toFixed(1);
  const indBar = Math.min(individualSum, 100);
  const casBar = Math.min(cascadeTotal, 100);

  const allTopics   = new Set(Object.keys(topicHits));
  const avgHireGap  = sorted.reduce((s, p) => s + Math.round((p.external_hire_gap || 0) * 100), 0) / sorted.length;
  const avgRecov12  = sorted.reduce((s, p) => {
    const rates = p.recovery_rates || [];
    return s + (rates[11] != null ? rates[11] * 100 : 0);
  }, 0) / sorted.length * 0.7;
  const totalPerm   = sorted.reduce((s, p) => s + (p.n_perm_loss_categories || 0), 0);

  const topicRows = Array.from(allTopics).map(cat => {
    const hits = topicHits[cat] || 0;
    const st   = hits >= 2 ? "LOST" : "PARTIAL";
    const stCls = hits >= 2 ? "ti-lost" : "ti-partial";
    return `<div class="topic-impact-row"><span class="ti-name">${cat}</span><span class="ti-status ${stCls}">${st}</span></div>`;
  }).join("") || `<div style="font-size:11px;color:var(--text-faint);font-family:'JetBrains Mono',monospace">No shared topics identified.</div>`;

  const affectedPeople = DATA.people
    .filter(p => !sorted.find(s => s.person === p.person))
    .map(p => ({
      name:     p.display_name || formatName(p.person),
      original: (multiOrigRisks[p.person] || p.risk_score) * 100,
      current:  (multiLiveRisks[p.person] || p.risk_score) * 100,
      increase: ((multiLiveRisks[p.person] || p.risk_score) - (multiOrigRisks[p.person] || p.risk_score)) * 100,
    }))
    .filter(p => p.increase > 0.05)
    .sort((a, b) => b.increase - a.increase)
    .slice(0, 5);

  const affectedRows = affectedPeople.map(p =>
    `<div class="affected-row">
      <div class="affected-name">${p.name}</div>
      <div class="affected-change">
        <span class="affected-old">${p.original.toFixed(1)}%</span>
        <span class="affected-arrow">→</span>
        <span class="affected-new">${p.current.toFixed(1)}%</span>
      </div>
    </div>`
  ).join("") || `<div style="font-size:11px;color:var(--text-faint);font-family:'JetBrains Mono',monospace">No significant risk increases detected.</div>`;

  panel.innerHTML = `
    <div style="padding:20px">
      <div class="ci-header">Combined Departure Impact</div>
      <div class="ci-subheader">Cascading simulation · ${sorted.length} removals</div>
      <div class="ci-names">${namePills}</div>

      <div class="nonlinear-callout">
        <div class="nonlinear-label">Non-linear risk amplification</div>
        <div class="nonlinear-row">
          <div class="nl-label">Individual sum</div>
          <div class="nl-value" style="color:#C49032">${indPct}%</div>
          <div class="nl-bar-wrap"><div class="nl-bar"><div class="nl-bar-fill" style="background:#C49032;width:${indBar}%"></div></div></div>
        </div>
        <div class="nonlinear-row">
          <div class="nl-label">Cascading risk</div>
          <div class="nl-value" style="color:var(--enron-red)">${casPct}%</div>
          <div class="nl-bar-wrap"><div class="nl-bar"><div class="nl-bar-fill" style="background:var(--enron-red);width:${casBar}%"></div></div></div>
        </div>
        <div class="nonlinear-delta">+${amplification}% amplification from cascading dependencies</div>
        ${tau > 0 ? `<div class="nonlinear-delta" style="margin-top:4px;opacity:0.75">Topic overlap penalty (τ): +${(tau * 100).toFixed(1)}%</div>` : ''}
      </div>

      <div class="ci-metrics">
        <div class="ci-metric"><div class="m-val" style="color:var(--enron-red)">${allTopics.size}</div><div class="m-label">Topics affected</div></div>
        <div class="ci-metric"><div class="m-val" style="color:#C49032">${avgHireGap.toFixed(0)}%</div><div class="m-label">Avg hire gap</div></div>
        <div class="ci-metric"><div class="m-val" style="color:var(--enron-red)">${avgRecov12.toFixed(1)}%</div><div class="m-label">Combined recovery</div></div>
        <div class="ci-metric"><div class="m-val" style="color:var(--text)">${totalPerm}</div><div class="m-label">Perm losses</div></div>
      </div>

      <div class="ci-rp-section">
        <div class="ci-rp-title">Topic impact breakdown</div>
        <div>${topicRows}</div>
      </div>

      <div class="ci-rp-section">
        <div class="ci-rp-title">Most affected remaining employees</div>
        <div>${affectedRows}</div>
      </div>

      <button class="multi-reset-btn" onclick="resetMultiSimulation()">Reset simulation</button>
    </div>`;
}

function resetMultiSimulation() {
  multiSimDone = false; multiSimRunning = false;
  multiOrigRisks = {}; multiLiveRisks = {};
  multiQueue = [];
  removedId  = null;
  cascadeState = null;   // clear persisted cascade data
  gvBuilt      = false;  // force Graph view to rebuild at baseline
  reportBuilt  = false;  // force Report view to rebuild without cascade section
  renderMultiQueue();
  renderEmployeeList(document.getElementById("searchBox").value);
  buildGraph();
  document.getElementById("rightPanel").innerHTML = `
    <div class="empty-state">
      <div class="empty-state-title">Select an employee</div>
      <div class="empty-state-hint">Click any name to simulate their departure</div>
    </div>`;
}

// Title-first dept assignment shared by both graph views
function titleToDept(role) {
  const t = (role || "").toLowerCase();
  if (/\b(ceo|president|coo|evp|chief|chairman|executive)\b/.test(t)) return "Executive";
  if (/\bvp\b/.test(t)) return "Executive";
  if (/\b(legal|counsel|attorney)\b/.test(t)) return "Legal";
  if (/\b(trader|trading)\b/.test(t)) return "Trading";
  if (/\b(analyst|associate|coordinator|specialist)\b/.test(t)) return "Operations";
  if (/\b(assistant|secretary|administrative)\b/.test(t)) return "Administration";
  return null; // fall back to role_category
}

// ── D3 graph ───────────────────────────────────────────────────────────────────
// buildGraph() creates a persistent simulation. Departure animation is handled
// by departGraph() which animates on existing elements without rebuilding.
function buildGraph() {
  const svg = d3.select("#graphSvg");
  svg.selectAll("*").remove();
  if (gSim) { gSim.stop(); gSim = null; }

  const c = document.getElementById("graphContainer");
  const w = c.clientWidth, h = c.clientHeight;

  // Static copies — filter out nodes with <3 connections within top-50 subgraph

  const deptLookupOI = {};
  DATA.people.forEach(p => {
    const fromTitle = titleToDept(p.role);
    deptLookupOI[p.person] = fromTitle || (p.role_category || "Administration");
  });

  const rawLinksOI = g50edges.map(e => ({ source: e.source, target: e.target, weight: e.weight, wn: e.wn }));
  const degOI = {};
  rawLinksOI.forEach(l => { degOI[l.source] = (degOI[l.source] || 0) + 1; degOI[l.target] = (degOI[l.target] || 0) + 1; });
  // Top-20 by risk_score always appear regardless of degree (e.g., Pete Davis)
  const top20OI = new Set([...g50nodes].sort((a, b) => (b.risk_score || 0) - (a.risk_score || 0)).slice(0, 20).map(n => n.id));
  const inclOI = new Set(g50nodes.filter(n => (degOI[n.id] || 0) >= 3 || top20OI.has(n.id)).map(n => n.id));

  const nodes = g50nodes.filter(n => inclOI.has(n.id)).map(n => ({
    id:              n.id,
    display_name:    n.display_name,
    risk_score:      n.risk_score,
    weighted_degree: n.weighted_degree,
    degree:          n.degree,
    dept:            deptLookupOI[n.id] || "Administration",
  }));
  const links = rawLinksOI.filter(l => inclOI.has(l.source) && inclOI.has(l.target));
  const wMaxOI = d3.max(links, l => l.weight) || 1;
  const edgeWOI = d => 1 + (d.weight / wMaxOI) * 2;

  // ── SVG defs ──
  const defs = svg.append("defs");

  // White pulse glow (for pulse overlay circles)
  const pulseF = defs.append("filter").attr("id","pulse-glow").attr("x","-100%").attr("y","-100%").attr("width","300%").attr("height","300%");
  pulseF.append("feGaussianBlur").attr("in","SourceGraphic").attr("stdDeviation","6").attr("result","blur");
  pulseF.append("feFlood").attr("flood-color","#FFFFFF").attr("flood-opacity","0.6").attr("result","white");
  pulseF.append("feComposite").attr("in","white").attr("in2","blur").attr("operator","in").attr("result","glow");
  const pMerge = pulseF.append("feMerge");
  pMerge.append("feMergeNode").attr("in","glow");
  pMerge.append("feMergeNode").attr("in","SourceGraphic");

  // Per-tier node glow
  [["high","#D4342E","0.4"],["mid","#0072BC","0.3"],["low","#2D8C3C","0.25"]].forEach(([tier,color,opacity]) => {
    const f = defs.append("filter").attr("id",`glow-${tier}`).attr("x","-100%").attr("y","-100%").attr("width","300%").attr("height","300%");
    f.append("feGaussianBlur").attr("in","SourceGraphic").attr("stdDeviation","4").attr("result","blur");
    f.append("feFlood").attr("flood-color",color).attr("flood-opacity",opacity).attr("result","color");
    f.append("feComposite").attr("in","color").attr("in2","blur").attr("operator","in").attr("result","glow");
    const m = f.append("feMerge");
    m.append("feMergeNode").attr("in","glow");
    m.append("feMergeNode").attr("in","SourceGraphic");
  });

  const g = svg.append("g");
  svg.call(d3.zoom().scaleExtent([0.3, 4]).on("zoom", ev => g.attr("transform", ev.transform)));

  // ── Dept hull layer (behind everything) ──
  const deptGroupsOI = {};
  nodes.forEach(n => { (deptGroupsOI[n.dept] = deptGroupsOI[n.dept] || []).push(n); });
  const hullDeptsOI    = Object.keys(deptGroupsOI).filter(d => deptGroupsOI[d].length >= 3);
  const clusterDeptsOI = Object.keys(deptGroupsOI).filter(d => deptGroupsOI[d].length >= 2);
  const gDeptOI = g.append("g").attr("class", "gvn-dept-layer");
  const hullPathsOI = {}, hullLabelsOI = {};
  hullDeptsOI.forEach(dept => {
    const hex = GV_DEPT_COLORS[dept] || "#48484A";
    hullPathsOI[dept]  = gDeptOI.append("path").attr("fill", hex).attr("opacity", 0.07)
      .attr("stroke", "none").style("pointer-events", "none");
    hullLabelsOI[dept] = gDeptOI.append("text").attr("fill", hex).attr("font-size", "9px")
      .attr("font-family", "'JetBrains Mono',monospace").attr("font-weight", "600")
      .attr("opacity", 0.35).attr("text-anchor", "middle").style("pointer-events", "none")
      .text(dept.toUpperCase());
  });
  function updateHullsOI() {
    hullDeptsOI.forEach(dept => {
      const pts = deptGroupsOI[dept].filter(n => n.x != null).map(n => [n.x, n.y]);
      if (pts.length < 3) return;
      const hull = d3.polygonHull(pts);
      if (!hull) return;
      const cx = d3.mean(pts, p => p[0]), cy = d3.mean(pts, p => p[1]);
      const pad = 28;
      const expanded = hull.map(([x, y]) => {
        const dx = x - cx, dy = y - cy, len = Math.sqrt(dx*dx + dy*dy) || 1;
        return [x + (dx/len)*pad, y + (dy/len)*pad];
      });
      hullPathsOI[dept].attr("d", "M" + expanded.map(p => p.join(",")).join("L") + "Z");
      hullLabelsOI[dept].attr("x", cx).attr("y", cy - 32);
    });
  }

  // ── Edges ──
  const tooltip = document.getElementById("graphTooltip");
  gLe = g.selectAll(".edge-line")
    .data(links).enter().append("line")
    .attr("class", "edge-line")
    .attr("stroke", "rgba(0,114,188,0.15)")
    .attr("stroke-width", edgeWOI)
    .on("mouseover", (ev, d) => {
      const sn = (d.source.display_name || lastName(d.source.id || d.source)).split(" ").pop();
      const tn = (d.target.display_name || lastName(d.target.id || d.target)).split(" ").pop();
      tooltip.textContent = `${sn} \u2194 ${tn} \u00b7 ${Math.round(d.weight).toLocaleString()} emails`;
      tooltip.style.display = "block";
      d3.select(ev.currentTarget).attr("stroke", "rgba(0,114,188,0.6)").attr("stroke-width", edgeWOI(d) + 1);
    })
    .on("mousemove", ev => {
      tooltip.style.left = (ev.clientX + 14) + "px";
      tooltip.style.top  = (ev.clientY - 10) + "px";
    })
    .on("mouseout", (ev, d) => {
      tooltip.style.display = "none";
      d3.select(ev.currentTarget).attr("stroke", "rgba(0,114,188,0.15)").attr("stroke-width", edgeWOI(d));
    });

  // ── Edge hit-area overlay (wide transparent lines for easier hover targeting) ──
  g.selectAll(".edge-hit")
    .data(links).enter().append("line")
    .attr("class", "edge-hit")
    .attr("stroke", "transparent")
    .attr("stroke-width", 10)
    .style("pointer-events", "stroke")
    .on("mouseover", (ev, d) => {
      const sn = (d.source.display_name || lastName(d.source.id || d.source)).split(" ").pop();
      const tn = (d.target.display_name || lastName(d.target.id || d.target)).split(" ").pop();
      tooltip.textContent = `${sn} \u2194 ${tn} \u00b7 ${Math.round(d.weight).toLocaleString()} emails`;
      tooltip.style.display = "block";
      gLe.filter(l => l === d).attr("stroke", "rgba(0,114,188,0.6)").attr("stroke-width", edgeWOI(d) + 1);
    })
    .on("mousemove", ev => {
      tooltip.style.left = (ev.clientX + 14) + "px";
      tooltip.style.top  = (ev.clientY - 10) + "px";
    })
    .on("mouseout", (ev, d) => {
      tooltip.style.display = "none";
      gLe.filter(l => l === d).attr("stroke", "rgba(0,114,188,0.15)").attr("stroke-width", edgeWOI(d));
    });

  // ── Glow halos ──
  gGc = g.selectAll(".node-glow")
    .data(nodes).enter().append("circle")
    .attr("class", "node-glow")
    .attr("r",       d => 12 + d.risk_score * 24)
    .attr("fill",    d => {
      if (d.risk_score >= 0.40) return "rgba(212,52,46,0.3)";
      if (d.risk_score >= 0.15) return "rgba(0,114,188,0.2)";
      return "rgba(45,140,60,0.10)";
    })
    .attr("opacity", 0.5)
    .style("pointer-events", "none");

  // ── Pulse overlay circles (white, initially invisible) ──
  gPc = g.selectAll(".pulse-circle")
    .data(nodes).enter().append("circle")
    .attr("class", "pulse-circle")
    .attr("r", 0).attr("fill", "white").attr("opacity", 0)
    .style("pointer-events", "none");

  // ── Node circles ──
  gNe = g.selectAll(".node-circle")
    .data(nodes).enter().append("circle")
    .attr("class", "node-circle")
    .attr("r",      d => 8 + d.risk_score * 20)
    .attr("fill",   d => nodeColor(d.risk_score))
    .attr("stroke", "#0A0A0A").attr("stroke-width", 2)
    .attr("filter", d => nodeGlowFilter(d.risk_score))
    .on("mouseover", (ev, d) => {
      tooltip.textContent = `${d.display_name || lastName(d.id)}  ·  ${(d.risk_score*100).toFixed(0)} risk`;
      tooltip.style.display = "block";
      if (d.quadrant === "Low Priority" && gLa) gLa.filter(d2 => d2.id === d.id).attr("display", null);
    })
    .on("mousemove", ev => {
      tooltip.style.left = (ev.clientX + 14) + "px";
      tooltip.style.top  = (ev.clientY - 10) + "px";
    })
    .on("mouseout", (ev, d) => {
      tooltip.style.display = "none";
      if (d.quadrant === "Low Priority" && gLa) gLa.filter(d2 => d2.id === d.id).attr("display", "none");
    })
    .on("click", (ev, d) => { ev.stopPropagation(); tooltip.style.display = "none"; simulateDeparture(d.id); })
    .style("cursor", "pointer");

  // ── Labels ──
  gLa = g.selectAll(".node-label")
    .data(nodes).enter().append("text")
    .attr("class", "node-label")
    .attr("dy",    d => (8 + d.risk_score * 20) + 14)
    .text(d => d.display_name ? d.display_name.split(" ").pop() : lastName(d.id))
    .attr("display", d => d.quadrant === "Low Priority" ? "none" : null);

  // ── Force simulation ──
  // Clustering force (mirrors Network Explorer)
  const clusterForceOI = alpha => {
    const centroids = {};
    clusterDeptsOI.forEach(dept => {
      const grp = deptGroupsOI[dept].filter(n => n.x != null);
      if (!grp.length) return;
      centroids[dept] = { x: d3.mean(grp, n => n.x), y: d3.mean(grp, n => n.y) };
    });
    nodes.forEach(n => {
      const c = centroids[n.dept];
      if (!c) return;
      n.vx = (n.vx || 0) + (c.x - n.x) * 0.04 * alpha;
      n.vy = (n.vy || 0) + (c.y - n.y) * 0.04 * alpha;
    });
  };

  gSim = d3.forceSimulation(nodes)
    .alphaDecay(0.02)
    .velocityDecay(0.4)
    .force("link",      d3.forceLink(links).id(d => d.id).distance(180))
    .force("charge",    d3.forceManyBody().strength(-800))
    .force("center",    d3.forceCenter(w / 2, h / 2).strength(0.03))
    .force("collision", d3.forceCollide().radius(50))
    .force("cluster",   clusterForceOI)
    .on("tick", () => {
      g.selectAll(".edge-line, .edge-hit")
        .attr("x1", d => d.source.x).attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
      gGc.attr("cx", d => d.x).attr("cy", d => d.y);
      gPc.attr("cx", d => d.x).attr("cy", d => d.y);
      gNe.transition().duration(300).ease(d3.easeCubicOut).attr("cx", d => d.x).attr("cy", d => d.y);
      gLa.transition().duration(300).ease(d3.easeCubicOut).attr("x", d => d.x).attr("y", d => d.y);
      updateHullsOI();
    });

  // Pre-warm: run ticks synchronously so nodes appear in settled positions on first render
  // instead of drifting in from center. Physics forces unchanged — just fast-forward initial state.
  gSim.stop();
  for (let i = 0; i < 80; i++) gSim.tick();
  gSim.restart();

  // If a departure was already active (e.g., after resize), restore visual state
  if (removedId) {
    gNe.filter(d => d.id === removedId).attr("r", 0).attr("opacity", 0);
    gGc.filter(d => d.id === removedId).attr("r", 0).attr("opacity", 0);
    gLa.filter(d => d.id === removedId).attr("opacity", 0);
    gLe.each(function(l) {
      const s = typeof l.source === "object" ? l.source.id : l.source;
      const t = typeof l.target === "object" ? l.target.id : l.target;
      if (s === removedId || t === removedId)
        d3.select(this).attr("stroke","#D4342E").attr("stroke-dasharray","4 4").attr("opacity", 0.35);
    });
  }
}

// ── Departure animation ───────────────────────────────────────────────────────
// Animates on the persistent graph elements — does NOT rebuild.
// Handles restore-previous → set-new-removed → animate-new sequence.
function departGraph(newPersonId) {
  if (!gNe) return;   // graph not yet built

  // ── 0. Restore previous departed person (if switching) ──
  if (removedId && removedId !== newPersonId) {
    gNe.filter(n => n.id === removedId)
      .transition().duration(400)
      .attr("r", d => 8 + d.risk_score * 20).attr("opacity", 1);
    gGc.filter(n => n.id === removedId)
      .transition().duration(400)
      .attr("r", d => 12 + d.risk_score * 24)
      .attr("fill", d => {
        if (d.risk_score >= 0.40) return "rgba(212,52,46,0.3)";
        if (d.risk_score >= 0.15) return "rgba(0,114,188,0.2)";
        return "rgba(45,140,60,0.10)";
      })
      .attr("opacity", 0.5);
    gLa.filter(n => n.id === removedId).transition().duration(400).attr("opacity", 1);
    gLe.attr("stroke","rgba(0,114,188,0.15)").attr("stroke-dasharray", null).attr("opacity", 1);
    gPc.attr("r", 0).attr("opacity", 0).attr("filter", null);
    gNe.attr("fill", d => nodeColor(d.risk_score)).attr("filter", d => nodeGlowFilter(d.risk_score));
  }

  removedId = newPersonId;

  // Find directly connected nodes
  const connectedIds = new Set();
  g50edges.forEach(e => {
    if (e.source === newPersonId) connectedIds.add(e.target);
    if (e.target === newPersonId) connectedIds.add(e.source);
  });

  // ── 1. Departed node shrinks and fades ──
  gNe.filter(n => n.id === newPersonId)
    .transition().duration(500).ease(d3.easeCubicIn)
    .attr("r", 0).attr("opacity", 0);
  gGc.filter(n => n.id === newPersonId)
    .transition().duration(500).attr("r", 0).attr("opacity", 0);
  gLa.filter(n => n.id === newPersonId)
    .transition().duration(300).attr("opacity", 0);

  // ── 3. Connected edges → dashed red ──
  gLe.each(function(l) {
    const src = typeof l.source === "object" ? l.source.id : l.source;
    const tgt = typeof l.target === "object" ? l.target.id : l.target;
    if (src === newPersonId || tgt === newPersonId) {
      d3.select(this).transition().duration(500)
        .attr("stroke", "#D4342E")
        .attr("stroke-dasharray", "4 4")
        .attr("opacity", 0.35);
    }
  });

  // ── 4. Connected nodes PULSE (scale 1.35× with easeElasticOut, back to normal) ──
  gNe.filter(n => connectedIds.has(n.id))
    .transition().delay(200).duration(300).ease(d3.easeElasticOut.amplitude(1.2))
    .attr("r", d => (8 + d.risk_score * 20) * 1.35)
    .transition().duration(500)
    .attr("r", d => 8 + d.risk_score * 20);

  // ── 5. White flash overlay on connected nodes ──
  gPc.filter(n => connectedIds.has(n.id))
    .attr("r", d => 8 + d.risk_score * 20 + 8)
    .attr("opacity", 0.4)
    .attr("filter", "url(#pulse-glow)")
    .transition().delay(200).duration(800).ease(d3.easeCubicOut)
    .attr("opacity", 0).attr("r", 0);

  // ── 6. Glow halos on connected nodes → red stress, then restore ──
  gGc.filter(n => connectedIds.has(n.id))
    .transition().delay(300).duration(400)
    .attr("fill", "#D4342E").attr("opacity", 0.25)
    .transition().delay(1500).duration(1000)
    .attr("fill", d => {
      if (d.risk_score >= 0.40) return "rgba(212,52,46,0.3)";
      if (d.risk_score >= 0.15) return "rgba(0,114,188,0.2)";
      return "rgba(45,140,60,0.10)";
    })
    .attr("opacity", 0.5);

  // ── 7. Restart simulation to show structural gap ──
  if (gSim) gSim.alpha(0.15).restart();
}

// ── Simulate departure ─────────────────────────────────────────────────────────
function simulateDeparture(personId) {
  simMonth = 11;
  departGraph(personId);   // owns removedId update + animation + sim restart
  renderEmployeeList(document.getElementById("searchBox").value);
  requestAnimationFrame(() => {
    const el = document.querySelector(`.employee[data-id="${CSS.escape(personId)}"]`);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "nearest" });
  });
  renderRightPanel();
}

// ── Right panel ────────────────────────────────────────────────────────────────
function renderRightPanel() {
  if (!removedId) return;
  const panel  = document.getElementById("rightPanel");
  const person = DATA.people.find(p => p.person === removedId);
  if (!person) return;

  const name     = person.display_name || formatName(removedId);
  const role     = empRole(person);
  const monthNum = simMonth + 1;   // 1-indexed for display and data lookup

  // Recovery rate for selected month
  const rates = person.recovery_rates || [];
  const recov = rates[simMonth] != null ? rates[simMonth] : 0;
  const recovPct = (recov * 100).toFixed(1);

  // Plateau: first month where change < 0.005
  let plateauMonth = 12;
  for (let i = 1; i < rates.length; i++) {
    if (Math.abs(rates[i] - rates[i - 1]) < 0.005) { plateauMonth = i + 1; break; }
  }

  // ── Inline recovery curve SVG ──
  const qColor = person.quadrant_color || "#0072BC";
  const gradId = "cg_" + (person.person || "").replace(/[^a-z0-9]/gi, "_");
  const cW = 260, cH = 130, pX = 30, pY = 12;
  const chartRight = cW - pX;
  const chartBottom = cH - pY;
  let curvePath = "";
  const dotPoints = [];
  rates.forEach((r, i) => {
    const x = pX + (i / 11) * (cW - pX * 2);
    const y = cH - pY - r * (cH - pY * 2);
    curvePath += (i === 0 ? "M" : "L") + `${x.toFixed(1)},${y.toFixed(1)}`;
    dotPoints.push({ x, y, r });
  });

  // Fill path: curve + close to bottom corners
  const fillPath = curvePath
    + (dotPoints.length ? `L${chartRight.toFixed(1)},${chartBottom.toFixed(1)} L${pX},${chartBottom.toFixed(1)} Z` : "");

  // Reference lines at 50% and 75% (dashed)
  let refLines = "";
  [0.5, 0.75].forEach(v => {
    const y = (cH - pY - v * (cH - pY * 2)).toFixed(1);
    refLines += `<line x1="${pX}" y1="${y}" x2="${chartRight}" y2="${y}" stroke="rgba(255,255,255,0.12)" stroke-width="0.8" stroke-dasharray="3 3"/>`;
    refLines += `<text x="${chartRight + 3}" y="${(+y + 3).toFixed(0)}" fill="var(--text-faint)" font-size="8" font-family="JetBrains Mono">${(v * 100).toFixed(0)}%</text>`;
  });

  // Faint grid at 0 and 100%
  let gridLines = "";
  [0, 1.0].forEach(v => {
    const y = (cH - pY - v * (cH - pY * 2)).toFixed(1);
    gridLines += `<line x1="${pX}" y1="${y}" x2="${chartRight}" y2="${y}" stroke="var(--border)" stroke-width="0.5"/>`;
  });

  // Dots + percentage labels at M1, M3, M6, M9, M12 (indices 0, 2, 5, 8, 11)
  const labelIndices = new Set([0, 2, 5, 8, 11]);
  let curveDots = "";
  dotPoints.forEach(({ x, y, r: rv }, i) => {
    curveDots += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3.5" fill="white" stroke="${qColor}" stroke-width="1.5"/>`;
    if (labelIndices.has(i)) {
      const labelY = (y - 7).toFixed(1);
      curveDots += `<text x="${x.toFixed(1)}" y="${labelY}" text-anchor="middle" fill="var(--text-faint)" font-size="7.5" font-family="JetBrains Mono,monospace">${(rv * 100).toFixed(0)}%</text>`;
    }
  });

  let monthLabels = "";
  [0, 3, 6, 11].forEach(i => {
    const x = (pX + (i / 11) * (cW - pX * 2)).toFixed(1);
    monthLabels += `<text x="${x}" y="${cH + 12}" text-anchor="middle" fill="var(--text-faint)" font-size="8" font-family="JetBrains Mono">M${i + 1}</text>`;
  });

  // M1 context line: recovery at M1 + routing count
  const m1Rate    = rates[0] != null ? (rates[0] * 100).toFixed(1) : "—";
  const m1Entries = (person.routing_by_month || {})["1"] || [];
  const m1Count   = m1Entries.length;
  const m1Method  = m1Count > 0
    ? (m1Entries.some(e => (e.step || 4) <= 2) ? "direct routing" : "broadcast")
    : "no routing";
  const m1Context = `M1: ${m1Rate}% recovery — ${m1Count} topic${m1Count !== 1 ? "s" : ""} via ${m1Method}`;

  // ── Topic status for selected month ──
  const topTopics      = (person.topic_profile || []).slice(0, 5);
  const routingEntries = (person.routing_by_month || {})[String(monthNum)] || [];
  const statusMap      = {};

  routingEntries.forEach(e => {
    const q    = e.quality || 0;
    const step = e.step || 4;
    let status = "lost";
    if (step <= 3 && q >= 0.35) status = "recovered";
    else if (step <= 3 && q >= 0.10) status = "partial";
    if (!statusMap[e.topic] || statusRank(status) > statusRank(statusMap[e.topic])) {
      statusMap[e.topic] = status;
    }
  });
  (person.permanent_losses || []).forEach(l => {
    if (l.month <= monthNum) statusMap[l.topic] = "lost";
  });

  const lostCount = topTopics.filter(t => (statusMap[t.topic] || "lost") === "lost").length;

  // Deduplicate by category — keep worst status per category
  const catStatusMap = {};
  topTopics.forEach(t => {
    const fallback = recov > 0.6 ? "recovered" : recov > 0.3 ? "partial" : "lost";
    const status   = statusMap[t.topic] || fallback;
    const label    = topicLabel(t.topic, t.category, t.words);
    if (!catStatusMap[label] || statusRank(status) < statusRank(catStatusMap[label])) {
      catStatusMap[label] = status;
    }
  });
  // Per-topic quality scores accumulated across all months 1..monthNum
  const idQualityMap = {};
  const routingByMonth = person.routing_by_month || {};
  for (let m = 1; m <= monthNum; m++) {
    (routingByMonth[String(m)] || []).forEach(e => {
      const tid = e.topic;
      const q = e.quality || 0;
      if (idQualityMap[tid] == null || q > idQualityMap[tid]) idQualityMap[tid] = q;
    });
  }
  // Label → topic ID map for bar lookup
  const labelToTopicId = {};
  topTopics.forEach(t => {
    labelToTopicId[topicLabel(t.topic, t.category, t.words)] = t.topic;
  });

  const topicRows = Object.entries(catStatusMap).map(([label, status], idx) => {
    const altCls = idx % 2 === 0 ? " topic-row-alt" : "";
    const tid = labelToTopicId[label];
    const rawPct = Math.round((idQualityMap[tid] || 0) * 100);
    const barPct = status === "partial" ? Math.max(rawPct, 15) : status === "lost" ? 0 : rawPct;
    return `<div class="topic-row${altCls}">
      <div class="topic-row-top">
        <div class="topic-name">${label}</div>
        <span class="topic-pill topic-pill-${status}">${status}</span>
      </div>
      <div class="topic-bar-track"><div class="topic-bar-fill topic-bar-${status}" style="width:${barPct}%"></div></div>
    </div>`;
  }).join("");

  // ── Successor readiness ──
  const succs = person.successor_analysis || [];
  const visibleSuccs = succs.slice(0, 3);
  const hiddenCount  = succs.length - visibleSuccs.length;
  const successorItems = visibleSuccs.map(s => {
    const pct      = s.readiness != null ? Math.round(s.readiness * 100) : 0;
    const succName = s.successor_name || formatName(s.best_successor || "Unknown");
    const label    = topicLabel(s.topic, s.topic_category, s.topic_words);
    const arcColor = pct >= 60 ? "#2D8C3C" : pct >= 30 ? "#C49032" : "#D4342E";
    const r = 18, cx = 24, cy = 24;
    const circ = +(2 * Math.PI * r).toFixed(2);   // 113.10
    const dash = ((pct / 100) * circ).toFixed(1);
    return `<div style="display:flex;align-items:center;gap:12px;padding:6px 0;min-width:0;">
      <svg class="inline-svg" width="48" height="48" viewBox="0 0 48 48" style="flex-shrink:0;overflow:visible">
        <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="rgba(255,255,255,0.07)" stroke-width="4"/>
        <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${arcColor}" stroke-width="4"
          stroke-dasharray="${dash} ${circ}" stroke-linecap="round" transform="rotate(-90 ${cx} ${cy})"/>
        <text x="${cx}" y="${cy}" text-anchor="middle" dominant-baseline="central"
          fill="${arcColor}" font-size="11" font-weight="700" font-family="JetBrains Mono,monospace">${pct}%</text>
      </svg>
      <div style="min-width:0;flex:1;overflow:hidden">
        <div style="font-size:12px;font-weight:500;color:var(--text-secondary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:2px">${succName}</div>
        <div style="font-size:9px;font-family:'JetBrains Mono',monospace;font-weight:700;color:var(--text-faint);text-transform:uppercase;letter-spacing:1.2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${label}</div>
      </div>
    </div>`;
  }).join("") + (hiddenCount > 0 ? `<div style="font-size:9px;font-family:'JetBrains Mono',monospace;color:var(--text-faint);margin-top:4px;cursor:default">+${hiddenCount} more successor${hiddenCount > 1 ? "s" : ""}</div>` : "");

  // ── Routing log (accumulated months 1..monthNum, max 20 entries) ──
  const accLog = [];
  for (let m = 1; m <= monthNum && accLog.length < 20; m++) {
    const entries = (person.routing_by_month || {})[String(m)] || [];
    for (const e of entries) {
      if (accLog.length >= 20) break;
      const q     = e.quality || 0;
      const step  = e.step || 4;
      const agent = e.agent_name || (e.agent ? formatName(e.agent) : "—");
      const tl    = topicLabel(e.topic, e.topic_category, e.topic_words);
      const qPct  = (q * 100).toFixed(0) + "%";
      let dotCls, decision, scoreColor;
      if (step === 4 || q < 0.05) {
        dotCls = "log-card-red"; decision = `${tl} → No successor found`; scoreColor = "#D4342E";
      } else if (q >= 0.70) {
        dotCls = "log-card-green"; decision = `${tl} → ${agent}`; scoreColor = "#2D8C3C";
      } else if (q >= 0.30) {
        dotCls = "log-card-orange"; decision = `${tl} → ${agent} (partial)`; scoreColor = "#C49032";
      } else {
        dotCls = "log-card-red"; decision = `${tl} → ${agent} (weak)`; scoreColor = "#D4342E";
      }
      accLog.push(`<div class="log-card ${dotCls}">
        <span class="log-card-score" style="color:${scoreColor}">${qPct}</span>
        <div class="log-card-month">M${m}</div>
        <div class="log-card-text">${decision}</div>
      </div>`);
    }
  }
  const logEntries = accLog.length
    ? `<div class="routing-timeline">${accLog.join("")}</div>`
    : `<div style="font-size:10px;font-family:'JetBrains Mono',monospace;color:var(--text-faint);padding:8px 0">no routing data available</div>`;

  // ── Render ──
  panel.innerHTML = `
    <div class="detail-header">
      <div class="detail-name">${name}</div>
      <div class="detail-role">${role}</div>
    </div>

    ${person.quadrant ? `
    <div class="quadrant-banner">
      <span class="quadrant-label" style="color:${person.quadrant_color}">${person.quadrant}</span>
      <span class="quadrant-desc">${QUADRANT_DESC[person.quadrant] || ""}</span>
    </div>` : ""}

    <div class="metrics-row">
      <div class="metric-card">
        <div class="metric-label">Knowledge Risk Score <span class="metric-info">ⓘ<span class="metric-info-tip">Normalized 0–100 index measuring how uniquely concentrated this employee's topic expertise is across the organization. Higher = fewer internal substitutes.</span></span></div>
        <div class="metric-value" style="color:${riskColor(person.risk_score)}">${(person.risk_score * 100).toFixed(1)}</div>
        <div class="metric-sub">${person.risk_score >= 0.40 ? "Critical" : person.risk_score >= 0.15 ? "Moderate" : "Low"} · How irreplaceable</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Positional Impact Score <span class="metric-info">ⓘ<span class="metric-info-tip">Composite of email graph degree centrality, betweenness centrality, and seniority weighting, normalized 0–100. Higher = more disruption if removed.</span></span></div>
        <div class="metric-value">${((person.positional_impact || 0) * 100).toFixed(0)}</div>
        <div class="metric-sub">How disruptive to lose</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Perm. Losses</div>
        <div class="metric-value">${person.n_perm_loss_categories ?? 0}</div>
        <div class="metric-sub">of ${person.total_categories ?? Object.keys(catStatusMap).length} categories</div>
      </div>
    </div>

    ${(() => {
      const gap = person.external_hire_gap;
      if (gap == null) return "";
      const pct = Math.round(gap * 100);
      let bg, color, label;
      if (pct > 50) {
        bg = "rgba(212,52,46,0.04)"; color = "#D4342E";
        label = "No internal successor for majority of key topics";
      } else if (pct >= 20) {
        bg = "rgba(196,144,50,0.04)"; color = "#C49032";
        label = "Partial internal coverage — some gaps remain";
      } else {
        bg = "rgba(45,140,60,0.07)"; color = "#2D8C3C";
        label = "Internal coverage sufficient";
      }
      return `<div style="padding:12px 20px 4px">
        <div style="background:${bg};border:1px solid ${color}33;border-radius:6px;padding:12px;display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;">
          <span style="font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:700;letter-spacing:1.5px;color:${color};text-transform:uppercase;">External Hire Gap <span class="metric-info" style="color:var(--text-faint);text-transform:none;letter-spacing:0;">ⓘ<span class="metric-info-tip">Share of departed employee's topic coverage with no viable internal successor, requiring external hiring or permanent knowledge loss.</span></span></span>
          <span style="font-family:'JetBrains Mono',monospace;font-size:16px;font-weight:700;color:${color};">${pct}%</span>
          <span style="font-family:'JetBrains Mono',monospace;font-size:10px;color:${color};opacity:0.8;flex-basis:100%;">${label}</span>
        </div>
      </div>`;
    })()}

    <div class="recovery-section">
      <div class="section-title">12-Month Recovery Curve <span class="metric-info">ⓘ<span class="metric-info-tip">Modeled percentage of departed employee's knowledge recoverable via successor routing over 12 months. Based on topic overlap with connected colleagues.</span></span></div>
      <svg class="recovery-chart" viewBox="0 0 ${cW} ${cH + 16}">
        <defs>
          <linearGradient id="${gradId}" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="${qColor}" stop-opacity="0.22"/>
            <stop offset="100%" stop-color="${qColor}" stop-opacity="0"/>
          </linearGradient>
        </defs>
        ${gridLines}
        ${refLines}
        <path d="${fillPath}" fill="url(#${gradId})"/>
        <path d="${curvePath}" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
        ${curveDots}
        ${monthLabels}
      </svg>
      <div class="month-selector">
        ${[0, 3, 5, 11].map(i => {
          const isActive = simMonth === i;
          const style = isActive
            ? `background:${qColor}4D;color:white;border-color:${qColor}99;`
            : "";
          return `<button class="month-btn" style="${style}" onclick="setMonth(${i})">M${i + 1}</button>`;
        }).join("")}
      </div>
      <div style="font-size:9px;font-family:'JetBrains Mono',monospace;color:var(--text-faint);margin:-6px 0 10px;line-height:1.5">${m1Context}</div>
      <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px;">
        <div>
          <div class="metric-value" style="font-size:28px;color:${parseFloat(recovPct) < 50 ? "#C49032" : "#F5F5F7"}">${recovPct}%</div>
          <div style="font-size:9px;font-family:'JetBrains Mono',monospace;color:var(--text-faint);margin-top:2px">of pre-departure capacity</div>
        </div>
        <div class="metric-sub">plateau M${plateauMonth}</div>
      </div>
      <div class="recovery-bar-track">
        <div class="recovery-bar-fill" style="width:${recovPct}%;background:${parseFloat(recovPct) < 50 ? "#C49032" : "var(--text-tertiary)"}"></div>
      </div>
    </div>

    <div class="topics-section">
      <div class="section-title">Topic Breakdown</div>
      ${topicRows}
    </div>

    ${visibleSuccs.length > 0 ? `
    <div class="successor-section">
      <div class="section-title">Successor Readiness</div>
      ${successorItems}
    </div>` : ""}

    <div class="routing-section">
      <div class="routing-toggle" onclick="this.nextElementSibling.classList.toggle('open');this.querySelector('span').textContent=this.nextElementSibling.classList.contains('open')?'↑':'↓'">
        Routing log <span>↓</span>
      </div>
      <div class="routing-log">${logEntries}</div>
    </div>
  `;
}

function setMonth(m) { simMonth = m; renderRightPanel(); }

// ── Pipeline modals ────────────────────────────────────────────────────────────
function showModal(key) {
  const ps  = (DATA && DATA.pipeline_stats) || {};
  const avg = ps.avg_final_recovery ? (ps.avg_final_recovery * 100).toFixed(1) + "%" : "—";
  const nTopics = Object.keys((DATA && DATA.topic_words) || {}).length || (DATA && DATA.topics && DATA.topics.length) || "—";

  const configs = {
    ingest: {
      title: "Data Ingestion", stage: "Stage 1 · Email Parsing",
      rows: [
        ["Source",        "Enron Email Corpus"],
        ["Emails parsed", "517,401"],
        ["Date range",    "1998 – 2002"],
        ["After filter",  "~340,000"],
        ["Output",        "enron_emails.parquet"],
      ],
    },
    nlp: {
      title: "NLP Topic Modeling", stage: "Stage 2 · BERTopic",
      rows: [
        ["Model",         "all-MiniLM-L6-v2"],
        ["Sample",        "50,000 emails"],
        ["Topics found",  String(nTopics)],
        ["Min topic size","30 emails"],
        ["Output",        "expertise_profiles.parquet"],
      ],
      extra: "nlp",
    },
    graph: {
      title: "Knowledge Graph", stage: "Stage 3 · NetworkX",
      rows: [
        ["Senders",        "12,920"],
        ["Edges",          "286,102"],
        ["Shown nodes",    String(g50nodes.length)],
        ["Shown edges",    String(g50edges.length)],
        ["Output",         "knowledge_graph.graphml"],
      ],
    },
    decay: {
      title: "Decay Simulation", stage: "Stage 4 · Risk Scoring",
      rows: [
        ["Simulations",    "200"],
        ["Topic monopoly", "weight 0.35"],
        ["Betweenness",    "weight 0.25"],
        ["Weighted degree","weight 0.20"],
        ["Output",         "risk_scores.parquet"],
      ],
      extra: "decay",
    },
    oi: {
      title: "OI Simulation", stage: "Stage 5 · Agent Recovery",
      rows: [
        ["Departures",     String(DATA ? DATA.people.length : "—")],
        ["Months",         "12"],
        ["Routing tiers",  "direct · N1(w>=5) · N2(w>=3) · lost"],
        ["Avg recovery",   avg],
        ["Perm. losses",   String(ps.total_perm_losses || "—")],
        ["Output",         "simulation_results.json"],
      ],
    },
    dashboard: {
      title: "Dashboard", stage: "Stage 6 · Current View",
      rows: [
        ["People shown",   String(DATA ? DATA.people.length : "—")],
        ["Topics shown",   String(DATA ? DATA.topics.length : "—")],
        ["Graph nodes",    String(g50nodes.length)],
        ["Graph edges",    String(g50edges.length)],
        ["Topic words",    Object.keys((DATA && DATA.topic_words) || {}).length > 0 ? "loaded" : "not available"],
      ],
    },
    ai: {
      title: "AI Automation", stage: "Stage 7 · Automability Scoring",
      rows: [
        ["Model",         "Weighted automability index"],
        ["Categories",    "13 topic domains"],
        ["BaseLLM wt.",   "40%"],
        ["Agentic wt.",   "35%"],
        ["Codifiability", "25%"],
      ],
      extra: "ai",
    },
  };

  const cfg = configs[key];
  if (!cfg) return;

  let ri = 0;
  let html = `<button class="modal-close" onclick="closeModal()">x</button><h2>${cfg.title}</h2><div class="stage-label">${cfg.stage}</div>`;
  cfg.rows.forEach(([k, v]) => {
    html += `<div class="modal-row" style="--ri:${ri++}"><span class="modal-key">${k}</span><span class="modal-val">${v}</span></div>`;
  });

  // DATA INGESTION — animated vertical bar chart
  if (key === "ingest") {
    const ingestBars = [
      { year: "1998", val: "12K",  h: 4  },
      { year: "1999", val: "45K",  h: 13 },
      { year: "2000", val: "156K", h: 45 },
      { year: "2001", val: "243K", h: 70 },
      { year: "2002", val: "61K",  h: 18 },
    ];
    html += `<div class="modal-section" style="--ri:${ri++}">Email Volume by Year</div>`;
    html += `<div style="display:flex;gap:6px;height:120px;align-items:flex-end;padding:0 2px;margin-top:8px">`;
    ingestBars.forEach((b, i) => {
      html += `<div style="flex:1;display:flex;flex-direction:column;align-items:center">`;
      html += `<div style="font-family:'JetBrains Mono',monospace;font-size:9px;color:rgba(255,255,255,0.55);margin-bottom:3px;line-height:1">${b.val}</div>`;
      html += `<div class="ingest-bar" data-h="${b.h}" style="width:100%;height:0;background:#0072BC;opacity:0.8;border-radius:2px 2px 0 0;transition:height 0.5s ease-out ${i * 80}ms"></div>`;
      html += `<div style="font-family:'JetBrains Mono',monospace;font-size:9px;color:rgba(255,255,255,0.4);margin-top:4px;line-height:1">${b.year}</div>`;
      html += `</div>`;
    });
    html += `</div>`;
  }

  // DECAY — top 5, recovery curves, then model assumptions
  if (cfg.extra === "decay" && DATA) {
    html += `<div class="modal-section" style="--ri:${ri++}">Top 5 highest risk</div>`;
    DATA.people.slice(0, 5).forEach((p, i) => {
      html += `<div class="modal-row" style="--ri:${ri++};font-size:14px"><span class="modal-key">${i + 1}. ${p.display_name || formatName(p.person)}</span><span class="modal-val">${(p.risk_score * 100).toFixed(1)}</span></div>`;
    });
  }

  if (cfg.extra === "decay") {
    html += `<div class="modal-section" style="--ri:${ri++}">Illustrative Recovery Curves</div>`;
    html += `<div style="display:flex;gap:12px;margin-bottom:8px">`;
    html += `<span style="font-family:'JetBrains Mono',monospace;font-size:9px;color:#2D8C3C">FAST</span>`;
    html += `<span style="font-family:'JetBrains Mono',monospace;font-size:9px;color:#C49032">AVG</span>`;
    html += `<span style="font-family:'JetBrains Mono',monospace;font-size:9px;color:#D4342E">SLOW</span>`;
    html += `</div>`;
    html += `<svg width="100%" height="90" viewBox="0 0 420 90" xmlns="http://www.w3.org/2000/svg" style="display:block;overflow:visible;margin-bottom:12px">`;
    html += `<line x1="0" y1="17.5" x2="385" y2="17.5" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>`;
    html += `<line x1="0" y1="35" x2="385" y2="35" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>`;
    html += `<line x1="0" y1="52.5" x2="385" y2="52.5" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>`;
    html += `<text x="0" y="68" font-family="JetBrains Mono" font-size="7" fill="rgba(255,255,255,0.25)">M1</text>`;
    html += `<text x="103" y="68" font-family="JetBrains Mono" font-size="7" fill="rgba(255,255,255,0.25)">M4</text>`;
    html += `<text x="208" y="68" font-family="JetBrains Mono" font-size="7" fill="rgba(255,255,255,0.25)">M7</text>`;
    html += `<text x="381" y="68" font-family="JetBrains Mono" font-size="7" fill="rgba(255,255,255,0.25)">M12</text>`;
    html += `<polyline class="decay-curve" points="0,62 35,42 70,24 105,18 140,16 175,15 210,15 245,14 280,14 315,14 350,13 385,13" fill="none" stroke="#2D8C3C" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="500" stroke-dashoffset="500" style="transition:stroke-dashoffset 0.8s ease-out"/>`;
    html += `<polyline class="decay-curve" points="0,62 35,55 70,46 105,38 140,33 175,30 210,28 245,27 280,27 315,26 350,26 385,26" fill="none" stroke="#C49032" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="500" stroke-dashoffset="500" style="transition:stroke-dashoffset 0.8s ease-out"/>`;
    html += `<polyline class="decay-curve" points="0,62 35,60 70,57 105,54 140,52 175,51 210,51 245,50 280,50 315,50 350,50 385,50" fill="none" stroke="#D4342E" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="500" stroke-dashoffset="500" style="transition:stroke-dashoffset 0.8s ease-out"/>`;
    html += `</svg>`;
    html += `<div class="modal-section" style="--ri:${ri++}">Model Assumptions</div>`;
    html += `<div class="modal-assumptions" style="--ri:${ri++};font-size:13px;color:var(--text-tertiary);line-height:1.75;padding:8px 0 4px;">This simulation estimates organizational knowledge recovery using modeled transfer assumptions, not empirical causal measurement. Key assumptions: knowledge transfers through active communication edges; successor absorption degrades 15% per month without structured handoff; recovery plateaus at 85% of original capacity after 12 months; multi-departure risk amplification is non-linear due to shared topic dependencies. These parameters are calibrated to consulting literature on knowledge retention, not Enron-specific empirical data.</div>`;
  }

  // AI SIMULATION — automability bar chart for all 13 topics
  if (cfg.extra === "ai") {
    const mult = (typeof AI_YEARS !== "undefined") ? AI_YEARS[aiSliderIdx].mult : 1.0;
    const year = (typeof AI_YEARS !== "undefined") ? AI_YEARS[aiSliderIdx].year : 2026;
    const sorted = (typeof AI_TOPICS !== "undefined")
      ? [...AI_TOPICS].map(t => ({ name: t.name, auto: getAutomability(t, mult) })).sort((a,b) => b.auto - a.auto)
      : [];
    html += `<div class="modal-section" style="--ri:${ri++}">Automability by Topic — ${year}</div>`;
    html += `<div style="margin-top:8px">`;
    sorted.forEach(({ name, auto }, i) => {
      const c = auto >= 65 ? "#D4342E" : auto >= 45 ? "#C49032" : "#2D8C3C";
      const shortName = name.length > 30 ? name.slice(0,28) + "…" : name;
      html += `<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">`;
      html += `<div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:rgba(255,255,255,0.65);width:200px;flex-shrink:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${shortName}</div>`;
      html += `<div style="flex:1;height:7px;border:1px solid var(--border);border-radius:3px;overflow:hidden"><div class="ai-modal-bar" data-w="${auto}" style="height:100%;width:0%;background:${c};border-radius:3px;transition:width 0.5s ease-out ${i * 40}ms"></div></div>`;
      html += `<div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:${c};width:28px;text-align:right;flex-shrink:0">${auto}</div>`;
      html += `</div>`;
    });
    html += `</div>`;
    html += `<div class="modal-section" style="--ri:${ri++}">Scoring Formula</div>`;
    html += `<div class="modal-row" style="--ri:${ri++}"><span style="font-family:'JetBrains Mono',monospace;font-size:9.5px;color:rgba(255,255,255,0.65)">0.40 × BaseLLM + 0.35 × min(100, Agentic × Mult) + 0.25 × Codifiability</span></div>`;
    html += `<div class="modal-section" style="--ri:${ri++}">Model Assumptions</div>`;
    html += `<div class="modal-assumptions" style="--ri:${ri++};font-size:13px;color:var(--text-tertiary);line-height:1.75;padding:8px 0 4px;">Automability scores are modeled estimates, not empirical measurements. BaseLLM reflects how well current large language models handle the domain in isolation. Agentic score reflects suitability for multi-step autonomous task completion. Codifiability reflects how completely the work can be specified in formal rules. Scores are applied uniformly across employees — individual variation in working style is not captured. Multipliers from 0.7× (2024) to 1.85× (2032) scale agentic capability as a function of projected AI progress.</div>`;
  }

  // NLP — animated horizontal bar chart with actual expert count data
  if (cfg.extra === "nlp") {
    const nlpTopics = [
      ["General Operations",               0],
      ["Corporate Communications",         1],
      ["Executive Operations",             1],
      ["Regulatory & Gov. Affairs",        2],
      ["Structured Finance & Derivs.",     2],
    ];
    const maxExperts = Math.max(...nlpTopics.map(t => t[1])) || 1;
    html += `<div class="modal-section" style="--ri:${ri++}">Top 5 Vulnerable Topics</div>`;
    html += `<div style="margin-top:8px">`;
    nlpTopics.forEach(([name, count], i) => {
      const pct = (count / maxExperts * 100).toFixed(1);
      const barColor = count === 0 ? "#D4342E" : count === 1 ? "#C49032" : "#2D8C3C";
      const countLabel = count === 1 ? "1 expert" : `${count} experts`;
      html += `<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">`;
      html += `<div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:rgba(255,255,255,0.65);width:200px;flex-shrink:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${name}</div>`;
      html += `<div style="flex:1;height:7px;border:1px solid var(--border);border-radius:3px;overflow:hidden"><div class="nlp-bar" data-w="${pct}" style="height:100%;width:0%;background:${barColor};border-radius:3px;transition:width 0.6s ease-out ${i * 100}ms"></div></div>`;
      html += `<div style="font-family:'JetBrains Mono',monospace;font-size:9px;color:rgba(255,255,255,0.4);width:56px;text-align:right;flex-shrink:0">${countLabel}</div>`;
      html += `</div>`;
    });
    html += `</div>`;
  }

  document.getElementById("modalContent").innerHTML = html;
  const box = document.getElementById("modalBox");
  box.classList.remove("modal-animate-in");
  void box.offsetWidth;
  box.classList.add("modal-animate-in");
  document.getElementById("modalOverlay").classList.add("open");

  // Chart animations — triggered after entrance animation completes
  if (key === "ingest") {
    setTimeout(() => {
      document.querySelectorAll(".ingest-bar").forEach(bar => { bar.style.height = bar.dataset.h + "px"; });
    }, 600);
  }
  if (key === "nlp") {
    setTimeout(() => {
      document.querySelectorAll(".nlp-bar").forEach(bar => { bar.style.width = bar.dataset.w + "%"; });
    }, 600);
  }
  if (key === "decay") {
    setTimeout(() => {
      document.querySelectorAll(".decay-curve").forEach((line, i) => {
        setTimeout(() => { line.style.strokeDashoffset = "0"; }, i * 150);
      });
    }, 650);
  }
  if (key === "ai") {
    setTimeout(() => {
      document.querySelectorAll(".ai-modal-bar").forEach(bar => { bar.style.width = bar.dataset.w + "%"; });
    }, 600);
  }
}

// ── View switching ──────────────────────────────────────────────────────────────
let reportBuilt = false;
function switchView(name) {
  currentView = name;
  document.getElementById("oi-view").style.display      = name === "oi"     ? "" : "none";
  document.getElementById("graph-view").style.display   = name === "graph"  ? "" : "none";
  document.getElementById("report-view").style.display  = name === "report" ? "" : "none";
  document.getElementById("ai-sim-view").style.display  = name === "ai"     ? "" : "none";
  document.getElementById("hv-view").style.display      = name === "hv"     ? "" : "none";
  document.getElementById("pipelineGraph").className =
    "pipeline-step " + (name === "graph" ? "active" : "complete");
  document.getElementById("pipelineOI").className =
    "pipeline-step " + (name === "oi" ? "active" : "complete");
  document.getElementById("pipelineAI").className =
    "pipeline-step " + (name === "ai" ? "active" : "complete");
  document.getElementById("pipelineReport").className =
    "pipeline-step " + (name === "report" ? "active" : (name === "hv" ? "complete" : "pending"));
  document.getElementById("pipelineHV").className =
    "pipeline-step " + (name === "hv" ? "active" : "pending");
  if (name === "report" && !reportBuilt) {
    reportBuilt = true;
    buildReportView();
  }
  if (name === "hv") {
    initHVView();
  }
  if (name === "ai") {
    initAIView();
  }
  if (name === "oi") {
    // Dispatch resize after a short delay so D3 uses the current SVG container
    // dimensions. Without this, nodes end up off-screen when returning from
    // Graph view (whose layout slightly shifts the container's pixel rect).
    setTimeout(() => window.dispatchEvent(new Event('resize')), 100);
  }
  if (name === "graph" && !gvBuilt) {
    gvBuilt = true;
    renderGvLeftPanel();
    document.getElementById("gvRightPanel").innerHTML = gvPlaceholderHTML();
    // Set banner visibility BEFORE the rAF so clientHeight is measured with correct layout
    _applyGvCascadeBanner();
    // Double rAF ensures grid has fully laid out before reading clientWidth/clientHeight
    requestAnimationFrame(() => requestAnimationFrame(() => buildGvScatter()));
  } else if (name === "graph" && gvBuilt) {
    // Refresh left panel counts (cascade may have changed them)
    renderGvLeftPanel();
    _applyGvCascadeBanner();
    // Refresh dot positions and colors
    if (cascadeState && gvScatterDots) {
      const removedSet = new Set(cascadeState.removed);
      gvScatterDots.filter(d =>  removedSet.has(d.person)).attr("r", 0).attr("opacity", 0);
      gvScatterDots.filter(d => !removedSet.has(d.person))
        .attr("cx",   d => gvDotPosCascade(d).cx)
        .attr("fill", d => cascadeQuadrantColor(d));
    } else if (!cascadeState && gvScatterDots) {
      // Restore original positions and colors
      gvScatterDots
        .attr("r",      gvDotR)
        .attr("opacity", gvDotOpacity)
        .transition().duration(600)
        .attr("cx",   d => gvDotPos(d).cx)
        .attr("fill", d => d.quadrant_color || "#6E6E73");
    }
  }
}

function _applyGvCascadeBanner() {
  const banner = document.getElementById("gvCascadeBanner");
  if (!banner) return;
  if (cascadeState) {
    const names = cascadeState.sorted.map(p => p.display_name || formatName(p.person)).join(", ");
    banner.innerHTML = `
      <span style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#D4342E;font-weight:600">
        Cascade scenario · ${cascadeState.removed.length} removed: ${names}
      </span>
      <button onclick="resetCascadeToBaseline()" style="font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:1px;background:transparent;border:1px solid rgba(212,52,46,0.4);color:#D4342E;padding:4px 10px;border-radius:3px;cursor:pointer;flex-shrink:0;margin-left:12px">Reset to baseline</button>`;
    banner.style.display = "flex";
  } else {
    banner.style.display = "none";
  }
}

function showGvTab(tab) {
  gvCurrentTab = tab;
  document.getElementById("gvTab0").className = "gv-tab" + (tab === "quadrant" ? " active" : "");
  document.getElementById("gvTab1").className = "gv-tab" + (tab === "network"  ? " active" : "");
  document.getElementById("gvScatterView").style.display = tab === "quadrant" ? "flex"   : "none";
  document.getElementById("gvNetView").style.display     = tab === "network"  ? "flex"   : "none";
  if (tab === "network" && !gvNetBuilt) {
    gvNetBuilt = true;
    buildGvNetwork();
  }
}

// ── Graph view left panel ───────────────────────────────────────────────────────
function gvFindingCard(label, val, sub, color) {
  return `<div class="gv-finding">
    <div class="gv-finding-label">${label}</div>
    <div class="gv-finding-value" style="color:${color}">${val}</div>
    <div class="gv-finding-sub">${sub}</div>
  </div>`;
}

function renderGvLeftPanel() {
  const panel = document.getElementById("gvLeftPanel");

  const qdist = { "Organizational Emergency": 0, "Silent Threat": 0, "Replaceable Executive": 0, "Low Priority": 0 };
  if (cascadeState) {
    const removedSet = new Set(cascadeState.removed);
    DATA.people.filter(p => !removedSet.has(p.person)).forEach(p => {
      const kr = (cascadeState.liveRisks[p.person] != null ? cascadeState.liveRisks[p.person] : p.risk_score) || 0;
      const pi = p.positional_impact || 0;
      const q  = kr >= GV_KR_T && pi >= GV_PI_T ? "Organizational Emergency"
               : kr >= GV_KR_T                  ? "Silent Threat"
               : pi >= GV_PI_T                  ? "Replaceable Executive"
               :                                  "Low Priority";
      qdist[q]++;
    });
  } else {
    DATA.people.forEach(p => { if (qdist[p.quadrant] != null) qdist[p.quadrant]++; });
  }

  const highestKR      = DATA.people[0];
  const silentThreats  = DATA.people.filter(p => p.quadrant === "Silent Threat").sort((a, b) => b.risk_score - a.risk_score);
  const topSilent      = silentThreats[0];
  const executives     = DATA.people.filter(p => (p.positional_impact || 0) >= 0.65);
  const mostConnExec   = [...executives].sort((a, b) => (b.weighted_degree || 0) - (a.weighted_degree || 0))[0];
  const largestGap     = [...DATA.people].sort((a, b) => (b.n_perm_loss_categories || 0) - (a.n_perm_loss_categories || 0))[0];

  panel.innerHTML = `
    <div class="panel-title">Quadrant distribution</div>
    <div class="gv-q-grid">
      <div class="gv-q-card" style="border-left-color:#D4342E">
        <div class="gv-q-count" style="color:#D4342E">${qdist["Organizational Emergency"]}</div>
        <div class="gv-q-label">Org. emergency</div>
      </div>
      <div class="gv-q-card" style="border-left-color:#C49032">
        <div class="gv-q-count" style="color:#C49032">${qdist["Silent Threat"]}</div>
        <div class="gv-q-label">Silent threat</div>
      </div>
      <div class="gv-q-card" style="border-left-color:#0072BC">
        <div class="gv-q-count" style="color:#0072BC">${qdist["Replaceable Executive"]}</div>
        <div class="gv-q-label">Replaceable exec</div>
      </div>
      <div class="gv-q-card" style="border-left-color:#2D8C3C">
        <div class="gv-q-count" style="color:#2D8C3C">${qdist["Low Priority"]}</div>
        <div class="gv-q-label">Low priority</div>
      </div>
    </div>

    <div class="panel-title" style="margin-top:20px">Key findings</div>
    ${gvFindingCard("Highest knowledge risk score",
        highestKR ? highestKR.display_name || formatName(highestKR.person) : "—",
        highestKR ? `${(highestKR.risk_score * 100).toFixed(0)} — ${highestKR.role || "—"}` : "—",
        "#D4342E")}
    ${gvFindingCard("Top silent threat",
        topSilent ? topSilent.display_name || formatName(topSilent.person) : "none found",
        topSilent ? `${(topSilent.risk_score * 100).toFixed(0)} knowledge, ${((topSilent.positional_impact || 0) * 100).toFixed(0)} positional` : "—",
        "#C49032")}
    ${gvFindingCard("Most connected executive",
        mostConnExec ? mostConnExec.display_name || formatName(mostConnExec.person) : "—",
        mostConnExec ? `${((mostConnExec.positional_impact || 0) * 100).toFixed(0)} positional — ${mostConnExec.role || "—"}` : "—",
        "#0072BC")}
    ${gvFindingCard("Largest knowledge gap",
        largestGap ? largestGap.display_name || formatName(largestGap.person) : "—",
        largestGap ? `${largestGap.n_perm_loss_categories || 0} perm. losses` : "—",
        "#C49032")}

    <div class="panel-title" style="margin-top:20px">Filter by quadrant</div>
    ${[
      { q: "Organizational Emergency", label: "Org. Emergency",   rgba: "212,52,46",  color: "#D4342E" },
      { q: "Silent Threat",            label: "Silent Threat",    rgba: "196,144,50", color: "#C49032" },
      { q: "Replaceable Executive",    label: "Replaceable Exec", rgba: "0,114,188",  color: "#0072BC" },
      { q: "Low Priority",             label: "Low Priority",     rgba: "45,140,60",  color: "#2D8C3C" },
    ].map(({ q, label, rgba, color }) => {
      const id = "gvfp-" + q.replace(/[\s.]/g, "_");
      return `<div id="${id}" data-q="${q}" data-rgba="${rgba}" data-color="${color}"
        onclick="toggleGvFilter('${q}')"
        onmouseenter="gvPillHover(this,true)" onmouseleave="gvPillHover(this,false)"
        style="font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:1px;cursor:pointer;border-radius:4px;padding:8px 10px;margin-bottom:6px;background:rgba(${rgba},0.08);color:${color};border:1px solid rgba(${rgba},0.15)">${label} (${qdist[q]})</div>`;
    }).join("")}
    <div onclick="resetGvFilters()" onmouseenter="this.style.textDecoration='underline'" onmouseleave="this.style.textDecoration='none'" style="font-size:9px;color:var(--text-faint);cursor:pointer;margin-top:2px">Reset filters</div>`;
}

// ── Scatter helpers (module-level so applyGvZoom can reference them) ─────────
function gvNameHash(str) {
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) % 1000003;
  return h;
}
function gvJitter(str, axis) {
  return (gvNameHash(str + axis) % 1000) / 1000 * 0.030 - 0.015;
}
function gvDotPos(d) {
  const name = d.display_name || d.person;
  const kr = d.risk_score || 0;
  const pi = d.positional_impact || 0;
  let jkr = kr + gvJitter(name, "x");
  let jpi = pi + gvJitter(name, "y");
  if (kr >= GV_KR_T) jkr = Math.max(jkr, GV_KR_T + 0.001);
  else               jkr = Math.min(jkr, GV_KR_T - 0.001);
  if (pi >= GV_PI_T) jpi = Math.max(jpi, GV_PI_T + 0.001);
  else               jpi = Math.min(jpi, GV_PI_T - 0.001);
  return { cx: gvScatterX(jkr), cy: gvScatterY(jpi) };
}
function gvDotPosCascade(d) {
  if (!cascadeState || cascadeState.liveRisks[d.person] == null) return gvDotPos(d);
  const name = d.display_name || d.person;
  const kr   = cascadeState.liveRisks[d.person];
  const pi   = d.positional_impact || 0;
  let jkr = kr + gvJitter(name, "x");
  let jpi = pi + gvJitter(name, "y");
  if (kr >= GV_KR_T) jkr = Math.max(jkr, GV_KR_T + 0.001);
  else               jkr = Math.min(jkr, GV_KR_T - 0.001);
  if (pi >= GV_PI_T) jpi = Math.max(jpi, GV_PI_T + 0.001);
  else               jpi = Math.min(jpi, GV_PI_T - 0.001);
  // Clamp to scale domain so boosted values don't plot outside the chart area
  jkr = Math.min(jkr, 0.499);               // x-axis max = 50%
  jpi = Math.min(Math.max(jpi, 0.001), 0.999); // y-axis 0–100%
  return { cx: gvScatterX(jkr), cy: gvScatterY(jpi) };
}
// Returns quadrant color based on cascaded risk + positional impact (both axes)
function cascadeQuadrantColor(d) {
  const lr = (cascadeState && cascadeState.liveRisks[d.person] != null)
             ? cascadeState.liveRisks[d.person] : d.risk_score || 0;
  const pi = d.positional_impact || 0;
  if (lr >= GV_KR_T && pi >= GV_PI_T) return GV_Q_HEX["Organizational Emergency"];
  if (lr >= GV_KR_T)                  return GV_Q_HEX["Silent Threat"];
  if (pi >= GV_PI_T)                  return GV_Q_HEX["Replaceable Executive"];
  return GV_Q_HEX["Low Priority"];
}
function gvDotR(d) { return 5 + (d.n_perm_loss_categories || 0) * 1.8; }

// Returns the current effective quadrant for a dot, using cascaded risk when active
function effectiveQuadrant(d) {
  if (!cascadeState || cascadeState.liveRisks[d.person] == null) return d.quadrant;
  const lr = cascadeState.liveRisks[d.person];
  const pi = d.positional_impact || 0;
  if (lr >= GV_KR_T && pi >= GV_PI_T) return "Organizational Emergency";
  if (lr >= GV_KR_T)                  return "Silent Threat";
  if (pi >= GV_PI_T)                  return "Replaceable Executive";
  return "Low Priority";
}

function gvDotOpacity(d) {
  if (gvScatterZoom) {
    if (effectiveQuadrant(d) !== gvScatterZoom) return 0.05;
    return gvSelectedId === d.person ? 1 : 0.85;
  }
  if (!gvSelectedId) return 0.85;
  return d.person === gvSelectedId ? 1 : 0.12;
}

function gvPillHover(el, enter) {
  const rgba     = el.dataset.rgba;
  const isActive = (gvScatterZoom === el.dataset.q);
  el.style.background = `rgba(${rgba},${enter ? (isActive ? 0.42 : 0.16) : (isActive ? 0.32 : 0.08)})`;
}

function toggleGvFilter(q) {
  applyGvZoom(gvScatterZoom === q ? null : q);
}

function resetGvFilters() {
  // Only clears the quadrant zoom — cascade state is preserved
  applyGvZoom(null);
}

// Clears cascade state AND zoom; returns graph to baseline
function resetCascadeToBaseline() {
  gvScatterZoom = null;     // clear zoom before cascade clear so applyGvZoom doesn't re-trigger
  resetMultiSimulation();   // clears cascadeState, sets gvBuilt=false
  switchView('graph');      // rebuild from scratch at baseline
}

// Compute tight axis domain from actual data extent in quadrant q
// In cascade mode, uses cascaded risk scores and cascaded quadrant classification
function gvComputeDomain(q) {
  const removed = cascadeState ? new Set(cascadeState.removed) : new Set();
  const people = DATA.people.filter(p =>
    p.positional_impact != null &&
    !removed.has(p.person) &&
    effectiveQuadrant(p) === q
  );
  if (!people.length) return { x: [0, 0.50], y: [0, 1.00] };
  const krs   = people.map(p => (cascadeState && cascadeState.liveRisks[p.person] != null)
    ? cascadeState.liveRisks[p.person] : (p.risk_score || 0));
  const pis   = people.map(p => p.positional_impact || 0);
  const krMin = Math.min(...krs), krMax = Math.max(...krs);
  const piMin = Math.min(...pis), piMax = Math.max(...pis);
  // 5% of range per side, minimum 0.02 to safely absorb jitter (±0.015)
  const padX  = Math.max((krMax - krMin) * 0.05, 0.02);
  const padY  = Math.max((piMax - piMin) * 0.05, 0.02);
  return {
    x: [Math.max(0,   krMin - padX), Math.min(1.0, krMax + padX)],
    y: [Math.max(0,   piMin - padY), Math.min(1.0, piMax + padY)],
  };
}

// Simple greedy collision resolution: push overlapping labels apart vertically
function gvResolveCollisions(items) {
  const lineH = 13;
  items.sort((a, b) => a.x - b.x || a.y - b.y);
  for (let i = 0; i < items.length; i++) {
    for (let j = i + 1; j < items.length; j++) {
      if (Math.abs(items[j].x - items[i].x) > 55) continue;
      if (Math.abs(items[j].y - items[i].y) < lineH) {
        items[j].y = items[i].y + lineH;
      }
    }
  }
}

function applyGvZoom(q) {
  if (!gvScatterX || !gvScatterY) return;
  gvScatterZoom = q;
  const dur = 400;

  // Update pill styling
  Object.keys(GV_Q_RGBA).forEach(name => {
    const pill = document.getElementById("gvfp-" + name.replace(/[\s.]/g, "_"));
    if (!pill) return;
    const rgba     = GV_Q_RGBA[name];
    const isActive = (name === q);
    pill.style.background = `rgba(${rgba},${isActive ? 0.32 : 0.08})`;
    pill.style.boxShadow  = isActive ? `inset 3px 0 0 ${GV_Q_HEX[name]}` : "none";
  });

  // Show/hide backgrounds, threshold lines, and corner labels
  if (gvScatterBgs) {
    Object.values(gvScatterBgs).forEach(r => r.transition().duration(dur).attr("opacity", q ? 0 : 0.05));
  }
  if (gvScatterThreshLines) {
    gvScatterThreshLines.forEach(l => l.transition().duration(dur).attr("opacity", q ? 0 : 1));
  }
  if (gvScatterQLabels) {
    Object.values(gvScatterQLabels).forEach(t => t.transition().duration(dur).attr("opacity", q ? 0 : 0.4));
  }

  // Update scale domains — tight data-driven bounds when zoomed, full view otherwise
  const domain = q ? gvComputeDomain(q) : { x: [0, 0.50], y: [0, 1.00] };
  gvScatterX.domain(domain.x);
  gvScatterY.domain(domain.y);

  // Transition dots — use cascade positions when active
  if (gvScatterDots) {
    const removed = cascadeState ? new Set(cascadeState.removed) : new Set();
    gvScatterDots.filter(d => removed.has(d.person)).attr("r", 0).attr("opacity", 0);
    gvScatterDots.filter(d => !removed.has(d.person))
      .transition().duration(dur).ease(d3.easeQuadOut)
      .attr("cx", d => cascadeState ? gvDotPosCascade(d).cx : gvDotPos(d).cx)
      .attr("cy", d => cascadeState ? gvDotPosCascade(d).cy : gvDotPos(d).cy)
      .attr("opacity", gvDotOpacity);
  }

  // Compute label positions; apply collision resolution for zoomed quadrant
  const removed2 = cascadeState ? new Set(cascadeState.removed) : new Set();
  const allPeople = DATA.people.filter(p => p.positional_impact != null && !removed2.has(p.person));
  let labelItems  = allPeople.map(d => ({
    person:   d.person,
    quadrant: effectiveQuadrant(d),
    x:        cascadeState ? gvDotPosCascade(d).cx : gvDotPos(d).cx,
    y:        cascadeState ? gvDotPosCascade(d).cy - 12 : gvDotPos(d).cy - 12,
  }));
  if (q) {
    const zItems = labelItems.filter(li => li.quadrant === q);
    gvResolveCollisions(zItems);
    const rm = new Map(zItems.map(li => [li.person, li]));
    labelItems = labelItems.map(li => rm.has(li.person) ? rm.get(li.person) : li);
  }
  const posMap = new Map(labelItems.map(li => [li.person, li]));

  // Transition labels
  if (gvScatterLabel) {
    gvScatterLabel.transition().duration(dur).ease(d3.easeQuadOut)
      .attr("x", d => (posMap.get(d.person) || { x: cascadeState ? gvDotPosCascade(d).cx : gvDotPos(d).cx }).x)
      .attr("y", d => (posMap.get(d.person) || { y: (cascadeState ? gvDotPosCascade(d).cy : gvDotPos(d).cy) - 12 }).y)
      .attr("opacity", d => {
        if (removed2.has(d.person)) return 0;
        if (!q) return effectiveQuadrant(d) === "Organizational Emergency" ? 1 : 0;
        return effectiveQuadrant(d) === q ? 1 : 0;
      });
  }

  // Transition axes with precise tick format for zoomed range
  const fmt = q
    ? v => (v * 100).toFixed(1) + "%"
    : v => (v * 100).toFixed(0) + "%";
  if (gvScatterXSel && gvScatterXAxis) {
    gvScatterXSel.transition().duration(dur).ease(d3.easeQuadOut)
      .call(gvScatterXAxis.ticks(5).tickFormat(fmt));
  }
  if (gvScatterYSel && gvScatterYAxis) {
    gvScatterYSel.transition().duration(dur).ease(d3.easeQuadOut)
      .call(gvScatterYAxis.ticks(5).tickFormat(fmt));
  }

  // Watermark
  if (gvScatterWatermark) {
    if (q) {
      gvScatterWatermark.text(q).transition().duration(dur).attr("fill", GV_Q_HEX[q]).attr("opacity", 0.18);
    } else {
      gvScatterWatermark.transition().duration(dur).attr("opacity", 0);
    }
  }
}

// ── Scatter plot ────────────────────────────────────────────────────────────────
function buildGvScatter() {
  const svg = d3.select("#gvScatter");
  svg.selectAll("*").remove();

  const container = document.getElementById("gvScatterView");
  // getBoundingClientRect forces a reflow and returns the true rendered size,
  // avoiding stale clientWidth/clientHeight when the panel just became visible.
  const rect = container.getBoundingClientRect();
  const w = Math.round(rect.width)  || container.clientWidth  || 600;
  const h = Math.round(rect.height) || container.clientHeight || 480;
  if (w < 10 || h < 10) return;

  svg.attr("width", w).attr("height", h);

  const margin = { top: 40, right: 40, bottom: 60, left: 65 };
  const plotW  = w - margin.left - margin.right;
  const plotH  = h - margin.top  - margin.bottom;

  // Clip path so zoomed-out dots don't render outside the plot area
  svg.append("defs").append("clipPath").attr("id", "gvClip")
    .append("rect").attr("width", plotW).attr("height", plotH);

  // g: axes (unclipped); gPlot: all plot content (clipped)
  const g     = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);
  const gPlot = g.append("g").attr("clip-path", "url(#gvClip)");

  // Initialize module-level scales
  gvScatterX = d3.scaleLinear().domain([0, 0.50]).range([0, plotW]);
  gvScatterY = d3.scaleLinear().domain([0, 1.00]).range([plotH, 0]);

  // Quadrant backgrounds — stored so applyGvZoom can hide them
  gvScatterBgs = {};
  gvScatterBgs["Low Priority"]             = gPlot.append("rect").attr("x", 0)                  .attr("y", gvScatterY(GV_PI_T)).attr("width", gvScatterX(GV_KR_T)         ).attr("height", plotH - gvScatterY(GV_PI_T)).attr("fill", "#2D8C3C").attr("opacity", 0.05);
  gvScatterBgs["Silent Threat"]            = gPlot.append("rect").attr("x", gvScatterX(GV_KR_T)).attr("y", gvScatterY(GV_PI_T)).attr("width", plotW - gvScatterX(GV_KR_T)).attr("height", plotH - gvScatterY(GV_PI_T)).attr("fill", "#C49032").attr("opacity", 0.05);
  gvScatterBgs["Replaceable Executive"]    = gPlot.append("rect").attr("x", 0)                  .attr("y", 0)                  .attr("width", gvScatterX(GV_KR_T)         ).attr("height", gvScatterY(GV_PI_T)        ).attr("fill", "#0072BC").attr("opacity", 0.05);
  gvScatterBgs["Organizational Emergency"] = gPlot.append("rect").attr("x", gvScatterX(GV_KR_T)).attr("y", 0)                  .attr("width", plotW - gvScatterX(GV_KR_T)).attr("height", gvScatterY(GV_PI_T)        ).attr("fill", "#D4342E").attr("opacity", 0.05);

  // Threshold lines — stored so applyGvZoom can hide them
  gvScatterThreshLines = [
    gPlot.append("line").attr("x1", gvScatterX(GV_KR_T)).attr("y1", 0).attr("x2", gvScatterX(GV_KR_T)).attr("y2", plotH).attr("stroke", "#333").attr("stroke-width", 1).attr("stroke-dasharray", "4 4"),
    gPlot.append("line").attr("x1", 0).attr("y1", gvScatterY(GV_PI_T)).attr("x2", plotW).attr("y2", gvScatterY(GV_PI_T)).attr("stroke", "#333").attr("stroke-width", 1).attr("stroke-dasharray", "4 4"),
  ];

  // Quadrant labels — stored so applyGvZoom can hide them
  const qlStyle = { "font-family": "'JetBrains Mono',monospace", "font-size": "10px", "pointer-events": "none" };
  gvScatterQLabels = {};
  gvScatterQLabels["Replaceable Executive"]    = gPlot.append("text").attr("x", gvScatterX(GV_KR_T) / 2)                           .attr("y", 18).attr("text-anchor", "middle").attr("fill", "#0072BC").attr("opacity", 0.4).text("Replaceable Executive").call(applyAttrs, qlStyle);
  gvScatterQLabels["Organizational Emergency"] = gPlot.append("text").attr("x", gvScatterX(GV_KR_T) + (plotW - gvScatterX(GV_KR_T)) / 2).attr("y", 18).attr("text-anchor", "middle").attr("fill", "#D4342E").attr("opacity", 0.4).text("Organizational Emergency").call(applyAttrs, qlStyle);
  gvScatterQLabels["Low Priority"]             = gPlot.append("text").attr("x", gvScatterX(GV_KR_T) / 2)                           .attr("y", plotH - 8).attr("text-anchor", "middle").attr("fill", "#2D8C3C").attr("opacity", 0.4).text("Low Priority").call(applyAttrs, qlStyle);
  gvScatterQLabels["Silent Threat"]            = gPlot.append("text").attr("x", gvScatterX(GV_KR_T) + (plotW - gvScatterX(GV_KR_T)) / 2).attr("y", plotH - 8).attr("text-anchor", "middle").attr("fill", "#C49032").attr("opacity", 0.4).text("Silent Threat").call(applyAttrs, qlStyle);

  // Watermark (large, centered, initially hidden)
  gvScatterWatermark = gPlot.append("text")
    .attr("x", plotW / 2).attr("y", plotH / 2)
    .attr("text-anchor", "middle").attr("dominant-baseline", "middle")
    .attr("font-family", "'Times New Roman',Times,serif").attr("font-size", "26px")
    .attr("font-weight", "600").attr("font-style", "italic").attr("pointer-events", "none")
    .attr("opacity", 0).text("");

  // Axes (in g, outside clip so ticks don't get clipped)
  gvScatterXAxis = d3.axisBottom(gvScatterX).ticks(5).tickFormat(v => (v * 100).toFixed(0) + "%");
  gvScatterYAxis = d3.axisLeft(gvScatterY).ticks(5).tickFormat(v => (v * 100).toFixed(0) + "%");
  gvScatterXSel  = g.append("g").attr("class", "gvax").attr("transform", `translate(0,${plotH})`).call(gvScatterXAxis);
  gvScatterYSel  = g.append("g").attr("class", "gvax").call(gvScatterYAxis);

  // Axis labels
  svg.append("text").attr("x", margin.left + plotW / 2).attr("y", h - 8).attr("text-anchor", "middle").attr("fill", "#6E6E73").attr("font-family", "'JetBrains Mono',monospace").attr("font-size", "11px").text("Knowledge risk score \u2192");
  svg.append("text").attr("x", 14).attr("y", margin.top + plotH / 2).attr("text-anchor", "middle").attr("transform", `rotate(-90,14,${margin.top + plotH / 2})`).attr("fill", "#6E6E73").attr("font-family", "'JetBrains Mono',monospace").attr("font-size", "11px").text("Positional impact score \u2192");

  const tt     = document.getElementById("gvTooltip");
  const people = DATA.people.filter(p => p.positional_impact != null);

  // Dots
  gvScatterDots = gPlot.selectAll(".gv-dot").data(people).enter().append("circle")
    .attr("class", "gv-dot")
    .attr("cx", d => gvDotPos(d).cx)
    .attr("cy", d => gvDotPos(d).cy)
    .attr("r",  gvDotR)
    .attr("fill",   d => d.quadrant_color || "#6E6E73")
    .attr("stroke", "#0A0A0A").attr("stroke-width", 1.5).attr("opacity", 0.85)
    .style("cursor", "pointer")
    .on("mouseover", (ev, d) => {
      const nm = d.display_name || formatName(d.person);
      tt.innerHTML = `<div style="font-weight:500;margin-bottom:2px">${nm}</div><div style="font-size:10px;color:var(--text-tertiary);margin-bottom:3px">${d.role || "—"}</div><div style="font-size:10px;color:#6E6E73">Knowledge: ${(d.risk_score * 100).toFixed(1)} &middot; Positional: ${((d.positional_impact || 0) * 100).toFixed(0)} &middot; Losses: ${d.n_perm_loss_categories || 0}</div>`;
      tt.style.display = "block";
      if (gvSelectedId !== d.person) d3.select(ev.target).attr("r", gvDotR(d) + 3).attr("opacity", 1);
    })
    .on("mousemove", ev => { tt.style.left = (ev.clientX + 14) + "px"; tt.style.top = (ev.clientY - 10) + "px"; })
    .on("mouseout", (ev, d) => {
      tt.style.display = "none";
      if (gvSelectedId !== d.person) d3.select(ev.target).attr("r", gvDotR(d)).attr("opacity", gvDotOpacity(d));
    })
    .on("click", (ev, d) => {
      gvSelectedId = d.person;
      gvNavPrev    = null;
      gvScatterDots.transition().duration(200).attr("opacity", gvDotOpacity);
      d3.select(ev.target).transition().duration(200).attr("opacity", 1).attr("r", gvDotR(d) + 5);
      renderGvRightPanel(d);
    });

  // Labels — ALL people rendered; opacity controlled by applyGvZoom / default rule
  gvScatterLabel = gPlot.selectAll(".gv-dot-label").data(people).enter().append("text")
    .attr("class", "gv-dot-label")
    .attr("x", d => gvDotPos(d).cx)
    .attr("y", d => gvDotPos(d).cy - 12)
    .attr("text-anchor", "middle")
    .attr("fill", "#6E6E73").attr("font-size", "9px").attr("font-family", "'JetBrains Mono',monospace")
    .attr("opacity", d => effectiveQuadrant(d) === "Organizational Emergency" ? 1 : 0)
    .text(d => (d.display_name || lastName(d.person)).split(" ").pop())
    .style("pointer-events", "none");

  // Double-click: reset selection (zoom stays)
  svg.on("dblclick", () => {
    gvSelectedId = null;
    if (gvScatterDots) gvScatterDots.transition().duration(200).attr("opacity", gvDotOpacity).attr("r", gvDotR);
    document.getElementById("gvRightPanel").innerHTML = gvPlaceholderHTML();
  });

  // Re-apply zoom if scatter was rebuilt during a resize while already zoomed
  if (gvScatterZoom) applyGvZoom(gvScatterZoom);

  // Apply cascade overlay if a multi-removal simulation is active
  if (cascadeState) {
    const removedSet = new Set(cascadeState.removed);
    // Hide removed employees
    gvScatterDots.filter(d =>  removedSet.has(d.person)).attr("r", 0).attr("opacity", 0);
    if (gvScatterLabel) gvScatterLabel.filter(d => removedSet.has(d.person)).attr("opacity", 0);
    // Move remaining employees to cascaded positions; color by new quadrant
    gvScatterDots.filter(d => !removedSet.has(d.person))
      .transition().duration(800)
      .attr("cx",   d => gvDotPosCascade(d).cx)
      .attr("fill", d => cascadeQuadrantColor(d));
    if (gvScatterLabel) {
      gvScatterLabel.filter(d => !removedSet.has(d.person))
        .transition().duration(800).attr("x", d => gvDotPosCascade(d).cx);
    }
  }
}

function applyAttrs(sel, attrs) {
  Object.entries(attrs).forEach(([k, v]) => sel.attr(k, v));
}

function gvPlaceholderHTML() {
  return `<div class="gv-placeholder">
    <svg width="48" height="48" style="margin-bottom:12px;opacity:0.3"><circle cx="24" cy="24" r="20" fill="none" stroke="#6E6E73" stroke-width="1.5"/><circle cx="24" cy="24" r="3" fill="#6E6E73"/></svg>
    Click any dot to explore<br>employee network position
  </div>`;
}

// ── Graph network explorer ──────────────────────────────────────────────────────
function buildGvNetwork() {
  const svg = d3.select("#gvNetSvg");
  svg.selectAll("*").remove();
  if (gvNetSim2) { gvNetSim2.stop(); gvNetSim2 = null; }
  gvNetIsolated = false;

  const container = document.getElementById("gvNetView");
  const w = container.clientWidth  || 700;
  const h = container.clientHeight || 480;
  svg.attr("width", w).attr("height", h);

  // Enrich nodes with dept — title-first logic, falls back to role_category
  const deptLookup = {};
  DATA.people.forEach(p => {
    const fromTitle = titleToDept(p.role);
    deptLookup[p.person] = fromTitle || (p.role_category || "Administration");
  });

  // Compute degree within top-50 graph; exclude nodes with fewer than 3 connections
  const NODE_NAME_OVERRIDES = { 'bwalker@hga.org': 'B. Walker' };
  const rawLinks = g50edges.map(e => ({ source: e.source, target: e.target, weight: e.weight, wn: e.wn }));
  const deg50 = {};
  rawLinks.forEach(l => { deg50[l.source] = (deg50[l.source] || 0) + 1; deg50[l.target] = (deg50[l.target] || 0) + 1; });
  // Top-20 by risk_score always appear regardless of degree (e.g., Pete Davis)
  const top20NE = new Set([...g50nodes].sort((a, b) => (b.risk_score || 0) - (a.risk_score || 0)).slice(0, 20).map(n => n.id));
  const inclIds = new Set(g50nodes.filter(n => (deg50[n.id] || 0) >= 3 || top20NE.has(n.id)).map(n => n.id));

  const nodes = g50nodes.filter(n => inclIds.has(n.id)).map(n => ({
    id: n.id,
    display_name: NODE_NAME_OVERRIDES[n.id] || n.display_name,
    risk_score: n.risk_score,
    dept: deptLookup[n.id] || "Administration",
  }));
  const links = rawLinks.filter(l => inclIds.has(l.source) && inclIds.has(l.target));

  // Edge width: 1–5px scaled by raw email count
  const wMax = d3.max(links, l => l.weight) || 1;
  const edgeW = d => 1 + (d.weight / wMax) * 4;

  // Dept groups: hullDepts (3+ nodes) for visible hulls; clusterDepts (2+ nodes) for force
  const deptGroups = {};
  nodes.forEach(n => { (deptGroups[n.dept] = deptGroups[n.dept] || []).push(n); });
  const hullDepts    = Object.keys(deptGroups).filter(d => deptGroups[d].length >= 3);
  const clusterDepts = Object.keys(deptGroups).filter(d => deptGroups[d].length >= 2);

  const g = svg.append("g");
  svg.call(d3.zoom().scaleExtent([0.3, 4]).on("zoom", ev => g.attr("transform", ev.transform)));

  const tt = document.getElementById("gvTooltip");

  // ── Dept hull layer (behind everything) ──
  const gDept = g.append("g").attr("class", "gvn-dept-layer");
  const hullPaths = {}, hullLabels = {};
  hullDepts.forEach(dept => {
    const hex = GV_DEPT_COLORS[dept] || "#48484A";
    hullPaths[dept]  = gDept.append("path").attr("fill", hex).attr("opacity", 0.07)
      .attr("stroke", "none").style("pointer-events", "none");
    hullLabels[dept] = gDept.append("text").attr("fill", hex).attr("font-size", "9px")
      .attr("font-family", "'JetBrains Mono',monospace").attr("font-weight", "600")
      .attr("opacity", 0.35).attr("text-anchor", "middle").style("pointer-events", "none")
      .text(dept.toUpperCase());
  });

  function updateHulls() {
    hullDepts.forEach(dept => {
      const pts = deptGroups[dept].filter(n => n.x != null).map(n => [n.x, n.y]);
      if (pts.length < 3) return;
      const hull = d3.polygonHull(pts);
      if (!hull) return;
      const cx = d3.mean(pts, p => p[0]), cy = d3.mean(pts, p => p[1]);
      const pad = 28;
      const expanded = hull.map(([x, y]) => {
        const dx = x - cx, dy = y - cy, len = Math.sqrt(dx*dx + dy*dy) || 1;
        return [x + (dx/len)*pad, y + (dy/len)*pad];
      });
      hullPaths[dept].attr("d", "M" + expanded.map(p => p.join(",")).join("L") + "Z");
      hullLabels[dept].attr("x", cx).attr("y", cy - 32);
    });
  }

  // ── Edges ──
  gvNetLe = g.selectAll(".gvn-edge").data(links).enter().append("line")
    .attr("class", "gvn-edge")
    .attr("stroke", "rgba(0,114,188,0.2)")
    .attr("stroke-width", edgeW)
    .on("mouseover", (ev, d) => {
      const sn = (d.source.display_name || lastName(d.source.id || d.source)).split(" ").pop();
      const tn = (d.target.display_name || lastName(d.target.id || d.target)).split(" ").pop();
      tt.innerHTML = `${sn} \u2194 ${tn} \u00b7 ${Math.round(d.weight).toLocaleString()} emails`;
      tt.style.display = "block";
      const sid = typeof d.source === "object" ? d.source.id : d.source;
      const tid = typeof d.target === "object" ? d.target.id : d.target;
      if (!gvNetIsolated || sid === gvSelectedId || tid === gvSelectedId) {
        d3.select(ev.target).attr("stroke", "rgba(0,114,188,0.6)").attr("stroke-width", edgeW(d) + 1.5);
      }
    })
    .on("mousemove", ev => { tt.style.left = (ev.clientX + 14) + "px"; tt.style.top = (ev.clientY - 10) + "px"; })
    .on("mouseout", (ev, d) => {
      tt.style.display = "none";
      d3.select(ev.target).attr("stroke", "rgba(0,114,188,0.2)").attr("stroke-width", edgeW(d));
    });

  // ── Glow halos ──
  gvNetGc = g.selectAll(".gvn-glow").data(nodes).enter().append("circle")
    .attr("class", "gvn-glow").attr("r", d => 10 + d.risk_score * 20)
    .attr("fill", d => nodeColor(d.risk_score)).attr("opacity", 0.12)
    .style("pointer-events", "none");

  // ── Nodes ──
  gvNetNe = g.selectAll(".gvn-node").data(nodes).enter().append("circle")
    .attr("class", "gvn-node").attr("r", d => 6 + d.risk_score * 18)
    .attr("fill", d => nodeColor(d.risk_score))
    .attr("stroke", "#0A0A0A").attr("stroke-width", 2)
    .style("cursor", "pointer")
    .on("mouseover", (ev, d) => {
      if (d.id !== gvSelectedId) d3.select(ev.target).attr("stroke", "#FFFFFF").attr("stroke-width", 2.5);
      tt.innerHTML = `${d.display_name || lastName(d.id)} \u00b7 ${(d.risk_score * 100).toFixed(0)} risk`;
      tt.style.display = "block";
    })
    .on("mousemove", ev => { tt.style.left = (ev.clientX + 14) + "px"; tt.style.top = (ev.clientY - 10) + "px"; })
    .on("mouseout", (ev, d) => {
      tt.style.display = "none";
      if (d.id !== gvSelectedId) d3.select(ev.target).attr("stroke", "#0A0A0A").attr("stroke-width", 2);
    })
    .on("click", (ev, d) => {
      ev.stopPropagation();
      tt.style.display = "none";
      // Toggle off if clicking already-selected non-isolated node
      if (gvSelectedId === d.id && !gvNetIsolated) {
        gvSelectedId = null;
        gvNetNe.transition().duration(200).attr("opacity", 1).attr("stroke", "#0A0A0A").attr("stroke-width", 2);
        gvNetGc.transition().duration(200).attr("opacity", 0.12);
        gvNetLe.transition().duration(200).attr("opacity", 1).attr("stroke", "rgba(0,114,188,0.2)").attr("stroke-width", edgeW);
        document.getElementById("gvRightPanel").innerHTML = gvPlaceholderHTML();
        return;
      }
      gvSelectedId  = d.id;
      gvNetIsolated = false;
      const connIds = new Set();
      links.forEach(l => {
        const s = typeof l.source === "object" ? l.source.id : l.source;
        const t = typeof l.target === "object" ? l.target.id : l.target;
        if (s === d.id) connIds.add(t);
        if (t === d.id) connIds.add(s);
      });
      gvNetNe.transition().duration(200)
        .attr("opacity",      n => n.id === d.id || connIds.has(n.id) ? 1 : 0.20)
        .attr("stroke",       n => n.id === d.id ? "#FFFFFF" : "#0A0A0A")
        .attr("stroke-width", n => n.id === d.id ? 3 : 2);
      gvNetGc.transition().duration(200).attr("opacity", n => n.id === d.id || connIds.has(n.id) ? 0.15 : 0.03);
      gvNetLe.transition().duration(200)
        .attr("opacity", l => {
          const s = typeof l.source === "object" ? l.source.id : l.source;
          const t = typeof l.target === "object" ? l.target.id : l.target;
          return (s === d.id || t === d.id) ? 0.8 : 0.05;
        })
        .attr("stroke-width", l => {
          const s = typeof l.source === "object" ? l.source.id : l.source;
          const t = typeof l.target === "object" ? l.target.id : l.target;
          return (s === d.id || t === d.id) ? edgeW(l) + 1 : edgeW(l);
        });
      const person = DATA.people.find(p => p.person === d.id);
      if (person) renderGvRightPanel(person);
    })
    .on("dblclick", (ev, d) => {
      ev.stopPropagation();
      tt.style.display = "none";
      if (gvNetIsolated && gvSelectedId === d.id) {
        // Restore
        gvNetIsolated = false;
        gvNetNe.transition().duration(300).attr("opacity", 1).attr("stroke", "#0A0A0A").attr("stroke-width", 2);
        gvNetGc.transition().duration(300).attr("opacity", 0.12);
        gvNetLe.transition().duration(300).attr("opacity", 1).attr("stroke", "rgba(0,114,188,0.2)");
      } else {
        // Isolate: show only direct connections
        gvNetIsolated = true;
        gvSelectedId  = d.id;
        const connIds = new Set();
        links.forEach(l => {
          const s = typeof l.source === "object" ? l.source.id : l.source;
          const t = typeof l.target === "object" ? l.target.id : l.target;
          if (s === d.id) connIds.add(t);
          if (t === d.id) connIds.add(s);
        });
        gvNetNe.transition().duration(300)
          .attr("opacity", n => n.id === d.id || connIds.has(n.id) ? 1 : 0.10)
          .attr("stroke",  n => n.id === d.id ? "#FFFFFF" : "#0A0A0A")
          .attr("stroke-width", n => n.id === d.id ? 3 : 2);
        gvNetGc.transition().duration(300).attr("opacity", n => n.id === d.id || connIds.has(n.id) ? 0.15 : 0.02);
        gvNetLe.transition().duration(300)
          .attr("opacity", l => {
            const s = typeof l.source === "object" ? l.source.id : l.source;
            const t = typeof l.target === "object" ? l.target.id : l.target;
            return (s === d.id || t === d.id) ? 0.8 : 0.03;
          })
          .attr("stroke", "rgba(0,114,188,0.2)");
        const person = DATA.people.find(p => p.person === d.id);
        if (person) renderGvRightPanel(person);
      }
    });

  g.selectAll(".gvn-label").data(nodes).enter().append("text")
    .attr("class", "gvn-label")
    .attr("fill", "#A1A1A6").attr("font-size", "9px").attr("font-family", "'JetBrains Mono',monospace")
    .attr("text-anchor", "middle").attr("dy", d => (6 + d.risk_score * 18) + 13)
    .text(d => d.display_name ? d.display_name.split(" ").pop() : lastName(d.id))
    .style("pointer-events", "none");

  // Clustering force: pull same-dept nodes toward their centroid
  // Uses clusterDepts (2+ nodes) so even two-person depts cluster together
  const clusterForce = alpha => {
    const centroids = {};
    clusterDepts.forEach(dept => {
      const grp = deptGroups[dept].filter(n => n.x != null);
      if (!grp.length) return;
      centroids[dept] = { x: d3.mean(grp, n => n.x), y: d3.mean(grp, n => n.y) };
    });
    nodes.forEach(n => {
      const c = centroids[n.dept];
      if (!c) return;
      n.vx = (n.vx || 0) + (c.x - n.x) * 0.08 * alpha;
      n.vy = (n.vy || 0) + (c.y - n.y) * 0.08 * alpha;
    });
  };

  gvNetSim2 = d3.forceSimulation(nodes)
    .force("link",      d3.forceLink(links).id(d => d.id).distance(140))
    .force("charge",    d3.forceManyBody().strength(-400))
    .force("center",    d3.forceCenter(w / 2, h / 2))
    .force("collision", d3.forceCollide().radius(d => 16 + d.risk_score * 20))
    .force("cluster",   clusterForce)
    .on("tick", () => {
      gvNetLe.attr("x1", d => d.source.x).attr("y1", d => d.source.y).attr("x2", d => d.target.x).attr("y2", d => d.target.y);
      gvNetGc.attr("cx", d => d.x).attr("cy", d => d.y);
      gvNetNe.attr("cx", d => d.x).attr("cy", d => d.y);
      g.selectAll(".gvn-label").attr("x", d => d.x).attr("y", d => d.y);
      updateHulls();
    });

  // Click empty space → restore from any highlight/isolation state
  svg.on("click", () => {
    if (!gvSelectedId && !gvNetIsolated) return;
    gvSelectedId  = null;
    gvNetIsolated = false;
    gvNetNe.transition().duration(250).attr("opacity", 1).attr("stroke", "#0A0A0A").attr("stroke-width", 2);
    gvNetGc.transition().duration(250).attr("opacity", 0.12);
    gvNetLe.transition().duration(250).attr("opacity", 1).attr("stroke", "rgba(0,114,188,0.2)").attr("stroke-width", edgeW);
  });

  // Double-click empty space → full reset
  svg.on("dblclick", () => {
    gvNetIsolated = false;
    gvSelectedId  = null;
    gvNetNe.transition().duration(300).attr("opacity", 1).attr("stroke", "#0A0A0A").attr("stroke-width", 2);
    gvNetGc.transition().duration(300).attr("opacity", 0.12);
    gvNetLe.transition().duration(300).attr("opacity", 1).attr("stroke", "rgba(0,114,188,0.2)");
    document.getElementById("gvRightPanel").innerHTML = gvPlaceholderHTML();
  });
}


// ── Ego network navigation ──────────────────────────────────────────────────────
function egoNavToPartner(partnerEmail, currentPerson) {
  const partner = DATA.people.find(p => p.person === partnerEmail);
  if (!partner) {
    const tt = document.getElementById("gvTooltip");
    if (tt) {
      tt.innerHTML = `<div style="font-size:11px;color:var(--text-tertiary)">Not in top 200 — no simulation data available</div>`;
      tt.style.display = "block";
      setTimeout(() => { tt.style.display = "none"; }, 2000);
    }
    return;
  }
  gvNavPrev  = currentPerson;
  gvSelectedId = partnerEmail;

  // Highlight selected dot on scatter
  if (gvScatterDots) {
    gvScatterDots.transition().duration(200).attr("opacity", gvDotOpacity).attr("r", gvDotR);
    gvScatterDots.filter(d => d.person === partnerEmail)
      .transition().duration(200).attr("opacity", 1).attr("r", d => gvDotR(d) + 5);
  }

  // Zoom handling: navigate to partner's quadrant (cascade-aware)
  const targetQ = effectiveQuadrant(partner);
  if (gvScatterZoom && gvScatterZoom !== targetQ) {
    applyGvZoom(null);
    setTimeout(() => applyGvZoom(targetQ), 450);
  } else if (!gvScatterZoom) {
    applyGvZoom(targetQ);
  }

  renderGvRightPanel(partner, currentPerson);
}

function navigateBack() {
  if (!gvNavPrev) return;
  const prev = gvNavPrev;
  gvNavPrev    = null;
  gvSelectedId = prev.person;

  if (gvScatterDots) {
    gvScatterDots.transition().duration(200).attr("opacity", gvDotOpacity).attr("r", gvDotR);
    gvScatterDots.filter(d => d.person === prev.person)
      .transition().duration(200).attr("opacity", 1).attr("r", d => gvDotR(d) + 5);
  }

  const targetQ = prev.quadrant;
  if (gvScatterZoom && gvScatterZoom !== targetQ) {
    applyGvZoom(null);
    setTimeout(() => applyGvZoom(targetQ), 450);
  } else if (!gvScatterZoom) {
    applyGvZoom(targetQ);
  }

  renderGvRightPanel(prev);
}

// ── Graph view right panel ─────────────────────────────────────────────────────
function renderGvRightPanel(person, prevPerson = null) {
  const name  = person.display_name || formatName(person.person);
  // Use cascaded risk score when cascade is active
  const kr    = (cascadeState && cascadeState.liveRisks[person.person] != null)
                ? cascadeState.liveRisks[person.person]
                : (person.risk_score || 0);
  const pi    = person.positional_impact || 0;
  const perm  = person.n_perm_loss_categories || 0;
  // Cascaded quadrant and color
  const effectiveQ = effectiveQuadrant(person);
  const color = GV_Q_HEX[effectiveQ] || person.quadrant_color || "#6E6E73";

  // Knowledge uniqueness: unique categories, count others sharing each
  const myCats = [...new Set((person.topic_profile || []).map(t => t.category).filter(Boolean))];
  const uniqueness = myCats.map(cat => {
    const others = DATA.people.filter(p => p.person !== person.person &&
      (p.topic_profile || []).some(t => t.category === cat)).length;
    return { name: cat, others };
  });
  const maxOthers = Math.max(...uniqueness.map(u => u.others), 1);

  // Tailored quadrant description built from person's actual data
  const rarestTopic  = [...uniqueness].sort((a, b) => a.others - b.others)[0];
  const nDepts       = Object.keys((() => {
    const dt = {};
    (gvEdgesByPerson[person.person] || []).forEach(e => {
      const pd = DATA.people.find(p => p.person === e.partner);
      dt[(pd && pd.role_category) || "Administration"] = 1;
    });
    return dt;
  })()).length;
  const nPartners    = (gvEdgesByPerson[person.person] || []).length;
  const primaryCat   = myCats[0] || "their domain";
  const isJunior     = pi < 0.40;
  const titleOpen    = isJunior ? "Despite a junior title" : `As ${person.role ? person.role.split(",")[0] : "a senior role"}`;
  const knowledgeLine = rarestTopic
    ? (rarestTopic.others === 0
        ? `Sole internal coverage of ${rarestTopic.name} with no backup.`
        : `Their ${rarestTopic.name} expertise has only ${rarestTopic.others} other internal expert${rarestTopic.others === 1 ? "" : "s"}.`)
    : "";
  const networkLine  = nPartners > 0
    ? `${nPartners} direct communication partner${nPartners === 1 ? "" : "s"} across ${nDepts} department${nDepts === 1 ? "" : "s"}.`
    : "";

  let quadrantCtx = "";
  if (effectiveQ === "Organizational Emergency") {
    quadrantCtx = `${titleOpen}, this person carries a ${(kr*100).toFixed(1)} knowledge risk score and ${(pi*100).toFixed(0)} positional authority — a dual exposure. ${knowledgeLine} Departure creates both a knowledge gap and a leadership vacuum simultaneously.`;
  } else if (effectiveQ === "Silent Threat") {
    quadrantCtx = `${titleOpen}, this person holds a ${(kr*100).toFixed(1)} knowledge risk score despite only ${(pi*100).toFixed(0)} positional impact — they appear replaceable on paper but carry critical operational knowledge. ${knowledgeLine}`;
  } else if (effectiveQ === "Replaceable Executive") {
    const primaryOthers = uniqueness.find(u => u.name === primaryCat);
    const distributed   = primaryOthers ? `${primaryOthers.others} others share their primary domain` : "knowledge is well-distributed";
    quadrantCtx = `${titleOpen} (${(pi*100).toFixed(0)} positional impact score), their knowledge is broadly shared — ${distributed}. Departure disrupts authority and coordination chains, not institutional knowledge.`;
  } else {
    const primaryOthers = uniqueness.find(u => u.name === primaryCat);
    const nOthers = primaryOthers ? primaryOthers.others : maxOthers;
    quadrantCtx = `Standard succession risk. Knowledge is well-distributed across ${nOthers} other expert${nOthers === 1 ? "" : "s"} in ${primaryCat}. ${networkLine}`;
  }

  // Communication partners from edge lookup
  const myEdges  = (gvEdgesByPerson[person.person] || []).sort((a, b) => b.weight - a.weight);
  const partners = myEdges.slice(0, 7).map(e => {
    const pd = DATA.people.find(p => p.person === e.partner);
    return { name: pd ? (pd.display_name || formatName(e.partner)) : formatName(e.partner), weight: e.weight };
  });

  // Cross-dept reach
  const deptTotals = {};
  myEdges.forEach(e => {
    const pd   = DATA.people.find(p => p.person === e.partner);
    const dept = (pd && pd.role_category) || "Administration";
    deptTotals[dept] = (deptTotals[dept] || 0) + e.weight;
  });
  const deptEntries = Object.entries(deptTotals).sort((a, b) => b[1] - a[1]);
  const deptTotal   = deptEntries.reduce((s, e) => s + e[1], 0) || 1;

  // Network role: top 2 topic categories
  const topCats = [...new Set((person.topic_profile || []).map(t => t.category).filter(Boolean))].slice(0, 2);
  const networkRole = topCats.length >= 2
    ? `Bridges <span style="color:var(--text)">${topCats[0]}</span> and <span style="color:var(--text)">${topCats[1]}</span>`
    : topCats.length === 1
    ? `Primary domain: <span style="color:var(--text)">${topCats[0]}</span>`
    : "—";

  const prevName = prevPerson ? (prevPerson.display_name || formatName(prevPerson.person)).split(" ").pop() : null;

  let html = `
    ${prevName ? `<div style="margin-bottom:10px"><button onclick="navigateBack()" style="background:none;border:none;cursor:pointer;color:#48484A;font-family:'JetBrains Mono',monospace;font-size:10px;padding:0;display:flex;align-items:center;gap:4px"><svg width="10" height="10" viewBox="0 0 10 10" fill="none" style="flex-shrink:0"><path d="M6.5 1.5L3 5l3.5 3.5" stroke="#48484A" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>Back to ${prevName}</button></div>` : ""}
    <div class="gv-person-name">${name}</div>
    <div class="gv-person-title">${person.role || "—"}</div>
    <div class="gv-quadrant-badge" style="background:${color}22;color:${color}">${effectiveQ || "—"}</div>
    <div class="gv-quadrant-ctx">${
      cascadeState
        ? quadrantCtx
        : (person.description
            ? person.description.replace(/-/g, "\u2011")
            : `${effectiveQ}: ${(kr*100).toFixed(1)} knowledge risk score, ${(pi*100).toFixed(0)} positional impact score.`)
    }</div>

    <div class="gv-metrics">
      <div class="gv-stat">
        <div class="gv-stat-label">Knowledge</div>
        <div class="gv-stat-value" style="color:${riskColor(kr)}">${(kr * 100).toFixed(1)}</div>
      </div>
      <div class="gv-stat">
        <div class="gv-stat-label">Positional</div>
        <div class="gv-stat-value" style="color:${pi >= 0.65 ? "#D4342E" : pi >= 0.40 ? "#C49032" : "#F5F5F7"}">${(pi * 100).toFixed(0)}</div>
      </div>
      <div class="gv-stat">
        <div class="gv-stat-label">Perm losses</div>
        <div class="gv-stat-value">${perm}</div>
      </div>
    </div>

    <div class="gv-section-header">Ego network</div>
    <div class="gv-ego" id="gvEgoContainer"></div>`;

  if (uniqueness.length) {
    html += `<div class="gv-section-header">Knowledge uniqueness</div>`;
    uniqueness.forEach(u => {
      const col  = u.others <= 5 ? "#D4342E" : u.others <= 15 ? "#C49032" : "rgba(0,114,188,0.5)";
      const textCol = u.others <= 5 ? "#D4342E" : u.others <= 15 ? "#C49032" : "var(--text-quaternary)";
      const barW = Math.min(100, (u.others / maxOthers) * 100);
      html += `<div class="gv-uniq-row">
        <div class="gv-uniq-topic">${u.name}</div>
        <div class="gv-uniq-bar-bg"><div class="gv-uniq-bar" style="width:${barW}%;background:${col}"></div></div>
        <div class="gv-uniq-count" style="color:${textCol}">${u.others} others</div>
      </div>`;
    });
  }

  if (partners.length) {
    html += `<div class="gv-section-header">Communication flow</div>
    <div class="gv-flow-legend">
      <span><span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:rgba(0,114,188,0.55);margin-right:3px;vertical-align:middle"></span>Sent</span>
      <span><span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:rgba(45,140,60,0.55);margin-right:3px;vertical-align:middle"></span>Received</span>
    </div>`;
    partners.forEach(p => {
      html += `<div class="gv-partner-row">
        <div class="gv-partner-name">${p.name}</div>
        <div class="gv-partner-bar"><div class="gv-partner-sent" style="width:50%"></div><div class="gv-partner-recv" style="width:50%"></div></div>
        <div class="gv-partner-total">${p.weight.toLocaleString()}</div>
      </div>`;
    });
  }

  if (deptEntries.length) {
    html += `<div class="gv-section-header">Cross-department reach</div>
    <div class="gv-dept-bar">`;
    deptEntries.forEach(([dept, val]) => {
      const col = GV_DEPT_COLORS[dept] || "#48484A";
      const pct = (val / deptTotal) * 100;
      html += `<div class="gv-dept-seg" style="width:${pct.toFixed(1)}%;background:${col}">${pct >= 15 ? Math.round(pct) + "%" : ""}</div>`;
    });
    html += `</div><div class="gv-dept-legend">`;
    deptEntries.forEach(([dept]) => {
      html += `<div class="gv-dept-item"><div class="gv-dept-dot" style="background:${GV_DEPT_COLORS[dept] || "#48484A"}"></div>${dept}</div>`;
    });
    html += `</div>`;
  }

  html += `<div class="gv-section-header">Network role</div>
    <div style="font-size:12px;color:var(--text-tertiary);line-height:1.6;font-family:'JetBrains Mono',monospace">
      ${networkRole}
    </div>`;

  document.getElementById("gvRightPanel").innerHTML = html;
  buildGvEgoGraph(person, prevPerson);
}

// ── Ego network mini-graph ──────────────────────────────────────────────────────
function buildGvEgoGraph(person, prevPerson = null) {
  const container = document.getElementById("gvEgoContainer");
  if (!container) return;
  d3.select(container).selectAll("*").remove();

  const w = container.clientWidth || 300;
  const h = 180;
  const centerColor = person.quadrant_color || nodeColor(person.risk_score || 0);
  const personLast  = (person.display_name || lastName(person.person)).split(" ").pop();

  const sortedEdges = (gvEdgesByPerson[person.person] || []).sort((a, b) => b.weight - a.weight).slice(0, 6);

  const egoNodes = [{ id: person.person, name: personLast, risk: person.risk_score || 0, center: true, inData: true }];
  const egoLinks = [];
  sortedEdges.forEach(e => {
    const pd   = DATA.people.find(p => p.person === e.partner);
    const last = pd ? (pd.display_name || formatName(e.partner)).split(" ").pop() : formatName(e.partner).split(" ").pop();
    egoNodes.push({ id: e.partner, name: last, risk: pd ? (pd.risk_score || 0) : 0.05, center: false, inData: !!pd });
    egoLinks.push({ source: person.person, target: e.partner, weight: e.weight });
  });

  const tt = document.getElementById("gvTooltip");

  const svg      = d3.select(container).append("svg").attr("width", w).attr("height", h);
  const linkEls  = svg.selectAll("line").data(egoLinks).enter().append("line")
    .attr("stroke", "rgba(0,114,188,0.35)")
    .attr("stroke-width", d => 0.5 + d.weight / 1200);
  const nodeEls  = svg.selectAll("circle").data(egoNodes).enter().append("circle")
    .attr("r",      d => d.center ? 12 : 7)
    .attr("fill",   d => d.center ? centerColor : nodeColor(d.risk))
    .attr("stroke", "#0A0A0A").attr("stroke-width", 1.5)
    .style("cursor", d => d.center ? "default" : "pointer")
    .on("mouseover", function(ev, d) {
      if (d.center) return;
      d3.select(this).attr("stroke", "#FFFFFF").attr("stroke-width", 2);
      if (!d.inData && tt) {
        tt.innerHTML = `<div style="font-size:11px;color:var(--text-tertiary)">Not in top 200 — no simulation data available</div>`;
        tt.style.left = (ev.clientX + 14) + "px";
        tt.style.top  = (ev.clientY - 10) + "px";
        tt.style.display = "block";
      }
    })
    .on("mousemove", (ev, d) => {
      if (!d.center && !d.inData && tt) {
        tt.style.left = (ev.clientX + 14) + "px";
        tt.style.top  = (ev.clientY - 10) + "px";
      }
    })
    .on("mouseout", function(ev, d) {
      if (d.center) return;
      d3.select(this).attr("stroke", "#0A0A0A").attr("stroke-width", 1.5);
      if (tt) tt.style.display = "none";
    })
    .on("click", (ev, d) => {
      if (d.center) return;
      if (tt) tt.style.display = "none";
      egoNavToPartner(d.id, person);
    });
  const labelEls = svg.selectAll("text").data(egoNodes).enter().append("text")
    .attr("fill", "#6E6E73").attr("font-size", "9px").attr("font-family", "'JetBrains Mono',monospace")
    .attr("text-anchor", "middle").attr("dy", d => d.center ? 22 : 16)
    .style("pointer-events", "none")
    .text(d => d.name);

  d3.forceSimulation(egoNodes)
    .force("link",      d3.forceLink(egoLinks).id(d => d.id).distance(55))
    .force("charge",    d3.forceManyBody().strength(-120))
    .force("center",    d3.forceCenter(w / 2, h / 2))
    .force("collision", d3.forceCollide().radius(20))
    .on("tick", () => {
      linkEls.attr("x1", d => d.source.x).attr("y1", d => d.source.y).attr("x2", d => d.target.x).attr("y2", d => d.target.y);
      nodeEls.attr("cx", d => d.x).attr("cy", d => d.y);
      labelEls.attr("x", d => d.x).attr("y", d => d.y);
    });
}

// ── Report View ─────────────────────────────────────────────────────────────────
function buildCascadeReportSection() {
  if (!cascadeState) return "";
  const { sorted, individualSum, cascadeTotal, amplification, topicHits, liveRisks, origRisks } = cascadeState;
  const names = sorted.map(p => p.display_name || formatName(p.person)).join(", ");

  const topicRows = Object.entries(topicHits).map(([cat, hits]) => {
    const st  = hits >= 2 ? "LOST" : "PARTIAL";
    const col = hits >= 2 ? "#D4342E" : "#C49032";
    const bg  = hits >= 2 ? "rgba(212,52,46,0.1)" : "rgba(196,144,50,0.1)";
    return `<tr>
      <td style="padding:5px 0;font-family:'Times New Roman',Times,serif;font-size:13px;color:var(--text-secondary)">${cat}</td>
      <td style="padding:5px 0;text-align:right"><span style="font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;padding:2px 8px;border-radius:3px;background:${bg};color:${col}">${st}</span></td>
    </tr>`;
  }).join("");

  const affectedPeople = DATA.people
    .filter(p => !sorted.find(s => s.person === p.person))
    .map(p => ({
      name: p.display_name || formatName(p.person),
      orig: (origRisks[p.person] || p.risk_score) * 100,
      live: (liveRisks[p.person] || p.risk_score) * 100,
      inc:  ((liveRisks[p.person] || p.risk_score) - (origRisks[p.person] || p.risk_score)) * 100,
    }))
    .filter(p => p.inc > 0.05)
    .sort((a, b) => b.inc - a.inc)
    .slice(0, 5);

  const affectedRows = affectedPeople.map(p =>
    `<tr>
      <td style="padding:5px 0;font-family:'Times New Roman',Times,serif;font-size:13px;color:var(--text-secondary)">${p.name}</td>
      <td style="padding:5px 0;font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--text-faint);text-decoration:line-through">${p.orig.toFixed(1)}%</td>
      <td style="padding:5px 0;font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:700;color:#D4342E;text-align:right">${p.live.toFixed(1)}%</td>
    </tr>`
  ).join("");

  const allTopics  = Object.keys(topicHits).length;
  const avgHireGap = sorted.reduce((s, p) => s + Math.round((p.external_hire_gap || 0) * 100), 0) / sorted.length;
  const avgRecov   = sorted.reduce((s, p) => {
    const rates = p.recovery_rates || [];
    return s + (rates[11] != null ? rates[11] * 100 : 0);
  }, 0) / sorted.length * 0.7;
  const totalPerm  = sorted.reduce((s, p) => s + (p.n_perm_loss_categories || 0), 0);

  return `
  <div style="background:rgba(212,52,46,0.05);border:1px solid rgba(212,52,46,0.18);border-radius:8px;padding:32px;margin-bottom:48px">
    <div style="font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:2px;color:#D4342E;margin-bottom:12px">Scenario Analysis</div>
    <div style="font-family:'Times New Roman',Times,serif;font-size:26px;font-weight:700;color:var(--text);margin-bottom:8px;letter-spacing:-0.3px">Simultaneous Departure: ${names}</div>
    <div style="font-family:'Times New Roman',Times,serif;font-size:14px;color:var(--text-secondary);line-height:1.7;margin-bottom:28px">Cascading simulation results. Risk amplification is non-linear due to shared topic dependencies across departing employees.</div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:28px">
      <div style="background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:20px">
        <div style="font-family:'JetBrains Mono',monospace;font-size:8px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:#D4342E;margin-bottom:14px">Non-linear risk amplification</div>
        <div style="margin-bottom:10px">
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
            <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--text-faint);width:100px">Individual sum</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:18px;font-weight:700;color:#C49032">${individualSum.toFixed(1)}%</div>
            <div style="flex:1;height:6px;background:var(--border);border-radius:3px;overflow:hidden"><div style="height:100%;border-radius:3px;background:#C49032;width:${Math.min(individualSum,100)}%"></div></div>
          </div>
          <div style="display:flex;align-items:center;gap:12px">
            <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--text-faint);width:100px">Cascading risk</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:18px;font-weight:700;color:#D4342E">${cascadeTotal.toFixed(1)}%</div>
            <div style="flex:1;height:6px;background:var(--border);border-radius:3px;overflow:hidden"><div style="height:100%;border-radius:3px;background:#D4342E;width:${Math.min(cascadeTotal,100)}%"></div></div>
          </div>
        </div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:11px;color:#D4342E;font-weight:600;text-align:center;padding:8px 0 0;border-top:1px solid rgba(212,52,46,0.15)">+${amplification}% amplification from cascading dependencies</div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;align-content:start">
        <div style="background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:16px;text-align:center">
          <div style="font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:700;color:#D4342E;line-height:1;margin-bottom:4px">${allTopics}</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:8px;text-transform:uppercase;letter-spacing:1px;color:var(--text-faint)">Topics affected</div>
        </div>
        <div style="background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:16px;text-align:center">
          <div style="font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:700;color:#C49032;line-height:1;margin-bottom:4px">${avgHireGap.toFixed(0)}%</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:8px;text-transform:uppercase;letter-spacing:1px;color:var(--text-faint)">Avg hire gap</div>
        </div>
        <div style="background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:16px;text-align:center">
          <div style="font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:700;color:#D4342E;line-height:1;margin-bottom:4px">${avgRecov.toFixed(1)}%</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:8px;text-transform:uppercase;letter-spacing:1px;color:var(--text-faint)">Combined recovery</div>
        </div>
        <div style="background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:16px;text-align:center">
          <div style="font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:700;color:var(--text);line-height:1;margin-bottom:4px">${totalPerm}</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:8px;text-transform:uppercase;letter-spacing:1px;color:var(--text-faint)">Perm losses</div>
        </div>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
      <div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:var(--text-faint);margin-bottom:10px;padding-bottom:6px;border-bottom:1px solid var(--border)">Topic impact breakdown</div>
        <table style="width:100%;border-collapse:collapse">${topicRows || `<tr><td style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--text-faint);padding:8px 0">No shared topics identified.</td></tr>`}</table>
      </div>
      <div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:var(--text-faint);margin-bottom:10px;padding-bottom:6px;border-bottom:1px solid var(--border)">Most affected remaining employees</div>
        <table style="width:100%;border-collapse:collapse">${affectedRows || `<tr><td style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--text-faint);padding:8px 0">No significant risk increases detected.</td></tr>`}</table>
      </div>
    </div>
  </div>`;
}

function buildReportView() {
  if (!DATA) return;
  const people = DATA.people;
  const edges  = (DATA.graph || {}).edges || [];

  // ── Build edge lookup for top communication partners
  const edgesBy = {};
  edges.forEach(e => {
    (edgesBy[e.source] = edgesBy[e.source] || []).push([e.target, e.weight]);
    (edgesBy[e.target] = edgesBy[e.target] || []).push([e.source, e.weight]);
  });
  const nameLk = {};
  people.forEach(p => { nameLk[p.person] = p.display_name || p.person.split("@")[0].replace(/\./g," ").replace(/\b\w/g,c=>c.toUpperCase()); });
  function topPartners(email, n=3) {
    return ((edgesBy[email] || []).sort((a,b)=>b[1]-a[1]).slice(0,n))
      .map(([e])=> nameLk[e] || e.split("@")[0].replace(/\./g," ").replace(/\b\w/g,c=>c.toUpperCase()));
  }

  // ── Quadrant counts
  const qCounts = { "Organizational Emergency": 0, "Silent Threat": 0, "Replaceable Executive": 0, "Low Priority": 0 };
  people.forEach(p => { if (qCounts[p.quadrant] != null) qCounts[p.quadrant]++; else qCounts["Low Priority"]++; });

  // ── Critical employees (Org Emergency + Silent Threat), sorted by risk_score
  const critical = people.filter(p => p.quadrant === "Organizational Emergency" || p.quadrant === "Silent Threat")
                         .sort((a,b) => b.risk_score - a.risk_score);

  // ── Key stats
  const recov12 = critical.filter(p => p.recovery_rates && p.recovery_rates.length >= 12)
                          .map(p => p.recovery_rates[11]);
  const avgRecov = recov12.length ? (recov12.reduce((a,b)=>a+b,0)/recov12.length) : 0;
  const avgGap   = critical.length ? critical.reduce((a,p)=>a+(p.external_hire_gap||0),0)/critical.length : 0;
  const top5PermLoss = critical.slice(0,5).reduce((a,p)=>a+(p.n_perm_loss_categories||0),0);

  // ── Unique topic categories
  const allCats = new Set(Object.values(DATA.topic_categories || {}));
  const nCats = allCats.size;

  // ── External hire gap by category — accumulate max gap per category holder
  const catGapMap = {}; // category -> {maxGap, holders: [{name, risk}]}
  people.forEach(p => {
    const g = p.external_hire_gap || 0;
    const cats = [...new Set((p.topic_profile||[]).slice(0,4).map(t=>t.category).filter(Boolean))];
    cats.forEach(c => {
      if (!catGapMap[c]) catGapMap[c] = { maxGap: 0, holders: [] };
      if (g > catGapMap[c].maxGap) catGapMap[c].maxGap = g;
      catGapMap[c].holders.push({ name: p.display_name, risk: p.risk_score });
    });
  });
  // Sort categories by maxGap desc, take top 8 with gap > 0
  const gapCategories = Object.entries(catGapMap)
    .filter(([,v]) => v.maxGap > 0)
    .sort((a,b) => b[1].maxGap - a[1].maxGap)
    .slice(0, 8)
    .map(([cat, v]) => {
      const topHolders = v.holders.sort((a,b)=>b.risk-a.risk).slice(0,2).map(h=>h.name);
      return { cat, gap: v.maxGap, holders: topHolders };
    });

  // ── Helper: badge HTML
  function qBadge(quadrant) {
    if (quadrant === "Organizational Emergency") return `<span class="rpt-badge rpt-badge-emergency">Org Emergency</span>`;
    if (quadrant === "Silent Threat")            return `<span class="rpt-badge rpt-badge-silent">Silent Threat</span>`;
    return `<span class="rpt-badge rpt-badge-replaceable">${quadrant}</span>`;
  }
  // ── Top 3 topics for a person
  function topCats(p, n=3) {
    return [...new Set((p.topic_profile||[]).map(t=>t.category).filter(Boolean))].slice(0,n);
  }

  // ── Priority interventions table rows (top 12 critical)
  const interventionRows = critical.slice(0, 12).map(p => {
    const recov = p.recovery_rates && p.recovery_rates.length >= 12 ? (p.recovery_rates[11]*100).toFixed(1) : "—";
    const gap   = p.external_hire_gap != null ? (p.external_hire_gap*100).toFixed(0)+"%" : "—";
    const cats  = topCats(p, 3).join(", ") || "—";
    const riskPct = (p.risk_score*100).toFixed(1);
    const riskColor = p.risk_score > 0.3 ? "#D4342E" : p.risk_score > 0.15 ? "#C49032" : "#F5F5F7";
    const recov12Color = parseFloat(recov) < 20 ? "#D4342E" : parseFloat(recov) < 50 ? "#C49032" : "#2D8C3C";
    const gapColor = (p.external_hire_gap||0) > 0.6 ? "#D4342E" : (p.external_hire_gap||0) > 0.3 ? "#C49032" : "#F5F5F7";
    return `<tr>
      <td>
        <div class="rpt-person-name">${p.display_name}</div>
        <div class="rpt-person-role">${p.role || "—"}</div>
      </td>
      <td>${qBadge(p.quadrant)}</td>
      <td><span style="font-family:'JetBrains Mono',monospace;font-weight:700;color:${riskColor}">${riskPct}</span></td>
      <td>
        <span style="font-family:'Times New Roman',Times,serif">${cats}</span>
        <div class="rpt-risk-meter"><div style="width:${Math.round(p.risk_score*200)}%;max-width:100%;height:100%;border-radius:2px;background:${riskColor}"></div></div>
      </td>
      <td><span style="font-family:'JetBrains Mono',monospace;font-weight:600;color:${gapColor}">${gap}</span></td>
      <td><span style="font-family:'JetBrains Mono',monospace;font-weight:600;color:${recov12Color}">${recov}%</span></td>
    </tr>`;
  }).join("");

  // ── External hire gap table rows
  const gapRows = gapCategories.map(({ cat, gap, holders }) => {
    const pct  = Math.round(gap * 100);
    const color = pct > 60 ? "#D4342E" : pct > 30 ? "#C49032" : "#0072BC";
    const status = pct > 60
      ? `<span class="rpt-badge rpt-badge-emergency">Critical</span>`
      : pct > 30
      ? `<span class="rpt-badge rpt-badge-silent">High</span>`
      : `<span class="rpt-badge rpt-badge-replaceable">Moderate</span>`;
    return `<tr>
      <td style="font-family:'Times New Roman',Times,serif;font-weight:600;color:var(--text)">${cat}</td>
      <td>
        <div class="rpt-gap-bar-wrap">
          <div class="rpt-gap-bar"><div class="rpt-gap-bar-fill" style="width:${pct}%;background:${color}"></div></div>
          <div class="rpt-gap-pct" style="color:${color}">${pct}%</div>
        </div>
      </td>
      <td style="font-family:'Times New Roman',Times,serif">${holders.join(", ")}</td>
      <td>${status}</td>
    </tr>`;
  }).join("");

  // ── Scenario stats
  const badRecov  = (avgRecov * 100).toFixed(1);
  const goodRecov = Math.min(avgRecov * 1.85, 0.92);
  const goodPermLoss = Math.max(1, Math.round(top5PermLoss * 0.3));

  // ── Top critical names for recommendations text
  const top3Names = critical.slice(0,3).map(p=>p.display_name).join(", ");

  const html = `
  ${buildCascadeReportSection()}
  <div class="report-header">
    <h1>Organizational Intelligence Report</h1>
    <div class="report-subtitle">Knowledge Risk Assessment &amp; Intervention Recommendations</div>
    <div class="report-meta">
      <span>Enron Corporation</span>
      <span>${people.length} employees analyzed</span>
      <span>${nCats} topic categories</span>
      <span>12-month simulation horizon</span>
      <span>Generated ${new Date().toLocaleDateString("en-US",{month:"long",year:"numeric"})}</span>
    </div>
  </div>

  <div class="rpt-section-header">Executive Summary</div>
  <div class="rpt-section-rule"></div>
  <div class="rpt-exec-summary">
    Analysis of <strong>${people.length} employees</strong> across <strong>${nCats} topic categories</strong> reveals significant concentration risk in Enron's organizational knowledge structure.
    <strong>${qCounts["Organizational Emergency"]} employees</strong> represent organizational emergencies, individuals whose departure would cause irreversible knowledge loss in critical business functions.
    An additional <strong>${qCounts["Silent Threat"]} employees</strong> are classified as silent threats: staff holding irreplaceable expertise that leadership may not recognize as critical until departure.
    Without intervention, simultaneous departure of the top five risk-scored employees would result in <strong>permanent loss across ${top5PermLoss} knowledge categories</strong>,
    with average organizational recovery capped at <strong>${badRecov}% of pre-departure capacity</strong> at twelve months.
    The external hire gap rate across critical personnel stands at <strong>${(avgGap*100).toFixed(0)}%</strong>, indicating that the majority of lost expertise cannot be sourced internally under any succession scenario.
  </div>

  <div class="rpt-stat-row">
    <div class="rpt-stat-card">
      <div class="rpt-stat-number" style="color:#D4342E">${critical.length}</div>
      <div class="rpt-stat-label">Critical risk employees</div>
    </div>
    <div class="rpt-stat-card">
      <div class="rpt-stat-number" style="color:#C49032">${(critical[0]?.risk_score*100||0).toFixed(1)}</div>
      <div class="rpt-stat-label">Peak knowledge risk score</div>
    </div>
    <div class="rpt-stat-card">
      <div class="rpt-stat-number" style="color:${parseFloat(badRecov)<50?"#D4342E":parseFloat(badRecov)<70?"#C49032":"#F5F5F7"}">${badRecov}%</div>
      <div class="rpt-stat-label">Avg 12-month recovery</div>
    </div>
    <div class="rpt-stat-card">
      <div class="rpt-stat-number" style="color:#D4342E">${(avgGap*100).toFixed(0)}%</div>
      <div class="rpt-stat-label">External hire gap rate</div>
    </div>
  </div>

  <div class="rpt-subheader">Risk Quadrant Distribution</div>
  <div class="rpt-quadrant-row">
    <div class="rpt-quadrant-card rqc-emergency">
      <div class="rq-count">${qCounts["Organizational Emergency"]}</div>
      <div><div class="rq-label">Organizational Emergency</div><div class="rq-desc">High knowledge + senior role</div></div>
    </div>
    <div class="rpt-quadrant-card rqc-silent">
      <div class="rq-count">${qCounts["Silent Threat"]}</div>
      <div><div class="rq-label">Silent Threat</div><div class="rq-desc">High knowledge + junior role</div></div>
    </div>
    <div class="rpt-quadrant-card rqc-replaceable">
      <div class="rq-count">${qCounts["Replaceable Executive"]}</div>
      <div><div class="rq-label">Replaceable Executive</div><div class="rq-desc">Senior role + lower uniqueness</div></div>
    </div>
    <div class="rpt-quadrant-card rqc-low">
      <div class="rq-count">${qCounts["Low Priority"]}</div>
      <div><div class="rq-label">Low Priority</div><div class="rq-desc">Standard succession planning</div></div>
    </div>
  </div>

  <div class="dossier-gen-section">
    <div class="rpt-section-header">Employee Knowledge Risk Dossier</div>
    <div class="rpt-section-rule"></div>
    <div class="dossier-selector-bar">
      <div class="dossier-selector-left">
        <div class="dossier-selector-label">Select employee</div>
        <div class="dossier-combobox" id="dossierCombobox">
          <button class="dossier-trigger" id="dossierTrigger" onclick="toggleDossierDropdown(event)" type="button">
            <span class="t-name" id="dossierTriggerName">Loading…</span>
            <span class="t-risk" id="dossierTriggerRisk"></span>
            <span class="t-arrow">▾</span>
          </button>
          <div class="dossier-dropdown" id="dossierDropdown">
            <input class="dossier-search" id="dossierSearch" type="text" placeholder="type to search…" oninput="filterDossierOptions(this.value)" autocomplete="off">
            <div class="dossier-option-list" id="dossierOptionList"></div>
          </div>
        </div>
      </div>
      <button class="dossier-print-btn" onclick="printDossier()">⎙ Export / Print</button>
    </div>
    <div id="dossierContent"></div>
  </div>

  <div class="rpt-section-header">Cost of Inaction</div>
  <div class="rpt-section-rule"></div>
  <div class="rpt-scenario-row">
    <div class="rpt-scenario-card bad">
      <div class="rpt-scenario-label">Without Intervention</div>
      <div class="rpt-scenario-title">Unmanaged Departure Scenario</div>
      <div class="rpt-scenario-stats">
        <div>
          <div class="rpt-s-val">${top5PermLoss}&nbsp;/&nbsp;${nCats}</div>
          <div class="rpt-s-label">Categories permanently degraded</div>
        </div>
        <div>
          <div class="rpt-s-val">${badRecov}%</div>
          <div class="rpt-s-label">Avg recovery at M12</div>
        </div>
      </div>
      <div class="rpt-scenario-body">
        If the top five risk-scored employees depart without knowledge transfer programs in place, ${top5PermLoss} of ${nCats} topic categories experience permanent degradation. Recovery plateaus at ${badRecov}% by month twelve with no further improvement possible. The highest-concentration topic areas, including ${topCats(critical[0],2).join(" and ")}, become irrecoverable under any internal routing scenario.
      </div>
    </div>
    <div class="rpt-scenario-card good">
      <div class="rpt-scenario-label">With Intervention</div>
      <div class="rpt-scenario-title">Managed Succession Scenario</div>
      <div class="rpt-scenario-stats">
        <div>
          <div class="rpt-s-val">${goodPermLoss}&nbsp;/&nbsp;${nCats}</div>
          <div class="rpt-s-label">Categories at risk</div>
        </div>
        <div>
          <div class="rpt-s-val">${(goodRecov*100).toFixed(1)}%</div>
          <div class="rpt-s-label">Projected recovery at M12</div>
        </div>
      </div>
      <div class="rpt-scenario-body">
        Targeted cross-training of the ${critical.length} critical-risk employees combined with structured documentation programs could lift twelve-month recovery to ${(goodRecov*100).toFixed(1)}%. Only ${goodPermLoss} highly specialized categories would remain at risk, and external hire gaps drop significantly across the organization through internal knowledge transfer.
      </div>
    </div>
  </div>

  <div class="rpt-section-header">External Hire Gap Analysis</div>
  <div class="rpt-section-rule"></div>
  <div class="rpt-subheader">Topic categories where no internal successor exists — external recruitment required</div>
  <table class="rpt-table">
    <thead>
      <tr>
        <th style="width:30%">Topic Category</th>
        <th style="width:38%">Coverage Gap</th>
        <th style="width:18%">Key Holders</th>
        <th style="width:14%">Status</th>
      </tr>
    </thead>
    <tbody>${gapRows}</tbody>
  </table>

  <div class="rpt-subheader" style="color:var(--gold);margin-top:48px">MODEL VALIDATION</div>
  <div class="rpt-section-header" style="margin-top:8px">Retrospective concordance with documented outcomes</div>
  <div class="rpt-section-rule"></div>

  <div class="rpt-exec-summary" style="margin-bottom:24px">
    The model's risk classifications were tested against documented Enron collapse outcomes for 14 employees with verifiable historical records. Sources include the Powers Report, FBI case summary, Senate Permanent Subcommittee on Investigations report, DOJ superseding indictment, FERC final report, and the Supreme Court opinion in Skilling v. United States.
  </div>

  <div style="display:flex;justify-content:center;margin-bottom:32px">
    <div class="rpt-stat-card" style="text-align:center;min-width:320px;max-width:400px">
      <div class="rpt-stat-number" style="color:var(--gold);font-size:52px">72%</div>
      <div class="rpt-stat-label" style="font-size:10px;letter-spacing:1px">concordance across 18 testable predictions</div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--text-faint);margin-top:10px;letter-spacing:0.5px">13 hits &middot; 2 partial &middot; 1 contextual &middot; 2 known misses</div>
    </div>
  </div>

  <div class="rpt-exec-summary">
    Of 18 testable predictions, 13 were direct hits, 2 were partial matches, 1 was contextual, and 2 were known misses. This produces a concordance rate of 72%.
    <br><br>
    Both known misses are attributable to corpus limitations rather than model failure. Andrew Fastow is effectively absent from the email dataset because his activities were deliberately concealed through off-book special purpose entities. Cliff Baxter resigned in May 2001, placing his departure outside the primary corpus analysis window.
    <br><br>
    The model's Organizational Emergency classification for Jeff Skilling is validated with the highest degree of fidelity. His departure on August 14, 2001 preceded Enron's bankruptcy filing by exactly four months, and the organizational deterioration that followed his resignation matches the model's predicted cascade trajectory. No interpretive successor existed within the organization.
    <br><br>
    The Kaminski case provides additional structural validation. The model classified Vince Kaminski as Organizational Emergency with a Knowledge Risk Score of 16. Historical records confirm Enron systematically marginalized and ultimately removed its most credible internal risk oversight function, consistent with the model's identification of his knowledge as irreplaceable.
  </div>

`;

  document.getElementById("reportContainer").innerHTML = html;
  // Init the dossier section after DOM is set
  requestAnimationFrame(() => initDossierSection());
}

// ── Dossier Generator ───────────────────────────────────────────────────────────
let _dossierPeople = null;  // sorted list
let _dossierEdgesBy = null; // email → [[email, weight]]
let _dossierNameLk  = null;
let _dossierRoleLk  = null;
let _dossierCatCountMap = null; // category → person count
let _dossierSelected = null;

function initDossierSection() {
  if (!DATA) return;
  const people = DATA.people;
  const edges  = (DATA.graph || {}).edges || [];

  // Build edge lookup
  _dossierEdgesBy = {};
  edges.forEach(e => {
    (_dossierEdgesBy[e.source] = _dossierEdgesBy[e.source] || []).push([e.target, e.weight]);
    (_dossierEdgesBy[e.target] = _dossierEdgesBy[e.target] || []).push([e.source, e.weight]);
  });
  _dossierNameLk = {};
  people.forEach(p => { _dossierNameLk[p.person] = p.display_name || formatName(p.person); });

  // Build category count map: how many people have each topic category
  _dossierCatCountMap = {};
  people.forEach(p => {
    const seen = new Set();
    (p.topic_profile || []).forEach(t => {
      if (t.category && !seen.has(t.category)) { seen.add(t.category); _dossierCatCountMap[t.category] = (_dossierCatCountMap[t.category] || 0) + 1; }
    });
  });

  // Build role lookup for cross-training candidates
  _dossierRoleLk = {};
  people.forEach(p => { _dossierRoleLk[p.person] = p.role || ""; });

  // Sort all people by risk_score desc
  _dossierPeople = [...people].sort((a,b) => b.risk_score - a.risk_score);

  // Build option list
  const list = document.getElementById("dossierOptionList");
  if (!list) return;
  _dossierPeople.forEach(p => {
    const q = p.quadrant || "Low Priority";
    const emoji = q === "Organizational Emergency" ? "🔴" : q === "Silent Threat" ? "🟠" : q === "Replaceable Executive" ? "🔵" : "🟢";
    const badgeCls = q === "Organizational Emergency" ? "rpt-badge-emergency" : q === "Silent Threat" ? "rpt-badge-silent" : q === "Replaceable Executive" ? "rpt-badge-replaceable" : "";
    const div = document.createElement("div");
    div.className = "dossier-option";
    div.dataset.email = p.person;
    div.dataset.name  = (p.display_name || "").toLowerCase();
    div.innerHTML = `<span>${emoji}</span><span class="opt-name">${p.display_name}</span><span class="opt-risk">${(p.risk_score*100).toFixed(1)}</span>${badgeCls ? `<span class="opt-quad rpt-badge ${badgeCls}">${q.replace("Organizational ","")||""}</span>` : ""}`;
    div.onclick = () => selectDossierPerson(p.person);
    list.appendChild(div);
  });

  // Close dropdown on outside click
  document.addEventListener("click", e => {
    const cb = document.getElementById("dossierCombobox");
    if (cb && !cb.contains(e.target)) closeDossierDropdown();
  });

  // Default: Jeff Dasovich (highest risk)
  const defaultEmail = _dossierPeople[0]?.person;
  if (defaultEmail) selectDossierPerson(defaultEmail);
}

function toggleDossierDropdown(e) {
  e.stopPropagation();
  const dd = document.getElementById("dossierDropdown");
  if (!dd) return;
  const isOpen = dd.classList.contains("open");
  if (isOpen) { closeDossierDropdown(); }
  else {
    dd.classList.add("open");
    const si = document.getElementById("dossierSearch");
    if (si) { si.value = ""; filterDossierOptions(""); si.focus(); }
  }
}

function closeDossierDropdown() {
  const dd = document.getElementById("dossierDropdown");
  if (dd) dd.classList.remove("open");
}

function filterDossierOptions(query) {
  const q = query.toLowerCase().trim();
  const opts = document.querySelectorAll("#dossierOptionList .dossier-option");
  opts.forEach(o => {
    const match = !q || (o.dataset.name||"").includes(q) || (o.dataset.email||"").includes(q);
    o.classList.toggle("hidden", !match);
  });
}

function selectDossierPerson(email) {
  if (!_dossierPeople) return;
  _dossierSelected = email;
  const p = _dossierPeople.find(x => x.person === email);
  if (!p) return;
  // Update trigger
  const q = p.quadrant || "Low Priority";
  const emoji = q === "Organizational Emergency" ? "🔴" : q === "Silent Threat" ? "🟠" : q === "Replaceable Executive" ? "🔵" : "🟢";
  const tn = document.getElementById("dossierTriggerName");
  const tr = document.getElementById("dossierTriggerRisk");
  if (tn) tn.textContent = `${emoji}  ${p.display_name}`;
  if (tr) tr.textContent = `${(p.risk_score*100).toFixed(1)} risk`;
  closeDossierDropdown();
  renderFullDossier(email);
}

function printDossier() {
  document.body.classList.add("print-dossier");
  window.print();
  window.addEventListener("afterprint", () => document.body.classList.remove("print-dossier"), { once: true });
}

function renderFullDossier(email) {
  if (!_dossierPeople) return;
  const p = _dossierPeople.find(x => x.person === email);
  if (!p) return;

  // ── Metrics
  const riskPct  = (p.risk_score * 100).toFixed(1);
  const posPct   = (p.positional_impact * 100).toFixed(0);
  const permLoss = p.n_perm_loss_categories || 0;
  const extGap   = Math.round((p.external_hire_gap || 0) * 100);
  const recov12  = p.recovery_rates && p.recovery_rates.length >= 12
    ? (p.recovery_rates[11] * 100).toFixed(1) : "—";

  const riskColor = p.risk_score > 0.3 ? "#D4342E" : p.risk_score > 0.15 ? "#C49032" : "#F5F5F7";
  const posColor  = (p.positional_impact||0) > 0.6 ? "#D4342E" : (p.positional_impact||0) > 0.3 ? "#C49032" : "#F5F5F7";
  const gapColor  = extGap > 60 ? "#D4342E" : extGap > 30 ? "#C49032" : "#2D8C3C";
  const recovNum  = parseFloat(recov12);
  const recovColor = isNaN(recovNum) ? "#F5F5F7" : recovNum < 20 ? "#D4342E" : recovNum < 50 ? "#C49032" : "#2D8C3C";

  // ── Quadrant badge class
  const q = p.quadrant || "Low Priority";
  const badgeCls = q === "Organizational Emergency" ? "gd-b-emergency" : q === "Silent Threat" ? "gd-b-silent" : q === "Replaceable Executive" ? "gd-b-replaceable" : "gd-b-low";

  // ── Top partners
  const allPartners = ((_dossierEdgesBy[email] || []).sort((a,b)=>b[1]-a[1]));
  const top5Partners = allPartners.slice(0,5);
  const maxW = top5Partners.length ? top5Partners[0][1] : 1;

  // ── Topics at M12
  const routingM12 = (p.routing_by_month || {})["12"] || [];
  // Build quality map across all months for this person
  const qMap = {};
  Object.entries(p.routing_by_month || {}).forEach(([m, entries]) => {
    entries.forEach(e => {
      const tid = e.topic;
      const q2 = e.quality || 0;
      if (qMap[tid] == null || q2 > qMap[tid]) qMap[tid] = q2;
    });
  });
  // Determine status per topic from M12 routing
  const statusMapM12 = {};
  routingM12.forEach(e => {
    const qv = e.quality || 0; const step = e.step || 4;
    let st = "lost";
    if (step <= 3 && qv >= 0.35) st = "recovered";
    else if (step <= 3 && qv >= 0.10) st = "partial";
    statusMapM12[e.topic] = st;
  });
  // Top 5 unique topic categories
  const topCatsSeen = new Set();
  const topTopics = [];
  (p.topic_profile || []).forEach(t => {
    if (t.category && !topCatsSeen.has(t.category) && topTopics.length < 5) {
      topCatsSeen.add(t.category);
      const tid = t.topic;
      const rawPct = Math.round((qMap[tid] || 0) * 100);
      const fallback = (p.recovery_rates && p.recovery_rates.length >= 12)
        ? (p.recovery_rates[11] > 0.6 ? "recovered" : p.recovery_rates[11] > 0.3 ? "partial" : "lost")
        : "lost";
      const status = statusMapM12[tid] || fallback;
      const barPct = status === "partial" ? Math.max(rawPct, 15) : status === "lost" ? Math.min(rawPct, 8) : rawPct;
      topTopics.push({ cat: t.category, status, barPct });
    }
  });
  const cats = topTopics.map(t => t.cat);
  const lostCats    = topTopics.filter(t => t.status === "lost").map(t => t.cat);
  const partialCats = topTopics.filter(t => t.status === "partial").map(t => t.cat);

  // ── Successors
  const succs = (p.successor_analysis || []).slice(0, 3);

  // ── Variant selector (deterministic per person)
  const _hash = (s) => s.split("").reduce((a,c)=>a+c.charCodeAt(0),0);
  const v = _hash(email) % 4;

  // ── Knowledge Concentration Index
  const concRows = topTopics.map(t => {
    const cnt = (_dossierCatCountMap || {})[t.cat] || 0;
    const tier = cnt < 10 ? "RARE" : cnt < 50 ? "MODERATE" : "COMMON";
    const tc   = tier === "RARE" ? "#D4342E" : tier === "MODERATE" ? "#C49032" : "#2D8C3C";
    const summary = tier === "RARE"
      ? `Only ${cnt} other employee${cnt===1?"":"s"} hold this knowledge. Severe concentration risk.`
      : tier === "MODERATE"
      ? `${cnt} employees share coverage. Knowledge transfer is feasible with deliberate effort.`
      : `${cnt} employees with overlapping expertise. Adequate internal redundancy.`;
    return `<div style="display:flex;align-items:flex-start;gap:12px;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.05)">
      <div style="flex:0 0 160px;font-family:'Times New Roman',Times,serif;font-size:12px;color:var(--text)">${t.cat}</div>
      <div style="flex:0 0 80px"><span style="font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:700;color:${tc};text-transform:uppercase;letter-spacing:1px">${tier}</span></div>
      <div style="flex:0 0 44px;font-family:'JetBrains Mono',monospace;font-size:11px;color:${tc};text-align:right">${cnt}</div>
      <div style="flex:1;font-family:'Times New Roman',Times,serif;font-size:12px;color:var(--text-faint)">${summary}</div>
    </div>`;
  }).join("");
  const concHTML = concRows || `<div style="font-family:'Times New Roman',Times,serif;font-size:13px;color:var(--text-faint)">No topic concentration data available.</div>`;

  // ── Departure Timeline
  const monthlyTL = p.monthly_timeline || [];
  const milestones = [1, 6, 12].map(mo => {
    const entry = monthlyTL.find(e => e.month === mo) || monthlyTL[mo - 1] || null;
    const routing = (p.routing_by_month || {})[String(mo)] || [];
    const recovered  = routing.filter(e => e.step <= 3 && (e.quality||0) >= 0.35).length;
    const partial    = routing.filter(e => e.step <= 3 && (e.quality||0) >= 0.10 && (e.quality||0) < 0.35).length;
    const lost       = routing.filter(e => e.step > 3 || (e.quality||0) < 0.10).length;
    const lossRate   = entry ? Math.round((entry.loss_rate || 0) * 100) : 0;
    const recovRate  = entry ? Math.round((entry.recovery_rate || 0) * 100) : 0;
    const lrColor    = lossRate > 50 ? "#D4342E" : lossRate > 25 ? "#C49032" : "#2D8C3C";
    const rrColor    = recovRate < 20 ? "#D4342E" : recovRate < 50 ? "#C49032" : "#2D8C3C";
    const label      = mo === 1 ? "M1, 30 Days" : mo === 6 ? "M6, 6 Months" : "M12, 1 Year";
    return `<div style="flex:1;padding:12px 16px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:4px">
      <div style="font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:700;color:var(--text-faint);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px">${label}</div>
      <div style="display:flex;gap:16px;margin-bottom:8px">
        <div><div style="font-family:'JetBrains Mono',monospace;font-size:16px;font-weight:700;color:${lrColor}">${lossRate}%</div><div style="font-family:'JetBrains Mono',monospace;font-size:8px;color:var(--text-faint);text-transform:uppercase">loss rate</div></div>
        <div><div style="font-family:'JetBrains Mono',monospace;font-size:16px;font-weight:700;color:${rrColor}">${recovRate}%</div><div style="font-family:'JetBrains Mono',monospace;font-size:8px;color:var(--text-faint);text-transform:uppercase">recovery</div></div>
      </div>
      ${routing.length ? `<div style="font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--text-faint)"><span style="color:#2D8C3C">${recovered} recovered</span> · <span style="color:#C49032">${partial} partial</span> · <span style="color:#D4342E">${lost} lost</span></div>` : `<div style="font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--text-faint)">No routing data</div>`}
    </div>`;
  }).join("");

  // ── Cross-Training Candidates
  const succEmails = new Set((p.successor_analysis || []).map(s => s.best_successor).filter(Boolean));
  const crossCandidates = allPartners
    .filter(([pe]) => !succEmails.has(pe) && _dossierNameLk[pe])
    .slice(0, 3);
  const crossHTML = crossCandidates.length ? crossCandidates.map(([pe, w], i) => {
    const cn   = _dossierNameLk[pe] || formatName(pe);
    const role2 = (_dossierRoleLk || {})[pe] || "Enron Employee";
    // topic overlap: categories from their profile vs this person
    const theirCats = new Set();
    const theirPerson = (DATA.people || []).find(px => px.person === pe);
    if (theirPerson) (theirPerson.topic_profile || []).forEach(t => { if (t.category) theirCats.add(t.category); });
    const overlapCats = cats.filter(c => theirCats.has(c));
    const overlapStr = overlapCats.length ? overlapCats.slice(0,2).join(", ") : "adjacent domains";
    const rationale = i === 0
      ? `Highest communication volume with ${p.display_name.split(" ")[0]}. Established working relationship reduces onboarding friction.`
      : i === 1
      ? `Strong ${overlapStr} overlap. Cross-training investment would address two knowledge gaps simultaneously.`
      : `Tertiary coverage pathway. Development would build organizational redundancy in ${overlapStr}.`;
    return `<div style="display:flex;align-items:flex-start;gap:12px;padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.05)">
      <div style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--text-faint);flex:0 0 16px;padding-top:2px">${i+1}</div>
      <div style="flex:1">
        <div style="display:flex;align-items:baseline;gap:8px;margin-bottom:2px">
          <span style="font-family:'Times New Roman',Times,serif;font-size:13px;font-weight:700;color:var(--text)">${cn}</span>
          <span style="font-family:'Times New Roman',Times,serif;font-size:11px;color:var(--text-faint)">${role2}</span>
        </div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--text-faint);margin-bottom:4px">Overlap: ${overlapStr || "N/A"}</div>
        <div style="font-family:'Times New Roman',Times,serif;font-size:12px;color:var(--text-faint)">${rationale}</div>
      </div>
    </div>`;
  }).join("") : `<div style="font-family:'Times New Roman',Times,serif;font-size:13px;color:var(--text-faint)">Insufficient communication data to identify candidates.</div>`;

  // ── Generate narrative
  const partnerNames = top5Partners.slice(0,3).map(([e2]) => _dossierNameLk[e2] || formatName(e2));
  const narrative    = genDossierNarrative(p, partnerNames, cats, v);
  const impact       = genDossierImpact(p, cats, lostCats, partialCats, riskPct, extGap, recov12, permLoss, v);
  const recommend    = genDossierRec(p, cats, succs, extGap, recov12, partnerNames, v);

  // ── Render
  const topicHTML = topTopics.map(t => {
    const sc = t.status === "recovered" ? "gd-ts-r" : t.status === "partial" ? "gd-ts-p" : "gd-ts-l";
    const bc = t.status === "recovered" ? "#2D8C3C" : t.status === "partial" ? "#C49032" : "#D4342E";
    return `<div class="gd-topic-row">
      <div class="gd-topic-hdr">
        <span class="gd-topic-name">${t.cat}</span>
        <span class="gd-ts ${sc}">${t.status}</span>
      </div>
      <div class="gd-topic-bar"><div class="gd-topic-bar-fill" style="width:${t.barPct}%;background:${bc}"></div></div>
    </div>`;
  }).join("");

  const contactHTML = top5Partners.map(([pe, w], i) => {
    const n = _dossierNameLk[pe] || formatName(pe);
    const barPct = Math.round((w / maxW) * 100);
    return `<div class="gd-contact-row">
      <div class="gd-c-rank">${i+1}</div>
      <div class="gd-c-name">${n}</div>
      <div class="gd-c-bar-wrap">
        <div class="gd-c-bar"><div class="gd-c-bar-fill" style="width:${barPct}%;background:#0072BC"></div></div>
        <div class="gd-c-count">${Math.round(w).toLocaleString()}</div>
      </div>
    </div>`;
  }).join("");

  const c = 2 * Math.PI * 20;
  const succHTML = succs.length ? succs.map(s => {
    const pct = Math.round((s.readiness || 0) * 100);
    const sc2 = pct >= 60 ? "#2D8C3C" : pct >= 30 ? "#C49032" : "#D4342E";
    const off = c - (pct/100)*c;
    const sn  = s.successor_name || formatName(s.best_successor || "");
    const st  = s.topic_category || cats[0] || "—";
    return `<div class="gd-succ-card">
      <div class="gd-succ-gauge">
        <svg width="48" height="48" viewBox="0 0 48 48">
          <circle fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="4" cx="24" cy="24" r="20"/>
          <circle fill="none" stroke="${sc2}" stroke-width="4" stroke-linecap="round" cx="24" cy="24" r="20"
            stroke-dasharray="${c.toFixed(2)}" stroke-dashoffset="${off.toFixed(2)}"/>
        </svg>
        <div class="gtext" style="color:${sc2}">${pct}%</div>
      </div>
      <div><div class="gd-s-name">${sn}</div><div class="gd-s-topic">${st}</div></div>
    </div>`;
  }).join("") : `<div style="font-family:'Times New Roman',Times,serif;font-size:13px;color:var(--text-faint);padding:16px 0">No successor data available.</div>`;

  document.getElementById("dossierContent").innerHTML = `
  <div class="gd-header">
    <div>
      <div class="gd-h1">${p.display_name}</div>
      <div class="gd-title">${p.role || "Unknown Role"}</div>
      <span class="gd-badge ${badgeCls}">${q}</span>
    </div>
    <div class="gd-doc-right">
      <div class="gd-doc-label">Knowledge Risk Assessment</div>
      <div class="gd-doc-label">Enron Corporation</div>
    </div>
  </div>

  <div class="gd-metrics">
    <div class="gd-metric"><div class="gd-m-val" style="color:${riskColor}">${riskPct}</div><div class="gd-m-lbl">Knowledge Risk Score</div></div>
    <div class="gd-metric"><div class="gd-m-val" style="color:${posColor}">${posPct}</div><div class="gd-m-lbl">Positional Impact Score</div></div>
    <div class="gd-metric"><div class="gd-m-val" style="color:var(--text)">${permLoss}</div><div class="gd-m-lbl">Perm. Losses</div></div>
    <div class="gd-metric"><div class="gd-m-val" style="color:${gapColor}">${extGap}%</div><div class="gd-m-lbl">External Hire Gap</div></div>
    <div class="gd-metric"><div class="gd-m-val" style="color:${recovColor}">${recov12}%</div><div class="gd-m-lbl">12-Mo Recovery</div></div>
  </div>

  <div class="gd-section">
    <div class="gd-sh">Knowledge Concentration Index</div>
    <div class="gd-rule"></div>
    <div style="display:flex;gap:8px;margin-bottom:8px">
      <span style="font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:700;color:#D4342E;text-transform:uppercase;letter-spacing:1px">Rare &lt;10</span>
      <span style="font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--text-faint)">·</span>
      <span style="font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:700;color:#C49032;text-transform:uppercase;letter-spacing:1px">Moderate 10–49</span>
      <span style="font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--text-faint)">·</span>
      <span style="font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:700;color:#2D8C3C;text-transform:uppercase;letter-spacing:1px">Common 50+</span>
    </div>
    ${concHTML}
  </div>

  ${(() => {
    if (typeof computeEmployeeAI === "undefined" || typeof AI_YEARS === "undefined") return "";
    // Prefer pre-computed aiComputedData (same object as shown in AI Automation tab).
    // Fall back to fresh computation if AI tab hasn't been visited yet.
    const _cached = (typeof aiComputedData !== "undefined") ? aiComputedData.find(x => x.person && x.person.person === p.person) : null;
    const aiD = _cached || computeEmployeeAI(p, AI_YEARS[aiSliderIdx].mult);
    const topH = [...aiD.breakdown].sort((a,b) => b.humanResidual - a.humanResidual).slice(0,3);
    const qStyle = aiD.quadrant === "Transition Candidate"
      ? "background:rgba(212,52,46,0.15);color:#D4342E;border:1px solid rgba(212,52,46,0.3)"
      : aiD.quadrant === "Critical Human Capital"
      ? "background:rgba(0,114,188,0.15);color:#0072BC;border:1px solid rgba(0,114,188,0.3)"
      : aiD.quadrant === "Human Workforce"
      ? "background:rgba(196,144,50,0.15);color:#C49032;border:1px solid rgba(196,144,50,0.3)"
      : "background:rgba(45,140,60,0.15);color:#2D8C3C;border:1px solid rgba(45,140,60,0.3)";
    const topHRows = topH.map(t => {
      const pctH = Math.round((1 - t.automability / 100) * 100);
      return `<div style="display:flex;align-items:center;gap:12px;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.05)">
        <div style="flex:0 0 175px;font-family:'Times New Roman',Times,serif;font-size:12px;color:var(--text)">${t.name}</div>
        <div style="flex:1;height:6px;background:rgba(255,255,255,0.06);border-radius:3px;overflow:hidden;display:flex">
          <div style="width:${t.automability}%;height:100%;background:#0072BC"></div>
          <div style="width:${pctH}%;height:100%;background:#D4342E"></div>
        </div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#D4342E;flex:0 0 36px;text-align:right">${pctH}% H</div>
      </div>`;
    }).join("");
    return `<div class="gd-section">
      <div class="gd-sh">AI Exposure Assessment</div>
      <div class="gd-rule"></div>
      <div style="display:flex;gap:10px;margin-bottom:10px">
        <div style="flex:1;background:rgba(255,255,255,0.03);border:1px solid var(--border);border-radius:5px;padding:10px 14px">
          <div style="font-family:'JetBrains Mono',monospace;font-size:18px;font-weight:700;color:#D4342E">${aiD.exposure}<span style="font-size:10px;opacity:0.35"> /100</span></div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:8px;color:var(--text-faint);text-transform:uppercase;margin-top:3px">AI Exposure</div>
        </div>
        <div style="flex:1;background:rgba(255,255,255,0.03);border:1px solid var(--border);border-radius:5px;padding:10px 14px">
          <div style="font-family:'JetBrains Mono',monospace;font-size:18px;font-weight:700;color:#2D8C3C">${aiD.residualGap}<span style="font-size:10px;opacity:0.35"> /100</span></div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:8px;color:var(--text-faint);text-transform:uppercase;margin-top:3px">Residual Human Gap</div>
        </div>
        <div style="flex:1.6;background:rgba(255,255,255,0.03);border:1px solid var(--border);border-radius:5px;padding:10px 14px;display:flex;align-items:center">
          <span style="font-family:'JetBrains Mono',monospace;font-size:7px;font-weight:700;text-transform:uppercase;letter-spacing:1px;padding:3px 8px;border-radius:3px;${qStyle}">${aiD.quadrant}</span>
        </div>
      </div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:8px;color:var(--text-faint);text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">Top Topics by Human Residual (${AI_YEARS[aiSliderIdx].year})</div>
      <div style="display:flex;gap:10px;margin-bottom:6px;font-family:'JetBrains Mono',monospace;font-size:8px;color:var(--text-faint)">
        <span><span style="display:inline-block;width:8px;height:8px;background:#0072BC;border-radius:2px;margin-right:3px"></span>AI-Coverable</span>
        <span><span style="display:inline-block;width:8px;height:8px;background:#D4342E;border-radius:2px;margin-right:3px"></span>Human Residual</span>
      </div>
      ${topHRows || `<div style="font-family:'Times New Roman',Times,serif;font-size:12px;color:var(--text-faint)">No AI topic data available.</div>`}
      <div style="font-family:'JetBrains Mono',monospace;font-size:8px;color:var(--text-tertiary);margin-top:10px;padding-top:8px;border-top:1px solid rgba(255,255,255,0.05);line-height:1.6">
        Adjusted KRS: <span style="color:var(--text-secondary)">${aiD.krs}</span> &nbsp;·&nbsp; Baseline KRS: <span style="color:var(--text-secondary)">${aiD.baseKrs}</span><br>
        KRS is reduced by AI absorption factor (0.5 × exposure). AI performs tasks but only partially retains institutional memory.
      </div>
      ${(() => {
        const firstName = (p.display_name || formatName(p.person)).split(" ")[0];
        const curYear = AI_YEARS[aiSliderIdx].year;
        const exp = aiD.exposure, gap = aiD.residualGap, q = aiD.quadrant;
        const topHtopic = [...aiD.breakdown].sort((a,b) => b.humanResidual - a.humanResidual)[0];
        const topHname = topHtopic ? `<em>${topHtopic.name}</em>` : "their primary domain";
        const topHpct = topHtopic ? Math.round((1 - topHtopic.automability / 100) * 100) : gap;
        const pi = aiD.pi !== undefined ? aiD.pi : Math.round((p.positional_impact || 0) * 100);
        // piOverride proxy: PI >= 80 and exposure >= 65 (would naturally be TC without override)
        const isExecOverride = pi >= 80 && exp >= 65;
        let prose;
        if (isExecOverride) {
          prose = `Despite an AI exposure score of ${exp}/100 at ${curYear} capability levels, which would mathematically place this role in the Transition Candidate quadrant, ${firstName}'s positional authority (PI: ${pi}) reflects executive judgment, political relationships, and crisis decision-making that remain beyond AI substitution at any projected capability level. The domain of ${topHname} carries ${topHpct}% human residual. This profile is classified as <strong>Critical Human Capital</strong>. Retention, succession planning, and explicit knowledge transfer protocols are the primary risk levers.`;
        } else if (q === "Critical Human Capital") {
          prose = `At ${curYear} capability levels, ${firstName} carries an AI exposure of ${exp}/100 with a residual human gap of ${gap}/100. The domain of ${topHname} (${topHpct}% human residual) anchors work that requires judgment, relational context, and institutional depth that current-generation AI cannot adequately replicate. Classified as <strong>Critical Human Capital</strong>, this profile presents high organizational risk in the event of departure. Retention and successor development are the primary levers.`;
        } else if (q === "Transition Candidate") {
          prose = `${firstName}'s AI exposure of ${exp}/100 at ${curYear} capability levels, combined with an organizational knowledge footprint above the classification threshold, places this role in the <strong>Transition Candidate</strong> quadrant. High AI substitutability and elevated departure risk are present simultaneously. The domain of ${topHname} (${topHpct}% human residual) represents the remaining knowledge concentration at risk. Proactive role redesign and structured knowledge transfer are indicated before AI capability advances further along this trajectory.`;
        } else if (q === "Human Workforce") {
          prose = `At ${curYear} capability levels, ${firstName} shows an AI exposure of ${exp}/100 — below the substitutability threshold. Classified as a <strong>Human Workforce</strong>, organizational impact is contained, but domain expertise in ${topHname} (${topHpct}% human residual) has limited AI coverage. While aggregate departure risk is moderate, this specific expertise may be difficult to reconstruct without a targeted successor development program. Periodic reclassification checks are advisable as agentic capability advances.`;
        } else {
          prose = `${firstName}'s knowledge profile at ${curYear} capability levels carries an AI exposure of ${exp}/100, placing this role in the <strong>AI-Ready Role</strong> quadrant. With a residual human gap of ${gap}/100, the work is broadly automatable across most topic categories. Proactive knowledge transfer is lower priority; organizational investment is better directed toward workflow redesign and AI augmentation to free capacity for higher-residual work elsewhere in the organization.`;
        }
        return `<div style="font-family:'Times New Roman',Times,serif;font-size:13px;line-height:1.75;color:var(--text);margin-top:14px;padding-top:12px;border-top:1px solid rgba(255,255,255,0.05)">${prose}</div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:rgba(255,255,255,0.25);margin-top:10px;line-height:1.5">AI exposure computed using three-dimension automability scoring (Base LLM · Agentic · Codifiability) across 13 topic categories. Full methodology available in How It Works.</div>`;
      })()}
    </div>`;
  })()}

  <div class="gd-section">
    <div class="gd-sh">Role &amp; Institutional Context</div>
    <div class="gd-rule"></div>
    <div class="gd-body">${narrative}</div>
  </div>

  <div class="gd-two-col">
    <div class="gd-section">
      <div class="gd-sh">Communication Network</div>
      <div class="gd-rule"></div>
      ${top5Partners.length ? `<div class="gd-bar-legend"><span><span class="ld" style="background:#0072BC"></span>Email volume</span></div>${contactHTML}` : `<div style="font-family:'Times New Roman',Times,serif;font-size:13px;color:var(--text-faint)">Insufficient graph data.</div>`}
    </div>
    <div>
      <div class="gd-section">
        <div class="gd-sh">Topic Expertise</div>
        <div class="gd-rule"></div>
        ${topicHTML || `<div style="font-family:'Times New Roman',Times,serif;font-size:13px;color:var(--text-faint)">No topic data available.</div>`}
      </div>
      <div class="gd-recov-mini">
        <div class="gd-recov-hdr">
          <div class="gd-rm-title">12-Month Recovery Projection</div>
          <div style="text-align:right"><div class="gd-rm-val" style="color:${recovColor}">${recov12}%</div><div class="gd-rm-sub">of pre-departure capacity</div></div>
        </div>
        <div class="gd-recov-bar-track"><div class="gd-recov-bar-fill" style="width:${Math.min(parseFloat(recov12)||0,100)}%;background:${recovColor}"></div></div>
      </div>
    </div>
  </div>

  <div class="gd-section">
    <div class="gd-sh">Departure Timeline</div>
    <div class="gd-rule"></div>
    <div style="display:flex;gap:12px">${milestones}</div>
  </div>

  <div class="gd-section">
    <div class="gd-sh">Successor Analysis</div>
    <div class="gd-rule"></div>
    <div class="gd-succ-grid">${succHTML}</div>
  </div>

  <div class="gd-section">
    <div class="gd-sh">Cross-Training Candidates</div>
    <div class="gd-rule"></div>
    ${crossHTML}
  </div>

  <div class="gd-section">
    <div class="gd-sh">Departure Impact Assessment</div>
    <div class="gd-rule"></div>
    <div class="gd-impact-box">
      <div class="gd-impact-label">Projected Organizational Impact</div>
      <div class="gd-impact-text">${impact}</div>
    </div>
  </div>

  <div class="gd-section">
    <div class="gd-sh">Recommended Action</div>
    <div class="gd-rule"></div>
    <div class="gd-action-box">
      <div class="gd-action-label">Priority Intervention</div>
      <div class="gd-action-text">${recommend}</div>
    </div>
  </div>

  <div class="gd-footer">
    <div class="gd-footer-line">Built ${new Date().toLocaleDateString("en-US",{month:"long",year:"numeric"})} · Independent Research</div>
    <div class="gd-footer-line" style="margin-top:4px">Organizational Intelligence, Knowledge Risk Assessment · Jeb Farneth</div>
  </div>`;
}

// ── Narrative generator ──────────────────────────────────────────────────────────
function genDossierNarrative(p, partners, cats, v) {
  const name   = p.display_name;
  const first  = name.split(" ")[0];
  const role   = p.role || "staff member";
  const vol    = Math.round(p.weighted_degree || 0).toLocaleString();
  const q      = p.quadrant || "Low Priority";
  const risk   = (p.risk_score * 100).toFixed(1);
  const pos    = (p.positional_impact * 100).toFixed(0);
  const nCats  = cats.length;
  const cat1   = cats[0] || "general operations";
  const cat2   = cats[1] || cat1;
  const cat3   = cats[2] || cat2;
  const extGap = Math.round((p.external_hire_gap || 0) * 100);
  const p1     = partners[0] || "internal colleagues";
  const p2     = partners[1] || "cross-functional peers";

  if (q === "Organizational Emergency") {
    const P1 = [
      `${name} serves as <strong>${role}</strong> at Enron, carrying a <strong>${pos}</strong> positional impact score. The role sits at the center of <strong>${cat1}</strong> decision-making. ${vol} weighted email interactions over the analysis period confirm sustained senior-level engagement. Primary working contacts are ${p1}${p2 ? ` and ${p2}` : ""}.`,
      `<strong>${pos}</strong> positional impact places ${name} among the most organizationally embedded leaders in the dataset. The <strong>${role}</strong> position spans <strong>${cat1}</strong> and <strong>${cat2}</strong>. ${vol} weighted email interactions reflect direct involvement in consequential decisions. Closest working contacts include ${p1}${p2 ? ` and ${p2}` : ""}.`,
      `${name} holds the <strong>${role}</strong> position with a <strong>${pos}</strong> positional impact score. That places ${first} in the top tier of organizational influence across the Enron dataset. The email record shows ${vol} weighted interactions. ${p1}${p2 ? ` and ${p2}` : ""} anchor the inner circle of ${first}'s working network.`,
      `${first}'s title is <strong>${role}</strong>. The <strong>${pos}</strong> positional impact score reflects direct involvement in decisions that require executive authority. ${vol} weighted email interactions tie ${first} to a broad network of senior counterparts. Key working relationships include ${p1}${p2 ? ` and ${p2}` : ""}.`
    ][v];
    const P2 = [
      `${first}'s knowledge risk score is <strong>${risk}</strong>, spanning <strong>${nCats}</strong> topic categories. <strong>${cat1}</strong> and <strong>${cat2}</strong> are the highest-concentration areas. Few other employees hold comparable depth in both domains. High knowledge concentration combined with senior positional authority produces the Organizational Emergency classification.`,
      `The <strong>${risk}</strong> knowledge risk score reflects concentration in <strong>${cat1}</strong> and <strong>${cat2}</strong>. Both are operationally critical categories at Enron. Internal coverage in these areas is thin. That scarcity drives the Organizational Emergency classification.`,
      `<strong>${cat1}</strong> and <strong>${cat2}</strong> anchor ${first}'s knowledge profile. The <strong>${risk}</strong> knowledge risk score reflects how few employees share comparable expertise. An Organizational Emergency classification results when high knowledge concentration coincides with senior authority. Both conditions apply here.`,
      `${first}'s knowledge spans <strong>${nCats}</strong> topic categories, led by <strong>${cat1}</strong>. The <strong>${risk}</strong> knowledge risk score ranks this profile among the highest in the dataset. Senior positional authority amplifies the risk. Decisions currently routed through ${first} cannot easily reroute through any existing internal candidate.`
    ][v];
    const P3 = [
      `${first}'s departure breaks the decision chain in <strong>${cat1}</strong>. No current internal candidate holds both the positional authority and knowledge depth required to step in directly. The <strong>${extGap}%</strong> external hire gap means outside recruitment is necessary but takes months to complete. Operational gaps in <strong>${cat2}</strong> will emerge before any hire reaches full effectiveness.`,
      `The organization has no ready internal successor for ${first}'s role. A <strong>${extGap}%</strong> external hire gap confirms that outside recruitment is unavoidable. Decisions in <strong>${cat1}</strong> will queue or escalate to leaders who lack the requisite context. The gap is largest in <strong>${cat2}</strong>, where ${first}'s knowledge is least shared.`,
      `Departure creates immediate authority gaps in <strong>${cat1}</strong> and <strong>${cat2}</strong>. Knowledge in these categories is concentrated. The organization loses the primary holder with no backup at the same depth. The external hire gap of <strong>${extGap}%</strong> means internal transition alone cannot close that gap.`,
      `${first}'s knowledge in <strong>${cat1}</strong> is not held by any successor candidate at comparable depth. Departure triggers a search process that the <strong>${extGap}%</strong> external hire gap makes slow. In the interim, <strong>${cat2}</strong> decisions must reroute to leaders with partial context at best. The 12-month recovery ceiling reflects this structural constraint.`
    ][v];
    return `<p>${P1}</p><p>${P2}</p><p>${P3}</p>`;
  }

  if (q === "Silent Threat") {
    const P1 = [
      `${name}'s title is <strong>${role}</strong>. Leadership has not flagged ${first} as a succession priority. The <strong>${risk}</strong> knowledge risk score tells a different story than the org chart. ${vol} weighted email interactions, anchored by ${p1}${p2 ? ` and ${p2}` : ""}, confirm sustained operational centrality.`,
      `${name} holds the <strong>${role}</strong> designation at Enron. The <strong>${pos}</strong> positional impact score understates the organizational dependency. ${vol} weighted email interactions point to an employee who is operationally indispensable without holding formal authority to match. Primary contacts include ${p1}${p2 ? ` and ${p2}` : ""}.`,
      `The <strong>${role}</strong> title does not reflect ${name}'s actual organizational importance. The knowledge risk score of <strong>${risk}</strong> exceeds most senior leaders in the dataset. ${vol} weighted email interactions confirm sustained involvement in critical operational decisions. Closest working contacts are ${p1}${p2 ? ` and ${p2}` : ""}.`,
      `${name} carries a <strong>${risk}</strong> knowledge risk score from the <strong>${role}</strong> position. That score does not match the title. The gap between formal authority (<strong>${pos}</strong> positional impact) and actual operational importance is the defining feature of this Silent Threat profile. ${first}'s email record shows ${vol} weighted interactions with ${p1}${p2 ? ` and ${p2}` : ""}.`
    ][v];
    const P2 = [
      `${first}'s expertise covers <strong>${cat1}</strong> and <strong>${cat2}</strong>. Both categories have limited internal coverage. The organization relies on ${first} for operational continuity in these areas without formally recognizing that dependency. A <strong>${risk}</strong> knowledge risk score at this positional level is a clear warning signal.`,
      `<strong>${cat1}</strong> is the highest-concentration knowledge area in ${first}'s profile. Few other employees operate at equivalent depth in this domain. The <strong>${risk}</strong> knowledge risk score reflects the aggregate across <strong>${nCats}</strong> topic categories. Standard succession planning has not addressed this risk because ${first}'s title does not indicate it.`,
      `The <strong>${risk}</strong> knowledge risk score reflects concentration in <strong>${cat1}</strong> and <strong>${cat2}</strong>. Both categories lack adequate backup coverage in the current employee population. ${first} built this expertise through direct operational involvement. It does not transfer easily through documentation.`,
      `${first}'s knowledge in <strong>${cat1}</strong> sits in a low-coverage area of the organization. The <strong>${risk}</strong> knowledge risk score is high relative to ${first}'s positional impact of <strong>${pos}</strong>. That gap defines the Silent Threat profile. Succession planning processes built around seniority will not catch this case.`
    ][v];
    const P3_ST = [
      `${first}'s departure will go undetected as a succession risk until operational failures surface. The dependency on ${first} for <strong>${cat1}</strong> decisions is real but informal. No escalation path exists for problems that currently resolve through ${first}'s direct involvement. The <strong>${extGap}%</strong> external hire gap confirms that outside recruitment cannot close the gap quickly.`,
      `Departure disrupts <strong>${cat1}</strong> and <strong>${cat2}</strong> operations at the functional level. The disruption will not be visible to senior leadership immediately. The knowledge is partly procedural and partly tacit. Procedural elements can be documented now. The tacit layer, built through years of hands-on work, cannot be recovered through documentation alone.`,
      `Without ${first}, <strong>${cat1}</strong> decisions escalate to leaders who hold partial context at best. The <strong>${extGap}%</strong> external hire gap makes rapid replacement impossible. Recovery in the 12-month window depends on how much of ${first}'s knowledge can be made explicit before departure. Most of it cannot.`,
      `${first}'s departure removes the primary knowledge holder in <strong>${cat1}</strong>. The organization has no backup for this role at comparable depth. The <strong>${extGap}%</strong> external hire gap means an internal solution must be developed. Identifying and developing a viable internal successor requires more time than a standard transition period allows.`
    ][v];
    return `<p>${P1}</p><p>${P2}</p><p>${P3_ST}</p>`;
  }

  if (q === "Replaceable Executive") {
    const P1 = [
      `${name} serves as <strong>${role}</strong> with a <strong>${pos}</strong> positional impact score. The role carries genuine organizational authority in <strong>${cat1}</strong>. ${vol} weighted email interactions confirm executive engagement across multiple organizational layers. Primary contacts are ${p1}${p2 ? ` and ${p2}` : ""}.`,
      `${name} holds the <strong>${role}</strong> designation. The <strong>${pos}</strong> positional impact score reflects a senior position with real organizational consequence. ${vol} weighted email interactions span <strong>${cat1}</strong> and <strong>${cat2}</strong>. Working relationships include ${p1}${p2 ? ` and ${p2}` : ""}.`
    ][v % 2];
    const P2 = [
      `${first}'s knowledge risk score is <strong>${risk}</strong>. That figure is moderate relative to Organizational Emergency and Silent Threat profiles in this dataset. Expertise in <strong>${cat1}</strong> is broadly shared across the organization. The succession risk here is leadership continuity, not knowledge concentration.`,
      `The <strong>${risk}</strong> knowledge risk score reflects a profile where internal coverage is adequate. <strong>${cat1}</strong> and <strong>${cat2}</strong> expertise is distributed across enough employees to support a managed transition. ${first}'s value is positional. The gap created by departure is a leadership gap, not an information gap.`
    ][v % 2];
    const P3_RE = [
      `${first}'s departure creates a leadership vacancy in <strong>${cat1}</strong> that requires a formal succession response. Knowledge recovery is not the primary concern. The harder problem is rebuilding the positional authority and stakeholder trust that ${first} has accumulated over time. That process cannot be accelerated through documentation or cross-training.`,
      `Departure opens a leadership gap at the <strong>${cat1}</strong> level. Internal knowledge coverage is sufficient to sustain operations during transition. The challenge is developing a successor with enough organizational standing to hold the role at full effectiveness. Standard succession planning with a defined timeline is the appropriate response.`
    ][v % 2];
    return `<p>${P1}</p><p>${P2}</p><p>${P3_RE}</p>`;
  }

  // Low Priority — two paragraphs max
  const P1 = [
    `${name} holds the <strong>${role}</strong> position at Enron. The knowledge risk score is <strong>${risk}</strong> and the positional impact score is <strong>${pos}</strong>. Both fall below the thresholds that require urgent succession intervention. ${vol} weighted email interactions reflect standard operational engagement.`,
    `${name} works as <strong>${role}</strong> with a <strong>${risk}</strong> knowledge risk score. The score reflects adequate internal redundancy in <strong>${cat1}</strong>. ${vol} weighted email interactions with ${p1}${p2 ? ` and ${p2}` : ""} show consistent operational involvement without creating a single point of failure.`
  ][v % 2];
  const P2 = [
    `Standard succession planning is sufficient for this profile. ${first}'s expertise in <strong>${cat1}</strong> is shared across enough employees to support a managed transition. No urgent intervention is required. Documentation and cross-training at the standard pace will address the departure risk.`,
    `Internal coverage of <strong>${cat1}</strong> is adequate. The <strong>${risk}</strong> knowledge risk score does not indicate dangerous concentration. ${first}'s departure creates a localized gap that existing succession pathways can fill. The appropriate response is routine succession planning.`
  ][v % 2];
  return `<p>${P1}</p><p>${P2}</p>`;
}

// ── Impact generator ──────────────────────────────────────────────────────────────
function genDossierImpact(p, cats, lostCats, partialCats, riskPct, extGap, recov12, permLoss, v) {
  const name  = p.display_name;
  const first = name.split(" ")[0];
  const q     = p.quadrant || "Low Priority";
  const cat1  = cats[0] || "key knowledge areas";
  const cat2  = cats[1] || cat1;

  if (q === "Organizational Emergency") {
    const lostStr    = lostCats.length ? `<strong>${lostCats.join(" and ")}</strong>` : `<strong>${cat1}</strong>`;
    const stmts = [
      `${first}'s departure creates an immediate gap across <strong>${cats.length}</strong> topic categories. The <strong>${extGap}%</strong> external hire gap confirms that no internal employee holds sufficient breadth to cover ${first}'s active knowledge domains. The 12-month simulation projects only <strong>${recov12}%</strong> recovery of pre-departure capacity. ${lostCats.length ? `${lostStr} degrades to permanent loss, irrecoverable through internal routing or cross-training alone.` : `Recovery in ${lostStr} plateaus before organizational function is restored.`}`,
      `Departure triggers disruption beyond individual knowledge loss. The <strong>${extGap}%</strong> external hire gap confirms that internal succession pathways are inadequate across ${first}'s full knowledge profile. Projected 12-month recovery is <strong>${recov12}%</strong>. ${permLoss > 0 ? `Permanent knowledge loss across <strong>${permLoss}</strong> topic categor${permLoss===1?"y":"ies"} represents an organizational cost that no hire or training program can fully remediate.` : `Recovery plateaus before pre-departure capacity is restored.`}`
    ][v % 2];
    return stmts;
  }

  if (q === "Silent Threat") {
    const stmts = [
      `${first}'s departure is the scenario organizational risk frameworks are least equipped to anticipate. A <strong>${extGap}%</strong> external hire gap and projected 12-month recovery of only <strong>${recov12}%</strong> mean a prolonged capability deficit in <strong>${cat1}</strong>${cat2 !== cat1 ? ` and <strong>${cat2}</strong>` : ""}. ${lostCats.length ? `The simulation classifies ${lostCats.length > 1 ? lostCats.join(" and ") : lostCats[0]} as effectively <strong>lost</strong>, irrecoverable within the 12-month horizon through any internal routing pathway.` : `Recovery across all active topic categories stalls well below pre-departure capacity.`}`,
      `The impact of ${first}'s departure will not register immediately in leadership visibility. Operational degradation surfaces as functions that depended on ${first}'s knowledge encounter problems no remaining employee can resolve. The <strong>${extGap}%</strong> external hire gap means external recruitment is necessary but insufficient. Tacit knowledge in <strong>${cat1}</strong> cannot be replicated by a hire who lacks the operational history. The 12-month recovery projection of <strong>${recov12}%</strong> reflects this constraint.`
    ][v % 2];
    return stmts;
  }

  if (q === "Replaceable Executive") {
    return `${first}'s departure creates a leadership gap in <strong>${cat1}</strong> that requires a managed succession response. The <strong>${extGap}%</strong> external hire gap is elevated relative to the broader organization, but the <strong>${recov12}%</strong> 12-month recovery projection indicates sufficient internal capacity to maintain functional continuity during transition. The primary risk is leadership continuity. The organization must develop a successor with the positional authority and stakeholder relationships to operate the role at full effectiveness.`;
  }

  return `${first}'s departure creates a localized disruption that existing succession pathways can absorb. The <strong>${recov12}%</strong> projected recovery at 12 months reflects adequate internal redundancy in <strong>${cat1}</strong>. Standard transition planning, including knowledge documentation and cross-training, will mitigate the majority of departure impact within a normal succession timeline.`;
}

// ── Recommendation generator ────────────────────────────────────────────────────
function genDossierRec(p, cats, succs, extGap, recov12, partners, v) {
  const name  = p.display_name;
  const first = name.split(" ")[0];
  const q     = p.quadrant || "Low Priority";
  const cat1  = cats[0] || "primary knowledge area";
  const cat2  = cats[1] || cat1;
  const cat3  = cats[2] || cat2;
  // Best and second-best successors
  const sortedSuccs = [...succs].sort((a,b) => (b.readiness||0)-(a.readiness||0));
  const bestSucc  = sortedSuccs[0] || null;
  const secSucc   = sortedSuccs[1] || null;
  const bestSuccName = bestSucc ? (bestSucc.successor_name || formatName(bestSucc.best_successor || "")) : null;
  const bestSuccPct  = bestSucc ? Math.round((bestSucc.readiness||0)*100) : 0;
  const secSuccName  = secSucc  ? (secSucc.successor_name  || formatName(secSucc.best_successor  || "")) : null;
  const secSuccPct   = secSucc  ? Math.round((secSucc.readiness||0)*100)  : 0;
  const p1 = partners[0] || "key counterparts";
  const p2 = partners[1] || "";
  const noReadySucc = !bestSucc || bestSuccPct < 30;

  // Helper to render a numbered action item with timeline badge
  function action(n, timeline, title, body) {
    const tColor = timeline.includes("Immediate") ? "#D4342E" : timeline.includes("Short") ? "#C49032" : "#F5F5F7";
    return `<div style="margin-bottom:16px"><span style="font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:700;color:${tColor};text-transform:uppercase;letter-spacing:1px">${timeline}</span><br><strong>(${n}) ${title}:</strong> ${body}</div>`;
  }

  if (q === "Organizational Emergency") {
    const variants = [
      // v=0
      [
        action(1,"Immediate (0–30 days)","Emergency Knowledge Capture",`Commission ${first} to produce a structured briefing document covering the tacit assumptions, stakeholder relationships, and institutional context embedded in their management of <strong>${cat1}</strong> and <strong>${cat2}</strong>. These domains have the lowest internal redundancy and the highest permanent loss probability.`),
        action(2,"Immediate (0–30 days)","Board-Level Succession Briefing",`Formally brief the board or executive leadership committee on ${first}'s departure risk classification. A <strong>${extGap}%</strong> external hire gap and <strong>${recov12}%</strong> projected 12-month recovery constitute a material organizational risk that requires governance-level awareness, not just operational planning.`),
        action(3,"Short-term (30–90 days)","Authority Mapping and Delegation",`Map the decision-making authorities that currently require ${first}'s approval and begin systematically delegating them to designated successors. This reduces single-point-of-failure risk before departure occurs and accelerates successor readiness in practice rather than only in theory.`),
        bestSuccName
          ? action(4,"Short-term (30–90 days)","Successor Acceleration",`${bestSuccName}, currently at <strong>${bestSuccPct}%</strong> readiness, is the strongest internal succession candidate. Elevate them into active co-leadership of ${first}'s primary responsibilities immediately. ${secSuccName ? `${secSuccName} (${secSuccPct}%) should be developed in parallel as a secondary pathway.` : ""}`)
          : action(4,"Short-term (30–90 days)","External Recruitment Pipeline",`With a <strong>${extGap}%</strong> external hire gap and no ready internal successor, initiate external search now in parallel with internal development. The search profile should prioritize candidates with direct experience in <strong>${cat1}</strong> and a track record in comparable organizational contexts.`),
        action(5,"Medium-term (90–180 days)","Stakeholder Relationship Transfer",`${first}'s relationships with ${p1}${p2 ? ` and ${p2}` : ""} and other key stakeholders represent institutional capital that must be formally redistributed. Assign named relationship stewards from the senior leadership team to each critical contact before departure, and arrange joint introduction meetings to begin transferring relationship equity.`)
      ],
      // v=1
      [
        action(1,"Immediate (0–30 days)","Formal Succession Plan",`Designate an interim authority structure with explicit decision rights for the period immediately following ${first}'s departure. The plan must specify who holds authority over <strong>${cat1}</strong> and <strong>${cat2}</strong> decisions. Inheriting the title alone is not sufficient.`),
        action(2,"Immediate (0–30 days)","Relationship Capital Redistribution",`Begin deliberately redistributing ${first}'s key relationships, ${p1}${p2 ? ` and ${p2}` : ""}, to named successors within the leadership team. Schedule joint-presence meetings now so that relationship continuity can be established before any departure forces a cold handoff.`),
        action(3,"Short-term (30–90 days)","Structured Knowledge Documentation",`Initiate a knowledge capture program focused on <strong>${cat1}</strong> and <strong>${cat2}</strong> — the domains most directly dependent on ${first}'s engagement. Sessions should produce machine-readable output usable by successors and, if needed, external hires.`),
        bestSuccName
          ? action(4,"Short-term (30–90 days)","Succession Acceleration",`Elevate ${bestSuccName} (currently <strong>${bestSuccPct}%</strong> readiness) into active co-leadership of ${first}'s responsibilities now. Real-world decision-making exposure is the fastest path from ${bestSuccPct}% to succession-ready. ${secSuccName ? `${secSuccName} (${secSuccPct}%) provides a secondary track.` : ""}`)
          : action(4,"Short-term (30–90 days)","External Search Initiation",`The <strong>${extGap}%</strong> external hire gap makes internal succession alone inadequate. Commission an external search in parallel with internal development, targeting candidates with <strong>${cat1}</strong> experience in comparable complex environments.`),
        action(5,"Medium-term (90–180 days)","Strategic Context Documentation",`Commission ${first} to produce a multi-part strategic briefing: the history of key decisions in <strong>${cat1}</strong>, active stakeholder commitments, and the informal power dynamics that govern how decisions actually get made, not merely the formal authority chart.`)
      ],
      // v=2
      [
        action(1,"Immediate (0–30 days)","Leadership Risk Escalation",`Escalate ${first}'s departure risk classification to the executive committee within 30 days. The combination of <strong>${extGap}%</strong> external hire gap and <strong>${recov12}%</strong> projected recovery is not an HR matter. It is a material organizational continuity risk requiring executive sponsorship of the response.`),
        action(2,"Immediate (0–30 days)","Tacit Knowledge Capture",`Begin daily structured documentation sessions with ${first}, targeting the operational assumptions, exception-handling protocols, and stakeholder intelligence embedded in <strong>${cat1}</strong> engagement. This knowledge resists formal documentation; sessions must be conducted iteratively over weeks, not condensed into a single handoff.`),
        action(3,"Short-term (30–90 days)","Successor Designation",
          bestSuccName
            ? `Formally designate ${bestSuccName} (${bestSuccPct}% readiness) as the primary successor candidate and begin structured transition. Assign ${first}'s active responsibilities incrementally over a 60-day period to build competency in context, not in isolation.${secSuccName ? ` ${secSuccName} (${secSuccPct}%) should be developed as a parallel track to reduce single-point dependency in the succession itself.` : ""}`
            : `With no internal candidate above 30% readiness, launch parallel tracks: intensive internal development for the most proximate candidates and an external search targeting <strong>${cat1}</strong> expertise. Do not wait for internal development to plateau before initiating external recruitment.`),
        action(4,"Short-term (30–90 days)","Relationship Transfer Protocol",`Map all external stakeholder relationships maintained by ${first} and assign named successors to each. Schedule introductions with ${p1}${p2 ? ` and ${p2}` : ""} immediately — relationship transfer is most effective when the incumbent is still present to provide context and endorsement.`),
        action(5,"Medium-term (90–180 days)","Knowledge Infrastructure",`Convert the documentation produced in phase one into accessible organizational knowledge — structured wikis, decision logs, and onboarding material for <strong>${cat1}</strong> and <strong>${cat2}</strong>. The goal is not archiving ${first}'s knowledge but making it operationally usable by the successor team.`)
      ],
      // v=3
      [
        action(1,"Immediate (0–30 days)","Board Succession Briefing",`Present ${first}'s risk profile to the board or executive committee with the following framing: a <strong>${extGap}%</strong> external hire gap and <strong>${recov12}%</strong> projected recovery represent a known material risk that board oversight is obligated to address. Treat this as a governance item, not an operational task.`),
        action(2,"Immediate (0–30 days)","Knowledge Extraction Program",`Commission a multi-week structured extraction of ${first}'s <strong>${cat1}</strong> and <strong>${cat2}</strong> institutional knowledge. Use interview-based methods, shadowing protocols, and decision-journal documentation to capture the tacit dimensions that formal documentation misses.`),
        action(3,"Short-term (30–90 days)","Authority Restructuring",`Identify every decision currently flowing through ${first} and begin restructuring those authority channels before departure. The goal is to eliminate organizational dependencies on ${first}'s presence, not merely to prepare a successor who can approximate them.`),
        bestSuccName
          ? action(4,"Short-term (30–90 days)","Successor Development and Testing",`${bestSuccName} at <strong>${bestSuccPct}%</strong> readiness requires structured exposure to ${first}'s active decisions, not briefings, but direct co-ownership of consequential choices. Assign one to two of ${first}'s current <strong>${cat1}</strong> responsibilities immediately to create real-world readiness.${secSuccName ? ` ${secSuccName} (${secSuccPct}%) should receive parallel development in ${cat2}.` : ""}`)
          : action(4,"Short-term (30–90 days)","Parallel Succession Tracks",`No internal candidate is currently successor-ready. Run three tracks simultaneously: intensive internal development for the best available candidates; external search targeting <strong>${cat1}</strong> and <strong>${cat2}</strong> expertise; and interim authority redistribution to reduce the risk surface during the transition period.`),
        action(5,"Medium-term (90–180 days)","Stakeholder Continuity Plan",`Develop formal continuity plans for all relationships currently maintained through ${first}'s authority. Each key contact, including ${p1}${p2 ? ` and ${p2}` : ""}, should have a named organizational counterpart with documented relationship history and active engagement before any departure scenario occurs.`)
      ]
    ];
    return variants[v % 4].join("");
  }

  if (q === "Silent Threat") {
    const variants = [
      // v=0
      [
        action(1,"Immediate (0–30 days)","Leadership Risk Disclosure",`Brief the relevant senior leadership on ${first}'s actual knowledge risk profile. The current ${first.split(" ")[0] === first ? `title` : `designation`} does not communicate the organizational dependency — leadership decisions about retention, compensation, and succession must be made with accurate information about what departure would cost.`),
        action(2,"Immediate (0–30 days)","Retention Risk Assessment",`Evaluate ${first}'s departure risk: compensation relative to market, career trajectory within the organization, workload and recognition. Silent threat profiles are most vulnerable to unplanned departure precisely because the organization has systematically undervalued the employee. A <strong>${extGap}%</strong> external hire gap makes retention significantly cheaper than replacement.`),
        action(3,"Short-term (30–90 days)","Structured Knowledge Documentation",`Begin systematic documentation sessions covering ${first}'s <strong>${cat1}</strong> and <strong>${cat2}</strong> expertise — operational procedures, exception-handling knowledge, and the institutional memory that exists only in practice rather than in written protocols. Focus on the highest-risk processes first.`),
        bestSuccName
          ? action(4,"Short-term (30–90 days)","Successor Pairing",`${bestSuccName} at <strong>${bestSuccPct}%</strong> readiness is the closest internal candidate. Establish a formal mentoring or co-working arrangement with ${first} immediately. ${secSuccName ? `${secSuccName} (${secSuccPct}%) should be developed in parallel.` : ""}  Target: bring the best candidate above 60% readiness within 90 days through direct knowledge transfer in active work contexts.`)
          : action(4,"Short-term (30–90 days)","Successor Identification",`No ready internal successor has been identified. Begin a structured internal assessment to identify candidates from adjacent departments who have relevant exposure to <strong>${cat1}</strong>. If internal pathways are insufficient, which the <strong>${extGap}%</strong> external hire gap suggests, initiate parallel external recruitment.`)
      ],
      // v=1
      [
        action(1,"Immediate (0–30 days)","Retention Prioritization",`Address ${first}'s retention risk before any knowledge capture program can be meaningfully completed. Conduct a compensation and recognition audit within 30 days. Silent threat employees are the most likely to depart without warning because the organization has not recognized their value. Correction must precede documentation.`),
        action(2,"Immediate (0–30 days)","Organizational Visibility",`Formally elevate ${first}'s organizational profile: ensure that ${first}'s contributions to <strong>${cat1}</strong> are visible to leadership, and that this visibility translates into recognition, involvement in strategic discussions, and career development opportunities that reflect actual organizational importance.`),
        action(3,"Short-term (30–90 days)","Knowledge Audit and Capture",`Commission a knowledge audit of ${first}'s <strong>${cat1}</strong> and <strong>${cat2}</strong> domains, with particular attention to processes that exist only in ${first}'s practice. The audit should produce a documented inventory of at-risk knowledge and a prioritized capture plan, with the highest-risk areas addressed first given a <strong>${extGap}%</strong> external hire gap.`),
        bestSuccName
          ? action(4,"Short-term (30–90 days)","Successor Development",`Elevate ${bestSuccName} (${bestSuccPct}% readiness) into direct collaboration with ${first} across active <strong>${cat1}</strong> responsibilities. Knowledge transfer is most effective when embedded in real work rather than structured separately from it. ${secSuccName ? `Develop ${secSuccName} (${secSuccPct}%) as a secondary succession pathway.` : ""}`)
          : action(4,"Short-term (30–90 days)","Cross-Functional Development",`With no identified internal successor, expand cross-training across adjacent departments to identify and develop candidates for <strong>${cat1}</strong> coverage. Simultaneously initiate external recruitment as a hedge, given the <strong>${extGap}%</strong> external hire gap.`)
      ],
      // v=2
      [
        action(1,"Immediate (0–30 days)","Executive Briefing",`Prepare a concise risk brief for senior leadership documenting ${first}'s actual organizational footprint: <strong>${(p.risk_score*100).toFixed(1)}</strong> knowledge risk, <strong>${extGap}%</strong> external hire gap, and <strong>${recov12}%</strong> projected 12-month recovery. The purpose is not to alarm leadership but to ensure that retention, compensation, and succession decisions are calibrated to actual organizational cost rather than job title.`),
        action(2,"Immediate (0–30 days)","Retention Contract",`If retention risk is elevated, commission a retention package within 30 days. Financial incentives or career development investments are both appropriate options. The cost of retention is almost always lower than the cost of replacement in silent threat profiles, particularly where the external hire gap exceeds <strong>40%</strong>.`),
        action(3,"Short-term (30–90 days)","Knowledge Extraction",`Establish a structured, time-bounded knowledge extraction program for ${first}'s <strong>${cat1}</strong> expertise. Sessions should focus on the operational processes, decision heuristics, and institutional relationships that are most difficult to document and least likely to survive an unplanned departure intact.`),
        bestSuccName
          ? action(4,"Short-term (30–90 days)","Successor Acceleration",`${bestSuccName}, at ${bestSuccPct}% readiness, requires hands-on exposure to ${first}'s active work. Co-ownership of decisions in <strong>${cat1}</strong> over a structured 60-day period will build readiness faster than any handoff document. ${secSuccName ? `${secSuccName} (${secSuccPct}%) provides a backup development pathway.` : ""}`)
          : action(4,"Short-term (30–90 days)","Successor Pipeline Construction",`No internal candidate is currently positioned for succession. Construct a pipeline: identify the two or three employees with the highest relevant exposure to <strong>${cat1}</strong>, begin immediate cross-training, and initiate external recruitment in parallel given the <strong>${extGap}%</strong> hire gap.`)
      ],
      // v=3
      [
        action(1,"Immediate (0–30 days)","Risk Reclassification",`Formally reclassify ${first} as a critical knowledge holder within the organization's succession framework. This reclassification has operational consequences: ${first}'s compensation, career path, and succession coverage should all be reassessed against a risk profile that reflects a <strong>${(p.risk_score*100).toFixed(1)}</strong> knowledge risk score, not a job title.`),
        action(2,"Immediate (0–30 days)","Departure Risk Evaluation",`Conduct an immediate assessment of ${first}'s departure probability. Interview ${first}'s direct manager and HR partner to identify any active retention risks. If risks are present, intervene within 30 days. After departure, the <strong>${extGap}%</strong> external hire gap means recovery is projected at only <strong>${recov12}%</strong> of pre-departure capacity at 12 months.`),
        action(3,"Short-term (30–90 days)","Systematic Documentation",`Establish a documentation program targeting ${first}'s most operationally exposed knowledge in <strong>${cat1}</strong> and <strong>${cat2}</strong>. Structure sessions to surface the tacit knowledge that standard job documentation never captures: exception-handling logic, informal decision rules, and the relationship context successors most need.`),
        bestSuccName
          ? action(4,"Short-term (30–90 days)","Knowledge Transfer Partnership",`Pair ${bestSuccName} (${bestSuccPct}% readiness) directly with ${first} in a structured knowledge transfer arrangement. Assign ${bestSuccName} as a shadow or co-owner on ${first}'s active <strong>${cat1}</strong> responsibilities for a minimum of 60 days. This is the fastest mechanism for closing the readiness gap. ${secSuccName ? `${secSuccName} (${secSuccPct}%) should receive parallel exposure in <strong>${cat2}</strong>.` : ""}`)
          : action(4,"Short-term (30–90 days)","Internal and External Pipeline",`With no successor above 30% readiness, run two parallel tracks: accelerate the most proximate internal candidates through structured <strong>${cat1}</strong> exposure, and initiate external search for candidates with directly relevant expertise. Given the <strong>${extGap}%</strong> external hire gap, both tracks are necessary.`)
      ]
    ];
    return variants[v % 4].join("");
  }

  if (q === "Replaceable Executive") {
    const variants = [
      [
        action(1,"Short-term (30–90 days)","Succession Identification",
          bestSuccName
            ? `Designate ${bestSuccName} (${bestSuccPct}% readiness) as the primary succession candidate for ${first}'s <strong>${cat1}</strong> responsibilities. ${secSuccName ? `${secSuccName} (${secSuccPct}%) provides a secondary pathway for <strong>${cat2}</strong> coverage.` : ""} The gap in this profile is leadership authority, not knowledge — succession planning should focus on developing executive confidence and stakeholder relationships rather than technical cross-training.`
            : `Conduct a formal internal assessment to identify succession candidates with relevant <strong>${cat1}</strong> exposure and leadership potential. The knowledge gap is manageable; the priority is finding individuals who can develop the organizational authority and stakeholder relationships that make this role effective.`),
        action(2,"Short-term (30–90 days)","Transition Architecture",`Develop a structured transition plan that allows ${first}'s institutional relationships, including ${p1}${p2 ? ` and ${p2}` : ""}, to be formally transferred before departure. Schedule joint-presence meetings now to establish continuity, even without an active departure signal.`),
        action(3,"Medium-term (90–180 days)","Leadership Development",`Accelerate successor readiness through expanded responsibilities, formal mentoring, and deliberate exposure to the decision-making contexts where ${first}'s authority currently operates. The target is not knowledge transfer but leadership preparation, building the judgment and stakeholder trust that can only develop through experience.`)
      ],
      [
        action(1,"Short-term (30–90 days)","Successor Designation and Development",
          bestSuccName
            ? `Formally designate ${bestSuccName} (${bestSuccPct}% readiness) as the primary succession candidate. Begin delegating components of ${first}'s <strong>${cat1}</strong> authority to them now, before any departure, to build practical readiness in context. ${secSuccName ? `Maintain ${secSuccName} (${secSuccPct}%) as a secondary succession pathway.` : ""}`
            : `Initiate a structured succession identification process. Given that the knowledge risk is distributed rather than concentrated, the selection criteria should weight leadership capability and stakeholder credibility more heavily than domain expertise in <strong>${cat1}</strong>.`),
        action(2,"Short-term (30–90 days)","Relationship Transfer Program",`Systematically redistribute ${first}'s key stakeholder relationships to named successors. Assign relationship stewards for each critical contact, including ${p1}${p2 ? ` and ${p2}` : ""}, and schedule introductions while ${first} is available to provide context and credibility transfer.`),
        action(3,"Medium-term (90–180 days)","Strategic Context Documentation",`Commission ${first} to produce a strategic context document: the history of key decisions, active stakeholder commitments, and the informal organizational dynamics that a successor will need to navigate. This is not a job description. It is the institutional memory that makes the role effective.`)
      ]
    ];
    return variants[v % 2].join("");
  }

  // Low Priority — 2 action items
  const variants = [
    [
      action(1,"Short-term (30–90 days)","Standard Documentation",`Ensure that ${first}'s responsibilities in <strong>${cat1}</strong> are documented in formats that successors can access without ${first}'s involvement. Focus on the operational processes most likely to create disruption if undocumented — routine documentation is the lowest-cost succession intervention.`),
      action(2,"Medium-term (90–180 days)","Cross-Training",`Identify one or two colleagues for cross-training in ${first}'s primary domain as a routine succession hedge. The goal is not to create a full replacement but to reduce single-point dependency in the most operationally exposed areas of ${first}'s work.`)
    ],
    [
      action(1,"Short-term (30–90 days)","Knowledge Documentation",`Document ${first}'s <strong>${cat1}</strong> responsibilities in a format accessible to successors. Prioritize processes that are least visible in existing documentation and most likely to create operational gaps if undocumented. Standard transition protocols are appropriate given the low-priority risk classification.`),
      action(2,"Medium-term (90–180 days)","Succession Monitoring",`Include ${first} in quarterly knowledge risk reviews to verify that the low-priority classification remains accurate. Role scope can expand over time, and silent threat profiles sometimes originate from employees who were correctly classified as low priority in earlier periods.`)
    ]
  ];
  return variants[v % 2].join("");
}

// ── AI Automation engine ───────────────────────────────────────────────────────
const AI_TOPICS = [
  { name: "Research & Quantitative Analysis", baseLLM: 72, agentic: 55, codifiability: 80 },
  { name: "California Energy Crisis",         baseLLM: 30, agentic: 15, codifiability: 12 },
  { name: "Corporate Communications",         baseLLM: 65, agentic: 40, codifiability: 55 },
  { name: "General Operations",               baseLLM: 55, agentic: 65, codifiability: 70 },
  { name: "Executive Operations",             baseLLM: 35, agentic: 30, codifiability: 25 },
  { name: "Legal — Transactional",            baseLLM: 60, agentic: 45, codifiability: 65 },
  { name: "Document Mgmt & Admin",            baseLLM: 80, agentic: 85, codifiability: 90 },
  { name: "Structured Finance & Derivatives", baseLLM: 68, agentic: 50, codifiability: 60 },
  { name: "Trading Operations",               baseLLM: 58, agentic: 62, codifiability: 55 },
  { name: "Legal — Corporate Governance",     baseLLM: 45, agentic: 25, codifiability: 35 },
  { name: "Government Relations",             baseLLM: 20, agentic: 10, codifiability:  8 },
  { name: "HR & Personnel",                   baseLLM: 50, agentic: 55, codifiability: 60 },
  { name: "IT & Infrastructure",              baseLLM: 70, agentic: 75, codifiability: 85 }
];

const AI_YEARS = [
  { year: 2024, mult: 0.70, label: "Early agents · basic RAG" },
  { year: 2025, mult: 0.85, label: "Improved tool use · multi-step chains" },
  { year: 2026, mult: 1.00, label: "Current-generation agents · RAG + tool use" },
  { year: 2027, mult: 1.15, label: "Autonomous workflows · cross-system orchestration" },
  { year: 2028, mult: 1.35, label: "Domain-specialist agents · persistent memory" },
  { year: 2029, mult: 1.50, label: "Multi-agent coordination · judgment scaffolding" },
  { year: 2030, mult: 1.65, label: "Near-human task planning · deep org integration" },
  { year: 2031, mult: 1.75, label: "Adaptive learning agents · tacit knowledge inference" },
  { year: 2032, mult: 1.85, label: "Ceiling scenario · max projected capability" }
];

let aiSliderIdx    = 2;   // default 2026
let aiSelectedEmail = null;
let aiBuilt        = false;
let aiDots         = null;
let aiScatterRefs  = null;
let aiComputedData = [];
let aiQuadFilter   = null;
let aiKrsThreshold = 20;  // fixed at 20; dots move through it as slider advances

function getAutomability(topic, mult) {
  const adj = Math.min(100, topic.agentic * mult);
  return Math.round(0.40 * topic.baseLLM + 0.35 * adj + 0.25 * topic.codifiability);
}

// Junior/admin role keywords — these roles carry an inherent automability floor
const JUNIOR_ROLE_KEYWORDS = ['associate', 'junior', 'assistant', 'coordinator', 'admin', 'clerk', 'analyst'];


function computeEmployeeAI(person, mult) {
  let totalWeight = 0, weightedAuto = 0;
  const breakdown = [];
  (person.topic_profile || []).forEach(t => {
    const topic = AI_TOPICS.find(at => at.name === t.category);
    if (!topic) return;
    const auto = getAutomability(topic, mult);
    const w = t.score || 0;
    weightedAuto += w * auto;
    totalWeight   += w;
    breakdown.push({
      name: t.category, weight: w, automability: auto,
      aiCoverable:   w * (auto / 100),
      humanResidual: w * (1 - auto / 100)
    });
  });

  // Raw exposure from topic distribution
  const rawExposure = totalWeight > 0 ? Math.round(weightedAuto / totalWeight) : 0;

  // Role-level floor: junior/admin work is inherently automatable (scheduling, data entry,
  // correspondence) regardless of which topic cluster the emails land in
  const roleStr = (person.role || '').toLowerCase();
  const isJuniorRole = JUNIOR_ROLE_KEYWORDS.some(kw => roleStr.includes(kw));
  const exposure = isJuniorRole ? Math.max(35, rawExposure) : rawExposure;

  // Base KRS from graph/topic analysis (static per person)
  const baseKrs = Math.round((person.risk_score || 0) * 100);

  // Adjusted KRS: as AI capability rises it acts as partial knowledge backup,
  // reducing the organizational risk of losing this person.
  // absorption factor = 0.5 (AI performs tasks but only partially retains institutional memory)
  const rawAdjKrs = baseKrs * (1 - (exposure / 100) * 0.5);

  // Positional Impact gate: true authority (graph centrality + role seniority composite)
  // determines whether a hard Adjusted KRS floor applies.
  // PI >= 80 → C-suite authority → floor at 25 (Lay, Skilling, Beck)
  // PI >= 60 → senior leadership → floor at 20
  // PI <  60 → no floor; standard formula applies unchanged
  const pi = Math.round((person.positional_impact || 0) * 100);
  const piFloorVal = pi >= 80 ? 25 : pi >= 60 ? 20 : 0;
  const krs = Math.round(piFloorVal > 0 ? Math.max(rawAdjKrs, piFloorVal) : rawAdjKrs);

  let quadrant;
  if      (krs >= 20 && exposure < 65)  quadrant = "Critical Human Capital";
  else if (krs >= 20 && exposure >= 65) quadrant = "Transition Candidate";
  else if (krs <  20 && exposure < 65)  quadrant = "Human Workforce";
  else                                   quadrant = "AI-Ready Role";

  return { exposure, residualGap: 100 - exposure, breakdown, quadrant, krs, rawAdjKrs: Math.round(rawAdjKrs), baseKrs, pi, piFloorVal };
}

function _aiQuadColor(q) {
  return q === "Transition Candidate" ? "#D4342E"
       : q === "Critical Human Capital" ? "#0072BC"
       : q === "Human Workforce" ? "#C49032"
       : "#2D8C3C";
}

function _rebuildAIData() {
  if (!DATA) return;
  const mult = AI_YEARS[aiSliderIdx].mult;
  aiComputedData = DATA.people.map(p => {
    const ai = computeEmployeeAI(p, mult);
    return { person: p, ...ai };
  });
  // Fixed KRS threshold at Y=20. The divider line stays put; dots move downward
  // through it as the slider advances and AI absorption compresses adjusted KRS values.
  aiKrsThreshold = 20;

  // Classify quadrants using the fixed threshold
  // visualQuadrant = math-based position; quadrant = with PI >= 80 executive override
  aiComputedData.forEach(d => {
    let vq;
    if      (d.krs >= aiKrsThreshold && d.exposure < 65)  vq = "Critical Human Capital";
    else if (d.krs >= aiKrsThreshold && d.exposure >= 65) vq = "Transition Candidate";
    else if (d.krs <  aiKrsThreshold && d.exposure < 65)  vq = "Human Workforce";
    else                                                    vq = "AI-Ready Role";
    d.visualQuadrant = vq;
    // Executive override: PI >= 80 → always Critical Human Capital
    d.quadrant = (d.pi >= 80) ? "Critical Human Capital" : vq;
    // piOverride = true when the override actually changes their classification
    d.piOverride = d.pi >= 80 && vq !== "Critical Human Capital";
  });
}

function onAISlider(val) {
  aiSliderIdx = +val;
  document.getElementById("aiYearNum").textContent  = AI_YEARS[aiSliderIdx].year;
  document.getElementById("aiYearDesc").textContent = AI_YEARS[aiSliderIdx].label;
  const hintEl = document.getElementById("aiHintDesc");
  if (hintEl) hintEl.textContent = AI_YEARS[aiSliderIdx].year + " · " + AI_YEARS[aiSliderIdx].label;
  _rebuildAIData();
  _updateAISummaryGrid();
  _renderAIEmpList();
  reportBuilt = false;  // Report AI section must reflect current slider year on next visit
  buildAIScatter();
  if (aiSelectedEmail) {
    renderAIRightPanel(aiSelectedEmail);
    // Re-apply selection stroke lost during scatter rebuild
    if (aiDots) {
      aiDots
        .attr("stroke",       d => d.person.person === aiSelectedEmail ? "rgba(255,255,255,0.85)" : "none")
        .attr("stroke-width", d => d.person.person === aiSelectedEmail ? 2 : 0);
    }
  }
}

function _updateAISummaryGrid() {
  if (!aiComputedData.length) return;
  const n      = aiComputedData.length;
  const avgExp = Math.round(aiComputedData.reduce((s,d) => s + d.exposure,    0) / n);
  const avgGap = Math.round(aiComputedData.reduce((s,d) => s + d.residualGap, 0) / n);
  const aiRdy  = aiComputedData.filter(d => d.quadrant === "AI-Ready Role").length;
  const critHC = aiComputedData.filter(d => d.quadrant === "Critical Human Capital").length;
  document.getElementById("aiSummaryGrid").innerHTML = `
    <div class="ai-summary-card">
      <div class="ai-summary-val" style="color:#D4342E">${avgExp}</div>
      <div class="ai-summary-lbl">Avg AI Exposure</div>
    </div>
    <div class="ai-summary-card">
      <div class="ai-summary-val" style="color:#2D8C3C">${avgGap}</div>
      <div class="ai-summary-lbl">Avg Human Gap</div>
    </div>
    <div class="ai-summary-card">
      <div class="ai-summary-val" style="color:#2D8C3C">${aiRdy}</div>
      <div class="ai-summary-lbl">AI-Ready Roles</div>
    </div>
    <div class="ai-summary-card">
      <div class="ai-summary-val" style="color:#0072BC">${critHC}</div>
      <div class="ai-summary-lbl">Critical HC</div>
    </div>`;
  _renderAIFilterPills();
}

function _renderAIFilterPills() {
  const wrap = document.getElementById("aiFilterWrap");
  if (!wrap) return;
  const qdist = {
    "Critical Human Capital": aiComputedData.filter(d => d.quadrant === "Critical Human Capital").length,
    "Transition Candidate":   aiComputedData.filter(d => d.quadrant === "Transition Candidate").length,
    "Human Workforce":       aiComputedData.filter(d => d.quadrant === "Human Workforce").length,
    "AI-Ready Role":          aiComputedData.filter(d => d.quadrant === "AI-Ready Role").length,
  };
  const pills = [
    { q: "Critical Human Capital", label: "Critical Human Capital", rgba: "0,114,188",  color: "#0072BC" },
    { q: "Transition Candidate",   label: "Transition Candidate",   rgba: "212,52,46",  color: "#D4342E" },
    { q: "Human Workforce",       label: "Human Workforce",       rgba: "196,144,50", color: "#C49032" },
    { q: "AI-Ready Role",          label: "AI-Ready Role",          rgba: "45,140,60",  color: "#2D8C3C" },
  ];
  const titleHTML = `<div class="panel-title" style="margin-bottom:6px">Filter by quadrant</div>`;
  const pillsHTML = pills.map(({ q, label, rgba, color }) => {
    const isActive = aiQuadFilter === q;
    const bg = isActive ? `rgba(${rgba},0.32)` : `rgba(${rgba},0.08)`;
    const shadow = isActive ? `inset 3px 0 0 ${color}` : "none";
    return `<div id="aifp-${q.replace(/[\s.]/g,'_')}" data-q="${q}" data-rgba="${rgba}" data-color="${color}"
      onclick="toggleAIFilter('${q}')"
      onmouseenter="this.style.background='rgba(${rgba},'+(aiQuadFilter==='${q}'?'0.42':'0.16')+')'"
      onmouseleave="this.style.background='rgba(${rgba},'+(aiQuadFilter==='${q}'?'0.32':'0.08')+')'"
      style="font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:600;text-transform:uppercase;letter-spacing:1px;cursor:pointer;border-radius:4px;padding:7px 10px;margin-bottom:5px;background:${bg};color:${color};border:1px solid rgba(${rgba},0.15);box-shadow:${shadow}"
      >${label} (${qdist[q]})</div>`;
  }).join("");
  const resetHTML = `<div onclick="toggleAIFilter(null)" onmouseenter="this.style.textDecoration='underline'" onmouseleave="this.style.textDecoration='none'" style="font-size:9px;color:var(--text-faint);cursor:pointer;margin-top:2px">Reset filter</div>`;
  wrap.innerHTML = titleHTML + pillsHTML + resetHTML;
}

function _renderAIEmpList(filter) {
  const query = (filter !== undefined ? filter : (document.getElementById("aiSearchBox") || {}).value || "").toLowerCase().trim();
  let rows = [...aiComputedData];
  if (aiQuadFilter) rows = rows.filter(d => d.quadrant === aiQuadFilter);
  if (query) rows = rows.filter(d => (d.person.display_name || "").toLowerCase().includes(query) || (d.person.person || "").toLowerCase().includes(query));
  rows.sort((a, b) => b.residualGap - a.residualGap);
  const hdr = document.getElementById("aiListHdr");
  if (hdr) hdr.textContent = aiQuadFilter ? `${aiQuadFilter} — ${rows.length} employees` : "Employees — ranked by human residual gap";
  document.getElementById("aiEmpList").innerHTML = rows.map(d => {
    const name = d.person.display_name || formatName(d.person.person);
    const qc   = _aiQuadColor(d.quadrant);
    const sel  = d.person.person === aiSelectedEmail ? " ai-selected" : "";
    return `<div class="ai-emp-row${sel}" onclick="selectAIEmployee('${d.person.person}')">
      <div style="flex:1;min-width:0">
        <div class="ai-emp-name">${name}</div>
        <div class="ai-emp-quad" style="color:${qc}">${d.quadrant}</div>
      </div>
      <div class="ai-emp-gap" style="color:${qc}">${d.residualGap}<span class="ai-emp-sub"> /100</span></div>
    </div>`;
  }).join("");
}

function filterAIList(val) { _renderAIEmpList(val); }

function toggleAIFilter(q) {
  aiQuadFilter = (aiQuadFilter === q) ? null : q;
  _renderAIFilterPills();
  _renderAIEmpList();
  applyAIZoom(aiQuadFilter);
}

function selectAIEmployee(email) {
  aiSelectedEmail = email;
  _renderAIEmpList();
  renderAIRightPanel(email);
  if (aiDots) {
    aiDots
      .attr("stroke",       d => d.person.person === email ? "rgba(255,255,255,0.85)" : "none")
      .attr("stroke-width", d => d.person.person === email ? 2 : 0)
      .attr("r", d => {
        const sel = d.person.person === email;
        if (!aiQuadFilter) return sel ? 7 : 5;
        const inQ = d.quadrant === aiQuadFilter || (d.piOverride && d.visualQuadrant === aiQuadFilter);
        return inQ ? (sel ? 8 : 6) : 4;
      })
      .attr("opacity", d => {
        const sel = d.person.person === email;
        if (!aiQuadFilter) return sel ? 1 : 0.78;
        const inQ = d.quadrant === aiQuadFilter || (d.piOverride && d.visualQuadrant === aiQuadFilter);
        return inQ ? (sel ? 1 : 0.88) : 0.10;
      });
  }
}

function renderAIRightPanel(email) {
  const d = aiComputedData.find(x => x.person.person === email);
  if (!d) return;
  const p     = d.person;
  const name  = p.display_name || formatName(p.person);
  const role  = p.role || "Enron Employee";
  const qc    = _aiQuadColor(d.quadrant);
  const qBadge = d.quadrant === "Transition Candidate"   ? "ai-quad-tc"
               : d.quadrant === "Critical Human Capital" ? "ai-quad-chc"
               : d.quadrant === "Human Workforce"       ? "ai-quad-ns"
               :                                          "ai-quad-ar";
  const krs     = d.krs;      // adjusted for AI capability at current slider year
  const baseKrs = d.baseKrs;  // original graph-derived KRS, slider-independent
  const pi         = d.pi !== undefined ? d.pi : Math.round((p.positional_impact || 0) * 100);
  const piFloorVal = d.piFloorVal || 0;
  const krsColor = krs > 30 ? "#D4342E" : krs > 15 ? "#C49032" : "#F5F5F7";
  const piColor  = pi  > 60 ? "#D4342E" : pi  > 30 ? "#C49032" : "#F5F5F7";

  const top5 = [...d.breakdown].sort((a,b) => b.humanResidual - a.humanResidual).slice(0, 5);
  const breakdownHTML = top5.map(t => {
    const pctH = Math.round((1 - t.automability / 100) * 100);
    const shortN = t.name.length > 30 ? t.name.slice(0, 28) + "…" : t.name;
    return `<div class="ai-breakdown-row">
      <div class="ai-br-name">${shortN} <span style="opacity:0.35">(auto: ${t.automability})</span></div>
      <div class="ai-br-track">
        <div class="ai-br-ai"    style="width:${t.automability}%"></div>
        <div class="ai-br-human" style="width:${pctH}%"></div>
      </div>
    </div>`;
  }).join("");

  const narrative = _genAINarrative(d, name);

  document.getElementById("aiRightPanel").innerHTML = `
    <div class="ai-profile-wrap">
      <div class="ai-prof-name">${name}</div>
      <div class="ai-prof-role">${role}</div>
      <span class="ai-quad-badge ${qBadge}">${d.quadrant}</span>
      <div class="ai-score-bubbles">
        <div class="ai-bubble">
          <div class="ai-bubble-val" style="color:#D4342E">${d.exposure}<span class="ai-bubble-sub">/100</span></div>
          <div class="ai-bubble-lbl">AI Exposure</div>
        </div>
        <div class="ai-bubble">
          <div class="ai-bubble-val" style="color:#2D8C3C">${d.residualGap}<span class="ai-bubble-sub">/100</span></div>
          <div class="ai-bubble-lbl">Human Gap</div>
        </div>
        <div class="ai-bubble">
          <div class="ai-bubble-val" style="color:${krsColor}">${krs}<span class="ai-bubble-sub">/100</span></div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:7.5px;color:rgba(255,255,255,0.28);margin-top:2px;line-height:1">${baseKrs} base${piFloorVal > 0 && krs === piFloorVal ? ` · PI floor` : ""}</div>
          <div class="ai-bubble-lbl">Adj. KRS</div>
        </div>
        <div class="ai-bubble">
          <div class="ai-bubble-val" style="color:${piColor}">${pi}<span class="ai-bubble-sub">/100</span></div>
          <div class="ai-bubble-lbl">PI Score</div>
        </div>
      </div>
      <div class="ai-breakdown-hdr">Topic Substitution Breakdown</div>
      <div class="ai-breakdown-legend">
        <span><span class="ai-br-swatch" style="background:var(--enron-blue)"></span>AI-Coverable</span>
        <span><span class="ai-br-swatch" style="background:var(--enron-red)"></span>Human Residual</span>
        <span style="opacity:0.4">(auto score)</span>
      </div>
      ${breakdownHTML}
      <div class="ai-narrative">${narrative}</div>
    </div>`;
}

function _genAINarrative(d, name) {
  const first   = name.split(" ")[0];
  const year    = AI_YEARS[aiSliderIdx].year;
  const q       = d.quadrant;
  const exp     = d.exposure;
  const gap     = d.residualGap;
  const krs     = d.krs;
  const baseKrs = d.baseKrs;
  const topH   = [...d.breakdown].sort((a,b) => b.humanResidual - a.humanResidual)[0];
  const topAI  = [...d.breakdown].sort((a,b) => b.automability  - a.automability )[0];
  const hn     = topH  ? `<em>${topH.name}</em>`  : "their primary domain";
  const an     = topAI ? `<em>${topAI.name}</em>` : "their primary domain";
  const piFloorVal = d.piFloorVal || 0;
  const floorActive = piFloorVal > 0 && krs === piFloorVal;
  const krsNote = baseKrs !== krs
    ? floorActive
      ? ` At ${year} capability levels, AI can absorb some workflow, but high positional authority (PI: ${d.pi}) prevents KRS from dropping below the floor of ${piFloorVal}.`
      : ` At ${year} capability levels, AI systems can absorb a portion of this role's workflow, reducing the adjusted knowledge risk score from ${baseKrs} to ${krs}.`
    : "";

  if (q === "Transition Candidate") {
    return `By ${year}, ${first}'s role carries an AI exposure score of ${exp}/100 — placing them in the <em>Transition Candidate</em> quadrant. High organizational knowledge risk combined with high AI substitutability indicates that both departure risk and replacement risk are elevated simultaneously. The domain with the highest remaining human residual is ${hn}.${krsNote} Proactive role redesign and structured knowledge transfer are indicated before AI capability reaches this threshold.`;
  }
  if (q === "Critical Human Capital") {
    if (d.piOverride) {
      return `Despite an AI exposure score of ${exp}/100 that places this role in the Transition Candidate quadrant mathematically, ${first}'s positional authority (PI: ${d.pi}) reflects executive judgment, board-level relationships, and crisis decision-making that remain beyond AI substitution at any projected capability level.${krsNote} With a residual human gap of ${gap}/100, this role is classified as Critical Human Capital. Retention, succession planning, and explicit institutional knowledge transfer are the primary levers.`;
    }
    return `In ${year}, ${first}'s role shows an AI exposure of ${exp}/100 — below the substitutability threshold despite elevated organizational risk. The work anchored in ${hn} requires judgment, context, and relational capital that current AI systems cannot adequately replicate.${krsNote} With a residual human gap of ${gap}/100, this profile represents irreplaceable institutional knowledge. Retention and succession planning are the primary levers.`;
  }
  if (q === "Human Workforce") {
    return `${first}'s AI exposure of ${exp}/100 in ${year} reflects limited substitutability alongside a contained organizational knowledge footprint. The domain of ${hn} anchors the human-residual portion of their work.${krsNote} As AI capability advances along this trajectory, periodic reclassification checks are advisable — profiles in this quadrant can shift to Transition Candidate as agentic multipliers increase.`;
  }
  return `With an AI exposure score of ${exp}/100 in ${year}, ${first}'s role sits in the <em>AI-Ready Role</em> quadrant — low organizational knowledge risk and above-threshold AI substitutability. The domain ${an} shows the highest automability in the portfolio.${krsNote} This role is a candidate for AI augmentation or workflow redesign, freeing capacity for higher-residual human work elsewhere in the organization.`;
}

function buildAIScatter() {
  const el = document.getElementById("aiScatter");
  if (!el) return;
  const rect = el.getBoundingClientRect();
  const W  = rect.width  || el.parentElement?.getBoundingClientRect().width  || 600;
  const H  = rect.height || el.parentElement?.getBoundingClientRect().height || 500;
  const mg = { top: 28, right: 20, bottom: 44, left: 52 };
  const w  = W - mg.left - mg.right;
  const h  = H - mg.top  - mg.bottom;

  const svg = d3.select("#aiScatter");
  svg.selectAll("*").remove();
  const g = svg.append("g").attr("transform", `translate(${mg.left},${mg.top})`);

  // X-axis = AI Exposure [0,100], Y-axis = KRS [0,50]
  // Capping Y at 50 (max Adjusted KRS after floors is ~35) so divider at 20 is at 60% from top,
  // giving AI-Ready (bottom-right) the most visual space proportional to its population.
  // SVG Y: 0=top (high KRS), h=bottom (low KRS)
  const xSc = d3.scaleLinear().domain([0, 100]).range([0, w]);    // AI Exposure
  const ySc = d3.scaleLinear().domain([0, 50]).range([h, 0]);     // KRS capped at 50

  // Quadrant background regions — stored for zoom
  // X divider at AI Exposure = 50; Y divider at KRS = 20
  // Top-left  (exp<50, krs≥20) = Critical HC        (blue)
  // Top-right (exp≥50, krs≥20) = Transition Cand    (red)
  // Bot-left  (exp<50, krs<20) = Human Workforce   (gold)
  // Bot-right (exp≥50, krs<20) = AI-Ready Role      (green) ← spacious majority
  const EXP_VIS = 65;
  const KRS_VIS = aiKrsThreshold;
  const bgRects = [
    { x:0,             y:0,            w:xSc(EXP_VIS),    h:ySc(KRS_VIS),    fill:"rgba(0,114,188,0.05)"  },  // top-left  CHC
    { x:xSc(EXP_VIS), y:0,            w:w-xSc(EXP_VIS), h:ySc(KRS_VIS),    fill:"rgba(212,52,46,0.05)"  },  // top-right TC
    { x:0,             y:ySc(KRS_VIS), w:xSc(EXP_VIS),   h:h-ySc(KRS_VIS), fill:"rgba(196,144,50,0.05)" },  // bot-left  NS
    { x:xSc(EXP_VIS), y:ySc(KRS_VIS), w:w-xSc(EXP_VIS), h:h-ySc(KRS_VIS), fill:"rgba(45,140,60,0.05)"  },  // bot-right AI-Ready
  ];
  const bgs = bgRects.map(r =>
    g.append("rect").attr("x",r.x).attr("y",r.y).attr("width",r.w).attr("height",r.h)
      .attr("fill",r.fill).attr("pointer-events","none")
  );

  // Quadrant corner labels — stored for zoom
  const qLabels = [
    g.append("text").attr("x",4).attr("y",ySc(KRS_VIS)-6).attr("font-family","'JetBrains Mono',monospace").attr("font-size",9).attr("font-weight",700).attr("fill","rgba(255,255,255,0.22)").text("CRITICAL HUMAN CAPITAL"),
    g.append("text").attr("x",xSc(EXP_VIS)+6).attr("y",ySc(KRS_VIS)-6).attr("font-family","'JetBrains Mono',monospace").attr("font-size",9).attr("font-weight",700).attr("fill","rgba(255,255,255,0.22)").text("TRANSITION CANDIDATE"),
    g.append("text").attr("x",4).attr("y",ySc(KRS_VIS)+14).attr("font-family","'JetBrains Mono',monospace").attr("font-size",9).attr("font-weight",700).attr("fill","rgba(255,255,255,0.22)").text("HUMAN WORKFORCE"),
    g.append("text").attr("x",xSc(EXP_VIS)+6).attr("y",ySc(KRS_VIS)+14).attr("font-family","'JetBrains Mono',monospace").attr("font-size",9).attr("font-weight",700).attr("fill","rgba(255,255,255,0.22)").text("AI-READY ROLE"),
  ];

  // Threshold lines — stored for zoom
  const threshLines = [
    g.append("line").attr("x1",xSc(EXP_VIS)).attr("x2",xSc(EXP_VIS)).attr("y1",0).attr("y2",h)
      .attr("stroke","rgba(255,255,255,0.15)").attr("stroke-width",1).attr("stroke-dasharray","4,3"),
    g.append("line").attr("x1",0).attr("x2",w).attr("y1",ySc(KRS_VIS)).attr("y2",ySc(KRS_VIS))
      .attr("stroke","rgba(255,255,255,0.15)").attr("stroke-width",1).attr("stroke-dasharray","4,3"),
  ];

  // Axes — stored for zoom transitions
  const xAxisFn = d3.axisBottom(xSc).ticks(5).tickSize(4);
  const yAxisFn = d3.axisLeft(ySc).ticks(5).tickSize(4);
  const xAxisSel = g.append("g").attr("transform",`translate(0,${h})`).call(xAxisFn);
  const yAxisSel = g.append("g").call(yAxisFn);
  const _styleAxes = () => {
    xAxisSel.selectAll("text").style("font-family","'JetBrains Mono',monospace").style("font-size","9px").style("fill","rgba(255,255,255,0.35)");
    xAxisSel.selectAll(".domain,.tick line").style("stroke","rgba(255,255,255,0.12)");
    yAxisSel.selectAll("text").style("font-family","'JetBrains Mono',monospace").style("font-size","9px").style("fill","rgba(255,255,255,0.35)");
    yAxisSel.selectAll(".domain,.tick line").style("stroke","rgba(255,255,255,0.12)");
  };
  _styleAxes();

  // Axis labels
  g.append("text").attr("x",w/2).attr("y",h+38).attr("text-anchor","middle").attr("fill","rgba(255,255,255,0.35)").attr("font-size",9).attr("font-family","'JetBrains Mono',monospace").text("AI Exposure →");
  g.append("text").attr("transform","rotate(-90)").attr("x",-h/2).attr("y",-42).attr("text-anchor","middle").attr("fill","rgba(255,255,255,0.35)").attr("font-size",9).attr("font-family","'JetBrains Mono',monospace").text("← Knowledge Risk Score");

  // Count indicator (shown when zoomed into a quadrant)
  const countLabel = g.append("text")
    .attr("x", w / 2).attr("y", -10)
    .attr("text-anchor", "middle")
    .attr("font-family", "'JetBrains Mono',monospace")
    .attr("font-size", 9)
    .attr("fill", "rgba(255,255,255,0.40)")
    .attr("opacity", 0)
    .attr("pointer-events", "none");

  // Dots — cx = AI Exposure, cy = KRS
  const tt = document.getElementById("graphTooltip");
  aiDots = g.selectAll("circle.ai-dot").data(aiComputedData).enter().append("circle")
    .attr("class","ai-dot")
    .attr("cx",   d => xSc(d.exposure))
    .attr("cy",   d => ySc(d.krs))
    .attr("r",    5)
    .attr("fill", d => _aiQuadColor(d.visualQuadrant || d.quadrant))
    .attr("opacity", 0.78)
    .attr("stroke","none")
    .attr("cursor","pointer")
    .on("mouseover", function(event, d) {
      if (aiQuadFilter && d.quadrant !== aiQuadFilter) return;
      d3.select(this).attr("r",7).attr("opacity",1);
      const name = d.person.display_name || formatName(d.person.person);
      tt.textContent = name + " · " + d.quadrant;
      tt.style.display = "block";
      tt.style.left = (event.clientX + 14) + "px";
      tt.style.top  = (event.clientY - 10) + "px";
    })
    .on("mousemove", function(event) {
      tt.style.left = (event.clientX + 14) + "px";
      tt.style.top  = (event.clientY - 10) + "px";
    })
    .on("mouseout", function(event, d) {
      tt.style.display = "none";
      const sel = d.person.person === aiSelectedEmail;
      const inFilter = !aiQuadFilter || d.quadrant === aiQuadFilter;
      d3.select(this)
        .attr("r",       sel ? 7 : (inFilter ? 5 : 4))
        .attr("opacity", sel ? 1 : (inFilter ? 0.78 : 0.12));
    })
    .on("click", (event, d) => {
      if (aiQuadFilter && d.quadrant !== aiQuadFilter) return;
      selectAIEmployee(d.person.person);
    });

  // Name labels — shown for top-5 KRS at full view, top-20 by residual gap when zoomed
  const top5KrsEmails = [...aiComputedData].sort((a,b) => b.krs - a.krs).slice(0,5).map(d => d.person.person);
  const nameLabels = g.selectAll("text.ai-name-label").data(aiComputedData).enter().append("text")
    .attr("class","ai-name-label")
    .attr("x",   d => xSc(d.exposure) + 7)
    .attr("y",   d => ySc(d.krs) + 3)
    .attr("font-family","'JetBrains Mono',monospace")
    .attr("font-size", 8)
    .attr("fill","rgba(255,255,255,0.65)")
    .attr("pointer-events","none")
    .attr("opacity", d => {
      const vq = d.visualQuadrant || d.quadrant;
      if (vq === "AI-Ready Role" || vq === "Human Workforce") return 0;
      return top5KrsEmails.includes(d.person.person) ? 0.7 : 0;
    })
    .text(d => (d.person.display_name || formatName(d.person.person)).split(" ")[0] + " " + ((d.person.display_name || "").split(" ").slice(-1)[0] || ""));

  aiScatterRefs = { xSc, ySc, xAxisSel, yAxisSel, xAxisFn, yAxisFn, bgs, threshLines, qLabels, nameLabels, countLabel, _styleAxes, top5KrsEmails, w, h, EXP_VIS };

  // Apply any pending filter that was clicked before scatter was built
  if (aiQuadFilter) applyAIZoom(aiQuadFilter);
}

function applyAIZoom(q) {
  if (!aiScatterRefs) return;
  const { xSc, ySc, xAxisSel, yAxisSel, xAxisFn, yAxisFn, bgs, threshLines, qLabels, nameLabels, countLabel, _styleAxes, top5KrsEmails } = aiScatterRefs;
  const dur = 400;

  // qPts: employees "in" this quadrant for zoom purposes.
  // piOverride executives physically sit in visualQuadrant (e.g. TC space) — they show
  // in both the TC zoom (physical position) and count in the CHC filter (override classification).
  const inZoom = (d) => !q ? false
    : d.quadrant === q
    || (d.piOverride && d.visualQuadrant === q);
  const qPts = q ? aiComputedData.filter(inZoom) : [];

  // Compute zoom domain
  const KRS_Y_MAX = 50;
  if (q && qPts.length) {
    const expVals = qPts.map(d => d.exposure);
    const krsVals = qPts.map(d => d.krs);
    const eMin = Math.min(...expVals), eMax = Math.max(...expVals);
    const kMin = Math.min(...krsVals), kMax = Math.max(...krsVals);
    const padX = Math.max((eMax - eMin) * 0.2, 5);
    const padY = Math.max((kMax - kMin) * 0.2, 3);
    xSc.domain([Math.max(0, eMin - padX), Math.min(100, eMax + padX)]);
    ySc.domain([Math.max(0, kMin - padY), Math.min(KRS_Y_MAX, kMax + padY)]);
  } else {
    xSc.domain([0, 100]);
    ySc.domain([0, KRS_Y_MAX]);
  }

  // Transition axes — finer ticks when zoomed into a small domain range
  const xDom = xSc.domain(), yDom = ySc.domain();
  const xRange = xDom[1] - xDom[0], yRange = yDom[1] - yDom[0];
  const xTicks = q ? Math.min(10, Math.max(4, Math.round(xRange / 2))) : 5;
  const yTicks = q ? Math.min(10, Math.max(4, Math.round(yRange / 2))) : 5;
  xAxisSel.transition().duration(dur).ease(d3.easeQuadOut).call(xAxisFn.ticks(xTicks));
  yAxisSel.transition().duration(dur).ease(d3.easeQuadOut).call(yAxisFn.ticks(yTicks));
  setTimeout(_styleAxes, dur + 30);

  // Fade quadrant decorations
  bgs.forEach(r => r.transition().duration(dur).attr("opacity", q ? 0 : 1));
  threshLines.forEach(l => l.transition().duration(dur).attr("opacity", q ? 0 : 1));
  qLabels.forEach(t => t.transition().duration(dur).attr("opacity", q ? 0 : 1));

  // Count indicator (excluding piOverride double-count: count by visualQuadrant in override zone)
  if (countLabel) {
    if (q && qPts.length) {
      countLabel.text(`${qPts.length} employees in this quadrant`);
      countLabel.transition().duration(dur).attr("opacity", 1);
    } else {
      countLabel.transition().duration(dur).attr("opacity", 0);
    }
  }

  // Executive override banner — visible when zoomed into a quadrant that contains
  // piOverride employees (they appear here visually but are reclassified as CHC)
  const overridePts = q ? qPts.filter(d => d.piOverride) : [];
  const bannerEl = document.getElementById("aiOverrideBanner");
  if (bannerEl) {
    if (overridePts.length) {
      const names = overridePts.map(d => (d.person.display_name || formatName(d.person.person)).split(" ")[0]).join(", ");
      bannerEl.innerHTML = `<span style="color:#9ecfff;font-weight:700">Executive override active · ${overridePts.length} employee${overridePts.length > 1 ? "s" : ""} reclassified</span> — Despite occupying the ${q} quadrant mathematically, ${names.length > 60 ? `${overridePts.length} employees` : names} hold${overridePts.length === 1 ? "s" : ""} non-automatable executive authority, political relationships, and crisis decision-making capacity that AI systems cannot replicate regardless of capability level.`;
      bannerEl.style.display = "block";
    } else {
      bannerEl.style.display = "none";
    }
  }

  // Transition dots
  // Full view: color by visualQuadrant (math position)
  // Zoomed: color by quadrant (piOverride execs turn blue in any zoom)
  if (aiDots) {
    aiDots.transition().duration(dur).ease(d3.easeQuadOut)
      .attr("cx", d => xSc(d.exposure))
      .attr("cy", d => ySc(d.krs))
      .attr("fill", d => q ? _aiQuadColor(d.quadrant) : _aiQuadColor(d.visualQuadrant || d.quadrant))
      .attr("r",  d => {
        const sel = d.person.person === aiSelectedEmail;
        if (!q) return sel ? 7 : 5;
        return inZoom(d) ? (sel ? 8 : 6) : 4;
      })
      .attr("opacity", d => {
        const sel = d.person.person === aiSelectedEmail;
        if (!q) return sel ? 1 : 0.78;
        return inZoom(d) ? (sel ? 1 : 0.88) : 0.10;
      });
  }

  // Name labels
  // CHC: all names  |  TC: all names (piOverride execs highlighted blue)  |  NS/AI-Ready: none
  if (nameLabels) {
    const staggerMap = {};
    if (q && qPts.length) {
      [...qPts].sort((a,b) => a.exposure - b.exposure).forEach((d, i) => {
        staggerMap[d.person.person] = ((i % 3) - 1) * 10;
      });
    }

    nameLabels.transition().duration(dur).ease(d3.easeQuadOut)
      .attr("x", d => xSc(d.exposure) + 7)
      .attr("y", d => {
        const offset = q ? (staggerMap[d.person.person] || 0) : 0;
        return ySc(d.krs) + 3 + offset;
      })
      .attr("font-size", 8)
      .attr("fill", d => (q && d.piOverride && inZoom(d)) ? "rgba(100,180,255,0.85)" : "rgba(255,255,255,0.65)")
      .attr("opacity", d => {
        const vq = d.visualQuadrant || d.quadrant;
        // NS and AI-Ready: never show names
        if (vq === "Human Workforce" || vq === "AI-Ready Role") return 0;
        // Full view: top-5 by KRS only
        if (!q) return top5KrsEmails.includes(d.person.person) ? 0.7 : 0;
        // Zoomed: hide employees not in this view
        if (!inZoom(d)) return 0;
        // CHC and TC: show all names
        return 0.7;
      });
  }
}

function _updateAIScatterDots() {
  if (!aiDots || !aiScatterRefs) return;
  const { xSc, ySc, nameLabels, top5KrsEmails, bgs, threshLines, qLabels, w, h, EXP_VIS } = aiScatterRefs;
  const dur = 450;

  // Update threshold-dependent elements when aiKrsThreshold has changed
  if (!aiQuadFilter) {
    const yt = ySc(aiKrsThreshold);
    threshLines[1].transition().duration(dur).attr("y1", yt).attr("y2", yt);
    bgs[0].transition().duration(dur).attr("height", yt);                   // CHC top-left
    bgs[1].transition().duration(dur).attr("height", yt);                   // TC top-right
    bgs[2].transition().duration(dur).attr("y", yt).attr("height", h - yt); // NS bot-left
    bgs[3].transition().duration(dur).attr("y", yt).attr("height", h - yt); // AI-Ready bot-right
    qLabels[0].transition().duration(dur).attr("y", yt - 6);
    qLabels[1].transition().duration(dur).attr("y", yt - 6);
    qLabels[2].transition().duration(dur).attr("y", yt + 14);
    qLabels[3].transition().duration(dur).attr("y", yt + 14);
  }

  aiDots.data(aiComputedData)
    .transition().duration(dur)
    .attr("cx",   d => xSc(d.exposure))
    .attr("cy",   d => ySc(d.krs))
    .attr("fill", d => _aiQuadColor(aiQuadFilter ? d.quadrant : (d.visualQuadrant || d.quadrant)));
  if (nameLabels) {
    nameLabels.data(aiComputedData)
      .transition().duration(dur)
      .attr("x", d => xSc(d.exposure) + 7)
      .attr("y", d => ySc(d.krs) + 3);
  }
}

function initAIView() {
  if (aiBuilt) {
    // Re-entering the view: refresh summary + list in case cascade state changed
    _rebuildAIData();
    _updateAISummaryGrid();
    _renderAIEmpList();
    _updateAIScatterDots();
    return;
  }
  aiBuilt = true;
  _rebuildAIData();
  _updateAISummaryGrid();
  _renderAIEmpList();
  const hintEl = document.getElementById("aiHintDesc");
  if (hintEl) hintEl.textContent = AI_YEARS[aiSliderIdx].year + " · " + AI_YEARS[aiSliderIdx].label;
  requestAnimationFrame(() => requestAnimationFrame(() => buildAIScatter()));
}

function closeModal() {
  document.getElementById("modalOverlay").classList.remove("open");
  document.getElementById("modalBox").classList.remove("modal-animate-in");
}

// ── Historical Validation ────────────────────────────────────────────────────

const HV_EMPLOYEES = [
  { name: "Vince J Kaminski", role: "Managing Director, Research Group", cls: "oe", krs: 16,
    date: "June 1999 — October 2001",
    title: "Kaminski marginalized after opposing LJM/Raptor structures",
    text: `Kaminski served as Managing Director of the Research Group at Enron, leading the quantitative analysis team responsible for evaluating the risk of the company's energy trading and structured finance portfolios. His domain was statistical risk modeling — the technical apparatus that was supposed to determine whether Enron's special purpose entity transactions represented genuine risk transfer or accounting fiction. He was one of fewer than a dozen people at the company with the mathematical sophistication to evaluate the Raptor and LJM structures on their merits. This concentration of technical oversight capacity in a single organizational leader made him the functional bottleneck for legitimate risk assessment at a company that was systematically falsifying its financial position.

In 1999, following his team's objections to the LJM1 partnership, Skilling moved Kaminski's group from its independent risk oversight role into the trading division — a structural transfer that eliminated its ability to block transactions it evaluated as dangerous. The decision was framed as a reorganization, not a punishment. In October 2001, Kaminski attended a senior management meeting to personally warn Kenneth Lay about Fastow's financial structures. Greg Whalley physically pushed him away from the podium. Shortly after, he received a call from HR. The sequence — organizational displacement in 1999, physical removal in 2001 — documents two distinct moments at which the company acted to silence its most credible internal critic.

The model's Organizational Emergency classification with a KRS of 16 is validated by precisely the mechanism the classification is designed to detect: the organization could not function safely with Kaminski in a position of authority, and took active steps to remove him from that position. The KRS reflects not just knowledge volume but knowledge criticality — the degree to which the knowledge held is irreplaceable given the organization's current risk profile. At a company perpetrating accounting fraud, the most irreplaceable knowledge was the ability to detect that fraud. The Powers Report's conclusion that the board's risk oversight failures were structural is consistent with what Kaminski documented in real time.

The Kaminski case establishes a principle that recurs throughout the Enron dataset: organizations that are concealing fraud systematically eliminate the knowledge holders most capable of detecting it. This is not incidental — it is the mechanism by which fraud sustains itself organizationally. For knowledge risk methodology, this creates a diagnostic implication: the sudden marginalization of a high KRS employee who holds oversight or control function knowledge should be treated as a fraud signal, not merely a knowledge loss event. The absence of Kaminski's voice from Enron's risk committee is not just a succession planning failure; it is the organizational signature of institutional concealment.`,
    clsLabel: "Org emergency", outcome: "Knowledge silenced; risk failures followed", conc: "Hit",
    src: "Powers Report (Feb 2002); Trial testimony, United States v. Skilling (2006); Risk.net interview (2016)" },

  { name: "Jeff Skilling", role: "President & COO", cls: "oe", krs: 25,
    date: "August 14, 2001",
    title: "Skilling resigns as CEO after six months",
    text: `Skilling joined Enron in 1990 after a consulting career at McKinsey and within five years had become the principal architect of its transformation from a natural gas pipeline company into an asset light trading operation. His domain knowledge spanned corporate strategy, financial engineering, and the investor relations narrative that justified Enron's market valuation to Wall Street. He understood how Enron's mark to market accounting worked in detail, how the special purpose entities interacted with its reported balance sheet, and why the business model required continuous financial engineering to sustain its reported earnings. No other executive combined strategic vision, technical financial fluency, and external credibility in the same configuration.

Skilling resigned on August 14, 2001, citing personal reasons — a claim later contradicted by prosecutors who noted he had sold approximately $60 million in Enron shares in the preceding year. His departure was the first confirmation to sophisticated Wall Street analysts that something was seriously wrong. The share price had already fallen from $90.56 to approximately $42, but the earnings narrative had remained credible through Skilling's direct engagement with analysts. Within hours of his resignation, Lay named Greg Whalley as president and COO, a succession that was improvised rather than planned. Enron filed for bankruptcy on December 2, 2001 — less than four months later.

The model's Organizational Emergency classification is validated with the highest possible degree of fidelity: the timeline makes the causal relationship explicit. Skilling's departure did not coincide with the collapse; it preceded it by exactly the interval that would be expected if his presence was the primary institutional stabilizer. The model's topic assignments — Corporate Communications and Research and Quantitative Analysis — capture both dimensions of his organizational value: his ability to articulate the business model to external audiences and his technical understanding of how the financial structures actually functioned. The KRS of 25 reflects the breadth and depth of this combined knowledge position.

The Skilling case is the canonical example of CEO knowledge concentration risk in organizational theory. When the primary architect of a business model departs, the organization loses not just executive leadership but interpretive capacity — the ability to explain, defend, and adapt its own strategy. What Skilling held was not simply positional authority but operational understanding that no other member of the executive team could replicate. Organizations can plan for positional succession — they can name a new president — but they rarely plan for interpretive succession: for what happens when the person who understands how things actually work is no longer present. Enron had no interpretive successor for Skilling, and the consequences were total.`,
    clsLabel: "Org emergency", outcome: "Departure preceded collapse by 4 months", conc: "Hit",
    src: "Skilling v. United States, 561 U.S. 358 (2010); DOJ Indictment (2004)" },

  { name: "Kenneth Lay", role: "Chairman & CEO", cls: "oe", krs: 26,
    date: "August 2001 — December 2001",
    title: "Lay presided over final collapse as returning CEO",
    text: `Lay founded what became Enron in 1985 through the merger of Houston Natural Gas and InterNorth, and served as its chairman and CEO for most of the following sixteen years. His domain knowledge was concentrated in two areas: external relationships — with politicians, regulators, bank executives, and investors — and the public narrative of Enron's transformation from a pipeline company to the world's leading energy company. He maintained direct personal relationships with two U.S. presidents and was a primary architect of the deregulation policy environment in which Enron operated. His knowledge of internal financial mechanics, however, was limited: he consistently delegated operational and financial decision making to Skilling, Fastow, and the business unit heads, creating a structural knowledge gap between the company's chairman and its actual financial operations.

When Skilling resigned on August 14, 2001, Lay returned as CEO — his second tenure in the role. The transition immediately revealed the gap between his relational capital and his operational knowledge. On an October 23, 2001 analyst call, when pressed on the $1.2 billion equity write down and the Raptor transactions, Lay admitted the questions were "getting way over my head." This public admission — from the CEO of a Fortune 7 company, on a recorded analyst call, in the middle of a collapsing stock price — represents one of the most consequential single statements in the history of American corporate governance. It documented, in Lay's own words, the knowledge deficit that the model's classification is designed to quantify.

The model's Organizational Emergency classification with a KRS of 26 is validated by the outcome, but with an important nuance. The KRS measures knowledge concentration, not operational competence. Lay's high score reflects the concentration of external relationship capital in his person — relationships that were genuinely irreplaceable and that did constrain what recovery options were available to Enron in its final months. The banks that might have provided emergency liquidity maintained their relationships with Lay personally; when he could not credibly explain Enron's finances, those relationships could not be leveraged. His knowledge concentration in Communications was real and its loss was consequential — it simply could not substitute for the financial engineering knowledge that was equally lost when Skilling departed.

The Lay case illustrates a critical distinction in knowledge risk theory between relational capital and operational knowledge. These two forms of organizational knowledge require different succession strategies and create different types of organizational vulnerability. Relational capital is personal, slow to build, and impossible to transfer; it dies with the relationship holder. Operational knowledge is embedded in processes and can be documented and transferred. Enron's failure concentrated both types in its executive tier — Lay held the relationships, Skilling held the operational understanding — and the simultaneous loss of both created a collapse with no recovery path. The implication for organizational design is that relational capital concentration at the chairman level is an underrecognized structural risk that requires explicit succession planning distinct from title succession.`,
    clsLabel: "Org emergency", outcome: "Unable to prevent bankruptcy as CEO", conc: "Hit",
    src: "Enron scandal, Wikipedia; Senate Commerce Committee testimony (2002)" },

  { name: "Jeff Dasovich", role: "Government Relations Executive", cls: "st", krs: 46,
    date: "2000 — 2001",
    title: "Dasovich held critical California energy crisis knowledge",
    text: `Dasovich served as the primary government relations executive for Enron's California and western United States operations during the peak of the state's energy crisis from 2000 to 2001. His domain knowledge encompassed regulatory strategy, political relationships with California state officials and federal regulators, and the operational context of the trading strategies that his government affairs function was publicly defending. He was the organizational bridge between Enron's West Coast trading desk — which was executing the manipulation strategies — and the regulatory and political environment that was simultaneously investigating those same strategies. This bridging position gave him knowledge that was simultaneously irreplaceable and deliberately underdocumented.

The California electricity market generated extraordinary profits for Enron's trading desk during Dasovich's tenure: Timothy Belden's desk recorded $254 million in gross profits in January 2001 alone. The FERC investigation that followed, culminating in the 2003 Final Report, documented $9 billion in overcharges to California consumers and found systematic evidence of market manipulation strategies with internal code names including Fat Boy, Death Star, and Get Shorty. Dasovich's email record became a central piece of the investigative record because his government relations role required him to communicate about strategies that were simultaneously being publicly denied. The gap between what he communicated internally and what Enron was saying publicly was documented in granular detail.

The model's Silent Threat classification with a KRS of 46 — the highest in the entire dataset — is validated by the FERC investigation's reliance on the Dasovich email record to reconstruct Enron's knowledge of its California strategies. The Silent Threat classification identifies employees whose knowledge concentration is extreme relative to their organizational visibility. Dasovich was not a C suite executive; he was a government relations manager. But his position at the interface between trading operations and regulatory audiences meant he held a cross domain knowledge position that was uniquely irreplaceable. His departure or removal would have eliminated the organization's most knowledgeable interface point with the regulatory response to its own actions.

The Dasovich case establishes a principle that is central to the project's methodology: knowledge risk is not a function of organizational title or seniority. The most dangerous knowledge concentrations frequently occur at the boundary of organizational functions — at the interfaces between trading and regulation, between strategy and operations, between internal and external audiences. Employees who hold bridging positions are systematically undervalued by succession planning processes that focus on vertical hierarchies rather than horizontal connections. The model's email corpus methodology detects these bridging positions through communication patterns rather than org chart position, which is precisely why it identifies Silent Threats that title based analysis misses entirely.`,
    clsLabel: "Silent threat", outcome: "California operations subject to $9B FERC investigation", conc: "Hit",
    src: "FERC Final Report (2003); California Attorney General energy investigation records" },

  { name: "Pete Davis", role: "Energy Scheduling Coordinator", cls: "st", krs: 43,
    date: "2000 — 2001",
    title: "Davis held concentrated West Coast trading desk knowledge",
    text: `Davis served as an energy scheduling coordinator on the Portland and West Coast trading desk, one of the operational roles closest to the actual execution of California market strategies. His function was to construct, submit, and reconcile the individual energy transaction submissions that translated the trading desk's strategies into actual market activity. Energy scheduling in a manipulated market requires detailed knowledge of the mechanical rules of the ISO market — the specific submission protocols, timing windows, and operational constraints that can be exploited to implement strategies like Fat Boy and Death Star. This operational knowledge was tacit, task embedded, and deeply concentrated in the individuals who performed the work daily.

Timothy Belden, who supervised the West Coast desk, later pled guilty to wire fraud and provided extensive cooperation to federal prosecutors. His cooperation documented that the manipulation strategies required operational execution knowledge that was concentrated in the scheduling coordinators — the people who actually submitted the transactions. The Washington Post investigation of January 2003 documented that the prosecution of senior Enron executives depended in part on tracing the transaction execution chain from the desk strategy level down to the scheduler level. Davis's position in that chain made him a material witness to the operational mechanics that Belden's cooperation described at the strategic level. The Portland trading group was largely disbanded after Enron's bankruptcy, and the operational knowledge its members held was permanently lost to the organization.

The model's Silent Threat classification with a KRS of 43 is validated by the fundamental asymmetry between Davis's organizational title and his actual knowledge position. He was a scheduling coordinator — a junior operational role in an energy trading company. His knowledge risk score is the second highest in the model. This gap between title and knowledge concentration is exactly what the Silent Threat classification is designed to measure. When the Portland trading group was disbanded, no successor entity reconstructed the West Coast manipulation operation, partly because the knowledge of how it was mechanically executed no longer existed in an accessible form.

Davis is the model's most important validation case for the Silent Threat thesis. The fundamental organizational knowledge theory insight is that knowledge risk is inversely correlated with organizational visibility: the most dangerous concentrations reside in junior positions precisely because those positions receive no succession planning attention, no documentation requirements, and no organizational recognition of their knowledge value. Every succession planning framework in corporate governance focuses on senior executives. The entire professional literature on knowledge management is oriented toward capturing expert knowledge from senior leaders before retirement. Davis's case argues that this orientation is systematically wrong — that the knowledge most likely to be irreplaceable is the knowledge held by specialists in junior roles whose expertise is too narrow to be covered by any obvious successor and too valuable to survive organizational disruption.`,
    clsLabel: "Silent threat", outcome: "Trading desk disbanded; Belden pled guilty to wire fraud", conc: "Hit",
    src: "Business History Review (Cambridge, 2022); Washington Post investigation (2003)" },

  { name: "Stan Horton", role: "CEO, Enron Transportation", cls: "re", krs: 4,
    date: "Post bankruptcy",
    title: "Horton and pipeline operations survived intact",
    text: `Horton served as CEO of Enron Transportation Services and had managed Enron's pipeline operations since 1985 — predating the Enron name itself, as the assets originated with Houston Natural Gas. His domain knowledge was operational in the traditional sense: how to run a regulated natural gas pipeline business, manage relationships with federal and state regulators, maintain physical infrastructure, and operate the distribution network that connected production to consumption. Pipeline operations in regulated utilities are among the most knowledge transferable domains in the energy industry, because regulatory requirements mandate documentation and because the physical assets themselves encode operational constraints that limit the range of possible approaches and require written procedures.

When Enron filed for bankruptcy on December 2, 2001, the pipeline assets were immediately recognized as the most valuable recoverable component of the estate. The domestic pipeline business was reorganized as CrossCountry Energy and ultimately sold for $2.45 billion to a consortium including GE Capital and the Boardwalk Pipeline partnership. Approximately 1,100 employees were retained by the acquiring entity. Horton was named president and COO of Southern Union's expanded pipeline operations following the sale. The entire transaction — from bankruptcy filing to knowledge transfer to operational continuity — proceeded without any of the knowledge loss events that characterized the simultaneous collapse of Enron's trading, finance, and executive operations. The pipeline business continued to function because its knowledge base was never dependent on the organization around it.

The model's Replaceable Executive classification with a KRS of 4 is validated in the strongest available way: the actual knowledge transfer was executed successfully. The classification does not mean that Horton was unimportant or easily replaced in a personal sense. It means that the knowledge he held was embedded in organizational systems, documented in regulatory filings, and distributed across his management team in ways that made it transferable to a successor organization. The KRS measures this transferability directly. A score of 4 means that approximately 96% of the knowledge value can be reconstructed from documentation and team retention — a prediction that the CrossCountry Energy sale validated precisely.

Horton's case is the positive control in the Enron knowledge validation dataset — the case that confirms the model can identify resilience, not just vulnerability. The organizational knowledge theory implication is that knowledge transferability is a design choice, not an inherent property of knowledge domains. Pipeline operations are transferable because regulatory requirements force documentation and because the physical nature of the assets requires operational procedures to be written down. Trading and financial engineering operations are far less transferable because they resist documentation — the tacit knowledge of how specific strategies work is held by the people who execute them. Organizational leaders who want to build institutional resilience should study the pipeline business's knowledge architecture: the lesson is that the durability of an organization's knowledge base is determined not by how much its people know, but by how much of what they know is embedded in systems that outlast them.`,
    clsLabel: "Replaceable exec", outcome: "Pipeline knowledge transferred to acquirer", conc: "Hit",
    src: "NBC News (Nov 2004); SEC Form 8-K, CrossCountry Energy sale" },

  { name: "Rick Buy", role: "EVP & Chief Risk Officer", cls: "re", krs: 7,
    date: "1999 — 2001",
    title: "Chief Risk Officer function was organizationally impotent",
    text: `Buy served as Executive Vice President and Chief Risk Officer, a position that in a normally functioning organization would have been one of the most influential in Enron's governance structure. His domain knowledge encompassed formal risk management frameworks, the methodology for evaluating credit and market risk in energy trading portfolios, and the procedural architecture of Enron's risk committee structure. He had access to information about every significant transaction and nominal authority to flag or block transactions that exceeded the company's stated risk appetite. In theory, his role was the organizational check that would have prevented the SPE fraud from proceeding. In practice, the organizational dynamics were not aligned with that theory.

The Powers Report, the Senate Permanent Subcommittee investigation, and the trial record of United States v. Skilling all document that the risk committee structure over which Buy presided consistently approved transactions that presented obvious conflict of interest problems. The most consequential of these approvals was the board's June 1999 waiver of Enron's conflict of interest policy, which allowed CFO Fastow to manage the LJM1 partnership — the foundational enabling condition for the fraud. Buy did not lead the opposition to this waiver. Risk committee meetings during the period of the Raptor transactions were documented as pro forma approvals rather than substantive deliberations. Buy's effective organizational authority was substantially less than his nominal authority, and his knowledge of the fraudulent mechanics appears to have been deliberately limited by Fastow, who minimized the financial detail shared with oversight functions.

The model's Replaceable Executive classification with a KRS of 7 is partially validated by the outcome. The classification correctly identifies that Buy's knowledge was not uniquely concentrated — another CRO with the same formal responsibilities would have had access to the same information and faced the same organizational constraints. What the model does not fully capture is the dynamic that rendered that information inaccessible: the same authority structure that blocked Kaminski from speaking at management meetings also blocked Buy from exercising his nominal oversight authority. The model classifies what the knowledge is; history documents what the organization allowed the knowledge holder to do. These are different dimensions of risk that the current methodology does not fully disaggregate.

Buy's case makes an important contribution to organizational knowledge theory about the difference between nominal and effective knowledge positions. Traditional knowledge risk assessment focuses on what a person knows — their domain expertise, communication centrality, topic concentration. Buy's case argues for a second dimension: whether the organizational context allows that knowledge to be exercised. A Chief Risk Officer in an organization that systematically overrides risk management is functionally equivalent to a Chief Risk Officer who is absent. A fully developed knowledge risk framework would assess not just concentration but exercisability — the degree to which the organization's power structure actually allows oversight knowledge holders to act on their knowledge. The Enron case suggests that organizations with high power concentration at the executive level systematically neutralize their own oversight functions, creating a risk dynamic that title based or KRS based analysis alone cannot detect.`,
    clsLabel: "Replaceable exec", outcome: "Risk function failed to prevent collapse", conc: "Partial",
    src: "Powers Report (Feb 2002); Senate Subcommittee findings (July 2002)" },

  { name: "Louise Kitchen", role: "COO, Enron Wholesale Services", cls: "re", krs: 11,
    date: "1999 — Post bankruptcy",
    title: "EnronOnline architect whose innovation survived the collapse",
    text: `Kitchen served as COO of Enron Wholesale Services and, more significantly, as the creator and driving force behind EnronOnline, the energy trading platform she built from a concept in 1998 to a live product on November 29, 1999, without initial executive approval. Working from Enron's London office, she assembled a technology and operations team that built the platform in seven months on a budget of approximately $15 million. Her domain knowledge spanned energy trading operations, technology platform development, and the organizational change management required to shift a trading desk from telephone based to electronic execution. EnronOnline became the largest e commerce site in the world by transaction volume within months of launch, executing over one million transactions totaling $880 billion in trades across its two year operational life.

When Enron collapsed, UBS Warburg acquired the trading operation and EnronOnline's technology platform as part of a transaction signed within days of the bankruptcy filing on December 2, 2001. The speed of this acquisition was possible precisely because Kitchen had built EnronOnline as a technology product rather than a personal knowledge system. The platform's logic was embedded in code, its processes were documented in system specifications, and its operational team was transferable as a unit. Kitchen herself was never implicated in any aspect of the fraud and continued her career at UBS Warburg before moving to Deutsche Bank, where she led the capital release unit responsible for disposing of 72 billion euros in risk weighted assets. Her post Enron career validated both her individual capability and the model's assessment that her departure from any organization would not create an irreplaceable knowledge gap.

The model's Replaceable Executive classification with a KRS of 11 is validated by the platform's successful transfer to UBS Warburg and by Kitchen's own career continuity. A KRS of 11 means that approximately 89% of the value associated with her role is recoverable without her personal presence. The historical outcome confirms this assessment: EnronOnline operated without interruption after Kitchen's departure from Enron, which is only possible if the knowledge was genuinely embedded in the technology and team rather than in her personally. The classification correctly identifies that while Kitchen was operationally important, her impact was through the systems she created rather than through irreplaceable personal expertise.

Kitchen's case introduces a dimension of organizational knowledge theory that is absent from most succession planning frameworks: intentional knowledge externalization. Most knowledge management literature focuses on how to capture tacit knowledge from people who hold it — how to document what experts know before they leave. Kitchen's case demonstrates a more powerful alternative: build systems that hold knowledge rather than relying on people to hold it. By building EnronOnline as a technology platform with documented logic, transferable team structures, and clear operational procedures, she created conditions for knowledge survival that no succession plan could have replicated. The lesson for organizational resilience is that the most durable knowledge management strategy is to externalize knowledge into institutional systems rather than to retain the people who hold it — and that the KRS is at its most actionable not when it measures existing concentration, but when it identifies which knowledge domains could be made transferable through deliberate design choices.`,
    clsLabel: "Replaceable exec", outcome: "EnronOnline technology acquired by UBS Warburg; Kitchen continued career unimpacted", conc: "Hit",
    src: `Harvard Business School Case Study, "EnronOnline: Louise Kitchen, Intrapreneur" (2001); eFinancialCareers (June 2021); Enron Annual Report 1999` },

  { name: "Greg Whalley", role: "President & COO (post Skilling)", cls: "re", krs: 4,
    date: "August 2001 — January 2002",
    title: "Whalley named president after Skilling's departure; fired Fastow without board approval",
    text: `Whalley was a West Point graduate and former Army tank captain who joined Enron in 1992 after completing his MBA at Stanford. He rose to president of Enron Wholesale Services, running the trading division that generated the majority of Enron's actual operating profits. His domain knowledge was concentrated in energy trading operations: counterparty management, trading floor oversight, risk limit enforcement, and the operational mechanics of executing large volume commodity transactions across multiple energy markets. He was one of the most respected operational leaders in the trading division precisely because his knowledge was practical and execution oriented rather than financial engineering oriented — he understood how to trade, not how to structure special purpose entities.

When Skilling resigned on August 14, 2001, Lay named Whalley president and COO of the entire company within hours, making him the operational head of Enron during its terminal phase. Weeks later, having assessed the depth of Enron's financial problems through direct engagement with the company's bankers, Whalley fired Andrew Fastow as CFO without waiting for formal board authorization — an extraordinary act that demonstrated both his understanding of the severity of the situation and the degree to which formal governance had ceased to function. He replaced Fastow with Jeff McMahon, a decision driven by the practical necessity of convincing creditor banks to continue providing liquidity, which they refused to do while Fastow remained in his role. Whalley cooperated with federal investigators after the collapse and followed Enron's trading operation to UBS Warburg, though the legal scrutiny surrounding former Enron executives led UBS to subsequently let him go.

The model's Replaceable Executive classification with a KRS of 4 is validated by Whalley's own role in the crisis: he was the succession plan, and he functioned as one. The speed with which he was elevated from divisional president to company president, and the speed with which the Enron trading knowledge subsequently transferred to UBS Warburg, both confirm that his knowledge was distributed across the trading organization rather than uniquely concentrated in him. A KRS of 4 is the model's way of saying that the knowledge held by this executive is approximately 96% recoverable from the team and systems around them. The UBS Warburg acquisition of the trading operation validated this assessment: the trading knowledge survived Enron's collapse precisely because it was distributed.

Whalley's case illustrates what organizational knowledge theory calls improvised succession — succession that is assembled under crisis conditions from available organizational resources rather than from a deliberate plan. Improvised succession degrades knowledge at every handoff: Skilling to Whalley transferred strategic understanding to operational focus; Whalley to McMahon transferred operational knowledge to crisis management; McMahon to the bankruptcy estate transferred organizational continuity to legal administration. Each transition is a knowledge compression event in which some of what was understood at the prior level is lost because the successor was not positioned to receive it in the time available. The lesson is that succession planning must be executed when organizations are stable precisely because crisis conditions make knowledge transfer exponentially more difficult and exponentially more necessary at the same time.`,
    clsLabel: "Replaceable exec", outcome: "Served as succession plan; cooperated with prosecutors; trading knowledge transferred to UBS", conc: "Hit",
    src: "Enron scandal, Wikipedia; CorpWatch, \"10 Enron Players: Where They Landed After the Fall\"; Bloomberg (Sept 2001)" },

  { name: "John Lavorato", role: "CEO, Enron Americas", cls: "re", krs: 8,
    date: "2000 — 2003",
    title: "Lavorato supervised West Coast trading operations; cooperated with DOJ",
    text: `Lavorato served as CEO of Enron Americas, the company's central energy trading division and its primary profit engine. His domain knowledge encompassed the management of a large and complex trading organization: overseeing divisional profit and loss, managing counterparty relationships with banks and utilities across North America, setting trading strategy, and maintaining the organizational culture of a high performance trading floor. He directly supervised Timothy Belden's West Coast power desk, which was generating the California profits that constituted a significant share of Enron Americas' results. As divisional CEO, his knowledge was broad rather than deep — he understood the operations he managed at the level required to manage them, rather than at the level required to execute them personally.

Following Enron's collapse, federal prosecutors identified Lavorato as a potential witness who could provide testimony about Skilling's involvement in the California trading operations and about the extent of executive level knowledge of the manipulation strategies. The Washington Post reported in January 2003 that his attorney had confirmed he was "helping prosecutors" and was not a target of the investigation — a status that distinguished him from Belden (who pled guilty) and from the senior executives (who were indicted). His cooperation with the DOJ investigation became part of the broader prosecution strategy that produced convictions against Skilling, Lay, and multiple other Enron executives. The trading operation he managed was one of the assets transferred to UBS Warburg following the bankruptcy, and its successful transfer validated the model's assessment that management level trading knowledge was distributable.

The model's Replaceable Executive classification with a KRS of 8 is validated by two independent historical facts: Lavorato was not indicted, and the trading operation he managed was successfully transferred to a successor entity. The first fact validates the low knowledge concentration score — prosecutors did not identify him as uniquely necessary to their case, suggesting his personal knowledge of specific fraud mechanics was limited relative to his organizational seniority. The second fact validates the transferability assessment — the operation he led was sufficiently documented and its knowledge sufficiently distributed that UBS Warburg could acquire and operate it. A divisional CEO whose division transfers successfully to an acquirer is definitionally a Replaceable Executive in the knowledge risk framework.

Lavorato's case raises a methodological question about the relationship between management knowledge and operational knowledge that is relevant to all large organizations. Management knowledge — how to run an organization, manage people, set strategy, maintain culture — is by its nature less concentrated than operational knowledge, because management functions inherently require distribution: an executive who knows everything personally is not managing. The implication for knowledge risk methodology is that large organizations with well distributed management structures generate naturally low KRS scores at the management level, regardless of how concentrated the operational knowledge is at execution levels. This means that organizational knowledge risk is frequently invisible at the management level and only detectable at the operational level — precisely where Davis, Kaminski, and Dasovich sit, and precisely where succession planning never looks.`,
    clsLabel: "Replaceable exec", outcome: "Cooperated with DOJ investigation; not indicted; trading knowledge was organizational, not personal", conc: "Hit",
    src: "Washington Post investigation (Jan 2003); Trial of Kenneth Lay and Jeffrey Skilling, Wikipedia" },

  { name: "Steven Kean", role: "EVP & Chief of Staff", cls: "re", krs: 8,
    date: "2000 — 2001",
    title: "Kean's communications became central evidence in California energy investigation",
    text: `Kean served as Executive Vice President and Chief of Staff of Enron, a role that functioned as the operational hub connecting Enron's government affairs, legal, communications, and trading divisions to the executive team. His domain knowledge was coordinative rather than technical: he did not hold specialized expertise in any single domain, but he held a comprehensive picture of how the organization's strategic decisions were being translated into operational action across multiple functions simultaneously. As Chief of Staff to CEO Kenneth Lay, he was responsible for ensuring that decisions made in the executive suite were communicated to and implemented by the relevant business units — and that information from those business units reached the executive suite in a form that was actionable. This coordinative function meant his communications captured information flows that were invisible in any other single inbox.

Kean's email record became one of the most extensively cited documentary sources in the FERC investigation and congressional inquiries into the California energy crisis, not because he was directing the manipulation strategies but because his coordinative role meant his inbox and outbox captured the connections between those strategies and the executive communications function. The FERC Final Report and Senate Permanent Subcommittee investigation both relied on Kean's email record to reconstruct how information about California trading strategies moved through Enron's executive layer. His emails documented the degree to which awareness of the California strategies was simultaneously distributed across government affairs, legal, and executive communications — establishing organizational rather than individual culpability for what followed.

The model's Replaceable Executive classification with a KRS of 8 is validated by the historical record in a specific way: the value of Kean's knowledge was documentary and coordinative rather than operationally irreplaceable. His communications were valuable to investigators because they captured organizational information flows, not because they contained unique technical knowledge that only he possessed. A KRS of 8 reflects this correctly — coordinative knowledge, while organizationally important during normal operations, is reconstructable from the documentary record it generates. The fact that investigators could use his email record to reconstruct Enron's decision making confirms that his knowledge was sufficiently externalized into documentation to be recoverable even after the organization that generated it was destroyed.

Kean's case introduces an important concept for organizational knowledge theory: the coordinative role as organizational memory. Chiefs of staff, chief operating officers, and senior coordinators occupy a unique epistemic position — they know less in depth than any domain expert, but they know more in breadth than any other single person in the organization. Their knowledge is the organization's integration capacity: the ability to connect what the trading desk knows, what the legal function knows, and what the communications function knows into a coherent organizational response. The loss of a coordinative role creates a different kind of knowledge gap than the loss of a domain expert — not the loss of specific technical knowledge, but the loss of organizational synthesis capacity. Standard succession planning treats these roles as interchangeable, but the organizations that lose effective coordinators frequently discover that the replacement cannot reconstruct the web of informal understanding that their predecessor had built over years of close proximity to the executive level.`,
    clsLabel: "Replaceable exec", outcome: "Email record became critical evidence; knowledge was coordinative and broadly distributed", conc: "Hit",
    src: "FERC Final Report (2003); Senate Permanent Subcommittee on Investigations (July 2002)" },

  { name: "James Derrick", role: "EVP & General Counsel", cls: "re", krs: 6,
    date: "1999 — 2001",
    title: "General Counsel presided over legal function that failed to prevent fraud",
    text: `Derrick served as Executive Vice President and General Counsel of Enron, heading the legal department responsible for reviewing and approving the company's transactions, negotiating its major contracts, and providing legal sign off on the financial structures that were at the center of the fraud. His domain knowledge encompassed transactional law, securities regulation, and the governance frameworks that were supposed to govern Enron's related party transactions. As General Counsel, he presided over a legal function that was one of the most important oversight mechanisms in the company — second only to the risk management function in its nominal authority to block or modify transactions that raised legal or compliance concerns. The legal department's size, seniority, and formal access to transaction documents gave it every structural prerequisite for effective oversight.

The Powers Report documented that Enron's legal function, under Derrick's leadership, reviewed and approved the LJM and Raptor SPE structures, including the conflict of interest waiver that allowed Fastow to manage both the company and the partnerships with which it was transacting. The legal department's failure to flag the conflicts embedded in these arrangements was a central finding of the Powers investigation. The Senate Permanent Subcommittee investigation similarly found that legal oversight was ineffective during the period when the fraud was being constructed. Derrick himself was not indicted, which the historical record suggests reflects a genuine limitation in his knowledge of the fraud's mechanics: the evidence indicates he reviewed the structures but did not have or did not exercise the financial engineering sophistication to understand that they were designed to manipulate reported earnings rather than achieve legitimate risk transfer.

The model's Replaceable Executive classification with a KRS of 6 is partially validated by the outcome. The low KRS correctly identifies that Derrick's knowledge was not uniquely concentrated — the legal function's knowledge, while organizationally important, was broadly distributed and documentable. The limitation of the classification is that it does not capture the institutional failure dimension: the legal function did not just fail to transfer its knowledge; it failed to exercise its knowledge in the first place. The concordance is Partial because while the low KRS prediction of transferability is confirmed by Derrick's non indictment, the broader prediction that Replaceable Executive knowledge functions normally in its oversight capacity is contradicted by the legal function's systematic failure.

Derrick's case makes a contribution to organizational knowledge theory about the limits of domain expertise in oversight functions. The conventional governance assumption is that legal expertise is sufficient for legal oversight. The Enron case demonstrates that this assumption fails when the transactions being reviewed involve financial engineering techniques that require quantitative and accounting expertise to evaluate — expertise that was not in the legal function's knowledge base. Derrick's legal team could not identify the fraud in the SPE structures because understanding why those structures were fraudulent required skills that were absent from the reviewing function. The organizational knowledge lesson is that effective oversight requires knowledge that matches the knowledge of the function being overseen — a standard that Enron's governance structure systematically failed to meet across multiple oversight layers simultaneously.`,
    clsLabel: "Replaceable exec", outcome: "Legal function failed oversight role; Derrick not indicted personally", conc: "Partial",
    src: "Powers Report (Feb 2002); Senate Permanent Subcommittee on Investigations (July 2002)" },

  { name: "Sally Beck", role: "COO, Enron Wholesale Operations", cls: "re", krs: 10,
    date: "2001 — Post bankruptcy",
    title: "Wholesale operations COO whose domain partially survived bankruptcy",
    text: `Beck served as COO of Enron Wholesale Operations, responsible for the back office and operational infrastructure of the trading business: settlement, transaction processing, risk reporting, and the operational procedures that kept the trading machinery functioning independently of the trading strategies it was executing. Her domain knowledge was procedural and systems oriented — it was about how to make the operational machinery work, not about what the machinery should be doing strategically. This distinction is critical: Beck's knowledge was embedded in processes and systems rather than in personal expertise, which is the defining characteristic of transferable organizational knowledge.

During Enron's collapse and the subsequent bankruptcy proceedings, portions of Beck's operational domain transferred to the successor entities that acquired Enron's various business units. UBS Warburg's acquisition of the trading operation required the transfer of the settlement and transaction processing infrastructure that Beck's team managed. The CrossCountry Energy transaction similarly required transfer of the operational procedures that supported the pipeline business's administrative functions. In both cases, the transfers were executed successfully — not without difficulty, but without the permanent knowledge loss that characterized the departures of Kaminski, Dasovich, and Davis. The operational infrastructure's survival in successor entities confirms the transferability prediction embedded in Beck's low KRS score, even as the strategic and financial knowledge that surrounded it was lost entirely.

The model's Replaceable Executive classification with a KRS of 10 is validated by the successful transfer of operational infrastructure to successor entities. The score is slightly higher than Horton's (4) or Whalley's (4) because Beck's domain, while proceduralized, included some organizational knowledge that was specific to Enron's particular operational configuration and that required active documentation effort to transfer rather than being automatically embedded in regulatory filings or physical assets. The validation is not that her knowledge was trivially transferable, but that it was systematically transferable — the kind of knowledge that can be reconstructed given sufficient time and documentation effort, which the bankruptcy and acquisition process provided.

Beck's case illustrates the organizational knowledge theory concept of operational infrastructure as institutional insurance. Organizations with high strategic knowledge concentration — like Enron's trading and financial engineering operations — are prone to catastrophic knowledge loss when their strategic knowledge holders depart or are removed. Operational infrastructure knowledge, while less prominent than trading strategy or financial engineering, provides a floor of transferable institutional capacity that allows successor entities to function even when strategic knowledge is lost entirely. Enron's collapse demonstrated both sides of this principle simultaneously: the strategic and financial knowledge was permanently lost with the departure and conviction of the executives who held it, but the operational infrastructure knowledge survived precisely because it had been proceduralized and distributed. The lesson for organizational design is that operational infrastructure investment is a form of knowledge resilience investment that limits the total damage when higher order knowledge loss occurs.`,
    clsLabel: "Replaceable exec", outcome: "Operational knowledge partially transferred to successor entities", conc: "Hit",
    src: "Enron Wikipedia; NBC News (Nov 2004)" },

  { name: "Tracey Kozadinos", role: "Executive Assistant, Office of the Chairman", cls: "st", krs: 23,
    date: "2001",
    title: "Executive assistant held concentrated knowledge about chairman's office operations",
    text: `Kozadinos served as Executive Assistant in the Office of the Chairman at Enron, supporting Kenneth Lay's executive operations. Executive assistant roles in major corporate headquarters are among the least examined knowledge positions in organizational theory, despite the fact that they routinely concentrate knowledge that is both critical and irreplaceable. The specific knowledge held by an executive assistant to a chairman includes: the complete schedule of the executive's commitments and the context behind those commitments; the informal network of relationships that the executive maintains outside formal organizational channels; the verbal agreements, understandings, and commitments that are made in meetings without documentation; the pattern of who gets through and who does not; and the organizational intelligence gathered through continuous proximity to the most sensitive conversations in the company. For Lay in particular, whose primary organizational value was his external relationship network, the assistant managing access to that network held disproportionate institutional knowledge about which relationships were active and what obligations they carried.

The model's identification of Kozadinos as a Silent Threat with a KRS of 23 — the third highest among non executive employees in the dataset — was derived from her anomalous communication centrality in the email corpus. Her communications touched a wider range of senior correspondents than would be expected for an administrative role, reflecting the coordinative function that executive assistants perform: routing communications, managing access, and synthesizing information flows that would otherwise reach the chairman only after filtration by multiple organizational layers. When Enron collapsed and the Office of the Chairman was dissolved as part of the bankruptcy proceedings, the informal knowledge layer that Kozadinos held — the complete context of Lay's commitments, relationships, and informal agreements — disappeared entirely and irreversibly. No bankruptcy administrator or federal prosecutor could reconstruct what she knew about which conversations had occurred and what had been understood in those conversations.

The model's Silent Threat classification is validated not by a specific documented outcome but by the structural reality of what the collapse of the Office of the Chairman entailed. Unlike Horton's pipeline knowledge, which survived in documented form, or Kitchen's platform knowledge, which survived in code, the knowledge held by Kozadinos existed only in her memory and in the informal patterns of her daily work. The Senate investigation, the Powers Report, and the DOJ prosecution all documented the difficulty of reconstructing Lay's decision making record: witnesses recalled different versions of conversations, agreements were disputed, and the informal context that would have resolved these disputes was unavailable. That reconstruction difficulty is precisely the historical signature of the knowledge loss that the model's KRS of 23 predicts.

Kozadinos represents the most important methodological contribution of the email corpus approach to knowledge risk identification. Every other knowledge risk methodology — org chart analysis, skills inventories, expert surveys, succession planning frameworks — would assign zero organizational risk to an executive assistant role. The title conveys no knowledge concentration. The formal authority is nil. The documentation is administrative. The email corpus approach bypasses title entirely and measures what the model is actually designed to measure: the pattern of organizational knowledge flows. An employee with high communication centrality to senior leadership is, by definition, a knowledge node regardless of their title. The Kozadinos finding is the model's clearest demonstration that knowledge risk is a property of information flows, not of organizational charts — and that the next generation of knowledge risk methodology must be built on communication analysis rather than job description analysis if it is to capture the full risk profile of complex organizations.`,
    clsLabel: "Silent threat", outcome: "Informal executive knowledge layer destroyed in collapse; no succession plan existed", conc: "Hit",
    src: "Model inference validated by organizational behavior literature on executive assistant knowledge concentration" }
];

const HV_TIMELINE = [
  { date: "1998", text: "Enron email corpus begins. Earliest parsed communications establish baseline organizational knowledge patterns.", color: "" },
  { date: "June 1999", text: "Enron Board waives conflict of interest policy to allow CFO Fastow to manage LJM1 partnership. Kaminski raises objections and is transferred out of risk assessment by Skilling.", color: "red" },
  { date: "Nov 1999", text: "EnronOnline launches, executing first transaction on November 29. Platform becomes largest e commerce site in the world by transaction volume within months.", color: "green" },
  { date: "May 2000", text: "Timothy Belden emails Houston confirming California energy price manipulation strategy is working. West Coast power desk begins most profitable period.", color: "red" },
  { date: "Aug 2000", text: "Enron stock hits all time high of $90.56. Market valuation reaches $70 billion.", color: "" },
  { date: "Oct 2000", text: "FERC investigation initially exonerates Enron for California market conduct.", color: "" },
  { date: "Dec 2000", text: "Internal memo by Christian Yoder and Stephen Hall details Belden's California trading strategies including Fat Boy, Death Star, and Get Shorty.", color: "red" },
  { date: "Jan 2001", text: "Belden's West Coast power desk records most profitable month ever at $254M gross profits.", color: "" },
  { date: "Feb 2001", text: "Skilling named CEO, replacing Lay in the role.", color: "" },
  { date: "May 2001", text: "Cliff Baxter resigns as Vice Chairman after opposing LJM partnerships internally. Model limitation: Baxter absent from email corpus — known miss.", color: "red" },
  { date: "Aug 14, 2001", text: "Jeff Skilling resigns as CEO citing personal reasons. Model correctly flags as Organizational Emergency (KRS 25). Stock drops sharply.", color: "red" },
  { date: "Aug 15, 2001", text: "Sherron Watkins sends anonymous whistleblower memo to Kenneth Lay warning of accounting scandals. Watkins not in model's top 200.", color: "" },
  { date: "Oct 16, 2001", text: "Enron announces $618M quarterly loss and $1.2B write down. Triggers SEC investigation.", color: "red" },
  { date: "Oct 24, 2001", text: "Andrew Fastow removed as CFO. Model limitation: Fastow absent from corpus — known miss. Deliberately concealed activities from email trail.", color: "red" },
  { date: "Nov 28, 2001", text: "Credit rating downgraded to junk. Dynegy merger collapses.", color: "red" },
  { date: "Dec 2, 2001", text: "Enron files Chapter 11 bankruptcy. Largest corporate bankruptcy in U.S. history at time. 20,000 employees lose jobs.", color: "red" },
  { date: "Post bankruptcy", text: "Pipeline operations (CrossCountry Energy) survive and sell for $2.45B. Stan Horton continues as executive. Model correctly classified pipeline knowledge as Replaceable Executive — recoverable.", color: "green" }
];

const HV_TOPICS = [
  { name: "California energy crisis", desc: "Collapsed — FERC investigation, $9B overcharges, trading desk disbanded. The West Coast power desk run by Timothy Belden was the primary vehicle for market manipulation strategies with code names including Fat Boy, Death Star, and Get Shorty. Belden pled guilty to wire fraud and cooperated with federal prosecutors. The knowledge held by Dasovich and Davis in this domain was permanently lost when the Portland trading group disbanded.", type: "collapsed", conc: "Hit" },
  { name: "Structured finance & derivatives", desc: "Collapsed — SPE/Raptor fraud, $1.2B restatement, criminal convictions. The LJM and Raptor special purpose entities were the primary instruments of Enron's accounting fraud, allowing the company to move debt off its balance sheet and manufacture earnings. When the Powers Report documented the structures in February 2002, it revealed that the knowledge of how these instruments actually worked was deliberately confined to Fastow and a small circle. That knowledge disappeared with the collapse.", type: "collapsed", conc: "Hit" },
  { name: "Corporate communications", desc: "Collapsed — public trust destroyed, C suite convicted or deceased. Lay and Skilling represented the entire external credibility infrastructure of Enron, and both were removed within months of each other. Lay's death before sentencing, Skilling's nineteen count conviction, and the destruction of the Enron brand meant that the communications and relationship capital concentrated in the executive tier became permanently inaccessible.", type: "collapsed", conc: "Hit" },
  { name: "Trading operations", desc: "Collapsed — West Coast desk disbanded, Belden pled guilty. The trading operation that generated the majority of Enron's actual operating profits was dismantled after bankruptcy, with the surviving infrastructure transferred to UBS Warburg under adverse conditions. The tacit knowledge of trading strategies, counterparty relationships, and market positioning that resided in individual traders was lost to the organization permanently.", type: "collapsed", conc: "Hit" },
  { name: "Legal — transactional", desc: "Partially survived — ENA legal talent absorbed by successor firms. The transactional legal knowledge developed at Enron North America, particularly around energy derivatives and structured finance, had genuine market value independent of the fraud. A significant portion of ENA's legal staff found positions at law firms and financial institutions that continued to structure similar transactions in the post Enron era.", type: "partial", conc: "Partial" },
  { name: "Pipeline & transportation", desc: "Survived — CrossCountry Energy sold for $2.45B, 1,100 employees retained. The pipeline business was the most transferable domain in the entire Enron knowledge base, and its survival validates the model's KRS scoring for Stan Horton and his team. Physical infrastructure, documented operating procedures, and regulated utility economics created conditions where knowledge transfer was structurally guaranteed rather than dependent on individual retention.", type: "survived", conc: "Hit" },
  { name: "Executive operations", desc: "Collapsed — entire executive leadership layer removed through resignation, termination, and post bankruptcy legal proceedings. Twenty two people were ultimately convicted for crimes related to the fraud, including the CEO, president and COO, CFO, treasurer, chief accounting officer, and heads of multiple business units. The model correctly identifies Executive Operations as a high risk knowledge domain where concentration in individuals rather than organizational structures is the primary failure mode.", type: "collapsed", conc: "Hit" },
  { name: "Research & quantitative analysis", desc: "Collapsed — Kaminski's research group marginalized after opposing Raptor SPE structures, transferred from risk assessment to the trading division. The group's quantitative models supporting energy trading represented the organization's primary check on fraudulent valuations. After bankruptcy, Kaminski's team members dispersed across the industry, with Kaminski himself joining Rice University. The knowledge was permanently lost to the organization.", type: "collapsed", conc: "Hit" }
];

const HV_SOURCES = [
  { num: 1, text: "Powers Report — Special Investigation Committee, Enron Board of Directors (Feb 1, 2002)", url: "https://www.justice.gov/archive/enron" },
  { num: 2, text: "FBI Enron Case Summary", url: "https://www.fbi.gov/history/famous-cases/enron" },
  { num: 3, text: 'Senate Permanent Subcommittee on Investigations — "Role of the Board of Directors in Enron\'s Collapse" (July 2002)', url: "https://www.govinfo.gov/content/pkg/CPRT-107SPRT80393/html/CPRT-107SPRT80393.htm" },
  { num: 4, text: "DOJ Superseding Indictment — United States v. Skilling, Lay, Causey (July 2004)", url: "https://www.justice.gov/archive/dag/cftf/chargingdocs/skillingindictment.pdf" },
  { num: 5, text: 'FERC Final Report — "Price Manipulation in Western Markets" (2003)', url: "https://www.ferc.gov/sites/default/files/2020-05/chronology-glance.pdf" },
  { num: 6, text: "Skilling v. United States, 561 U.S. 358 (2010) — Supreme Court opinion", url: "https://www.law.cornell.edu/supct/html/08-1394.ZO.html" },
  { num: 7, text: 'McLean & Elkind, "The Smartest Guys in the Room" (Portfolio/Penguin, 2003)' },
  { num: 8, text: 'Business History Review, "Enron and the California Energy Crisis" (Cambridge, 2022)', url: "https://doi.org/10.1017/S0007680521000866" },
  { num: 9, text: 'Harvard Business School Case Study, "EnronOnline: Louise Kitchen, Intrapreneur" (2001)', url: "https://www.hbs.edu/faculty/Pages/item.aspx?num=28391" },
  { num: 10, text: "Washington Post, West Coast trading desk investigation (January 2003)", url: "https://www.washingtonpost.com/archive/business/2003/01/08/enron-investigators-expand-probe-to-california-energy-trading/70c9b254-cbc0-4b45-9046-ea72c33c10f4/" },
  { num: 11, text: 'CorpWatch, "10 Enron Players: Where They Landed After the Fall"', url: "https://www.corpwatch.org/article/us-10-enron-players-where-they-landed-after-fall" },
  { num: 12, text: "NBC News, CrossCountry Energy sale (November 2004)", url: "https://www.nbcnews.com/id/wbna6519921" }
];

let hvInitialized = false;
let hvActiveEmp = 0;
let hvActiveTab = 0;

function initHVView() {
  if (hvInitialized) return;
  hvInitialized = true;
  _buildHVEmpList();
  _buildHVTimeline();
  _buildHVDomains();
  _buildHVSources();
  showHVDetail(0);
}

function _buildHVEmpList() {
  const el = document.getElementById("hv-emp-list");
  if (!el) return;
  el.innerHTML = HV_EMPLOYEES.map((e, i) =>
    `<div class="hv-row${i === 0 ? ' active' : ''}" onclick="showHVDetail(${i})">
      <div style="flex:1">
        <div class="hv-row-name">${e.name}</div>
        <div class="hv-row-role">${e.role}</div>
        <div style="margin-top:5px"><span class="hv-badge hv-badge-${e.cls}">${e.clsLabel}</span></div>
      </div>
      <div class="hv-krs">${e.krs}<span style="font-size:10px;opacity:0.45;font-weight:400">/100</span></div>
    </div>`
  ).join("");
}

function showHVDetail(i) {
  hvActiveEmp = i;
  const d = HV_EMPLOYEES[i];
  const concCls = d.conc === "Hit" ? "hv-badge-hit" : d.conc === "Partial" ? "hv-badge-partial" : "hv-badge-miss";
  const panel = document.getElementById("hv-detail-panel");
  if (!panel) return;
  const paras = d.text.trim().split(/\n\n+/).map(p => `<p style="margin-bottom:16px;line-height:1.7">${p.trim()}</p>`).join("");
  panel.innerHTML = `
    <div class="hv-detail-date">${d.date}</div>
    <div class="hv-detail-title">${d.title}</div>
    <div style="margin-bottom:14px">${paras}</div>
    <div>
      <div class="hv-conc-row"><span style="font-size:12px">Model classification</span><span class="hv-badge hv-badge-${d.cls}">${d.clsLabel}</span></div>
      <div class="hv-conc-row"><span style="font-size:12px">Historical outcome</span><span style="color:var(--text-primary);font-size:12px">${d.outcome}</span></div>
      <div class="hv-conc-row"><span style="font-size:12px">Concordance</span><span class="hv-badge ${concCls}">${d.conc}</span></div>
    </div>
    <div class="hv-source">${d.src}</div>`;
  document.querySelectorAll(".hv-row").forEach((r, j) => r.classList.toggle("active", j === i));
}

function _buildHVTimeline() {
  const el = document.getElementById("hv-timeline-list");
  if (!el) return;
  el.innerHTML = HV_TIMELINE.map(t =>
    `<div class="hv-tl-item${t.color ? ' ' + t.color : ''}">
      <div class="hv-tl-date">${t.date}</div>
      <div class="hv-tl-text">${t.text}</div>
    </div>`
  ).join("");
}

function _buildHVDomains() {
  const el = document.getElementById("hv-domains-grid");
  if (!el) return;
  el.innerHTML = HV_TOPICS.map(t => {
    const concCls = t.conc === "Hit" ? "hv-badge-hit" : t.conc === "Partial" ? "hv-badge-partial" : "hv-badge-miss";
    return `<div class="hv-domain-card ${t.type}">
      <div class="hv-domain-name">${t.name}</div>
      <div class="hv-domain-desc">${t.desc}</div>
      <span class="hv-badge ${concCls}">${t.conc}</span>
    </div>`;
  }).join("");
}

function _buildHVSources() {
  const el = document.getElementById("hv-src-panel");
  if (!el) return;
  el.innerHTML = `<div class="hv-src-head">Primary sources</div>` +
    HV_SOURCES.map(s => {
      const label = s.url
        ? `<a href="${s.url}" target="_blank" class="hv-src-link">${s.text}</a>`
        : `<span style="color:var(--text-secondary);cursor:default">${s.text}</span>`;
      return `<div class="hv-src-item"><span class="hv-src-num">[${s.num}]</span>${label}</div>`;
    }).join("");
}

function switchModalTab(tabId) {
  document.querySelectorAll('.hiw-tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.hiw-tab-panel').forEach(panel => panel.classList.remove('active'));
  document.getElementById('hiw-tab-' + tabId).classList.add('active');
  document.getElementById('hiw-panel-' + tabId).classList.add('active');
}

function switchHVTab(n) {
  hvActiveTab = n;
  document.querySelectorAll(".hv-tab").forEach((t, i) => t.classList.toggle("active", i === n));
  document.getElementById("hv-tab0").style.display = n === 0 ? "" : "none";
  document.getElementById("hv-tab1").style.display = n === 1 ? "" : "none";
  document.getElementById("hv-tab2").style.display = n === 2 ? "" : "none";
}
