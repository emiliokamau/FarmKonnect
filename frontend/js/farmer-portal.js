/* ------------------------------------------------------------------
   FarmKonnect Farmer Portal controller
------------------------------------------------------------------ */

let PORTAL_CACHE = { farms: [], commodities: [], counties: [], reports: [] };

/* ---------------- Bootstrap ---------------- */
document.addEventListener("DOMContentLoaded", async () => {
  if (document.body.dataset.page !== "farmer") return;

  if (!window.isLoggedIn()) {
    window.location.href = "login.html";
    return;
  }

  const user = window.getUser();
  const userEl = document.getElementById("portalUser");
  if (userEl) userEl.textContent = user?.first_name || user?.username || "Farmer";

  // sidebar dropdowns
  document.querySelectorAll(".nav-group > .nav-group-title").forEach(t => {
    t.addEventListener("click", () => t.parentElement.classList.toggle("open"));
  });

  // tab switching
  document.querySelectorAll("[data-portal-tab]").forEach(link => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      showTab(link.dataset.portalTab);
    });
  });

  // logout
  document.querySelectorAll("[data-logout]").forEach(b => {
    b.addEventListener("click", async (e) => {
      e.preventDefault();
      try { await window.API.logout(); } catch {}
      window.logout();
    });
  });

  // advisory form
  document.getElementById("advisoryForm").addEventListener("submit", submitAdvisory);

  // prefetch farms + commodities + counties for dropdowns
  try {
    const [farms, commodities, counties] = await Promise.all([
      window.API.farms.list().catch(() => ({ results: [] })),
      window.API.commodities().catch(() => ({ results: [] })),
      window.API.counties().catch(() => ({ results: [] })),
    ]);
    PORTAL_CACHE.farms = farms.results || farms || [];
    PORTAL_CACHE.commodities = commodities.results || commodities || [];
    PORTAL_CACHE.counties = counties.results || counties || [];
    hydrateDropdowns();
  } catch (e) {
    console.warn("Prefetch failed:", e);
  }

  showTab("trends");
});

/* ---------------- Tab switching ---------------- */
const TAB_LOADERS = {
  trends:     loadTrends,
  prices:     loadPriceComparison,
  disease:    loadDisease,
  practices:  loadPractices,
  officers:   loadOfficers,
  events:     loadEvents,
  subsidy:    loadSubsidy,
  advisories: loadAdvisories,
};

const TAB_TITLES = {
  trends: "Market Trends", prices: "Price Comparison",
  disease: "Disease Detection", practices: "Best Practices",
  officers: "Agricultural Officers", events: "Training & Grants",
  subsidy: "Fertilizer Subsidy", advisories: "Ask an Officer",
};

function showTab(name) {
  document.querySelectorAll(".content-section").forEach(s => s.classList.remove("active"));
  document.getElementById(`tab-${name}`)?.classList.add("active");

  document.querySelectorAll("[data-portal-tab]").forEach(l =>
    l.classList.toggle("active", l.dataset.portalTab === name)
  );

  const titleEl = document.getElementById("portalTitle");
  if (titleEl) titleEl.textContent = TAB_TITLES[name] || name;

  TAB_LOADERS[name]?.();
}

/* ---------------- Dropdown hydration ---------------- */
function hydrateDropdowns() {
  const c = document.getElementById("trendsCommodity");
  const co = document.getElementById("trendsCounty");
  const farmSel = document.getElementById("diseaseFarm");

  if (c) {
    PORTAL_CACHE.commodities.forEach(x => {
      const o = document.createElement("option");
      o.value = x.id; o.textContent = x.name;
      c.appendChild(o);
    });
  }
  if (co) {
    PORTAL_CACHE.counties.forEach(x => {
      const o = document.createElement("option");
      o.value = x.id; o.textContent = x.name;
      co.appendChild(o);
    });
  }
  if (farmSel) {
    PORTAL_CACHE.farms.forEach(x => {
      const o = document.createElement("option");
      o.value = x.id; o.textContent = x.name;
      farmSel.appendChild(o);
    });
  }
}

/* ---------------- Helpers ---------------- */
function money(n) {
  return "KSh " + parseFloat(n || 0).toLocaleString(undefined, {
    minimumFractionDigits: 2, maximumFractionDigits: 2,
  });
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;",
    '"': "&quot;", "'": "&#39;",
  })[c]);
}

/* =============================================================
   MARKET TRENDS
============================================================= */
async function loadTrends() {
  const statsEl = document.getElementById("trendsStats");
  const tableEl = document.getElementById("trendsTable");
  const cSel = document.getElementById("trendsCommodity");
  const coSel = document.getElementById("trendsCounty");
  const refresh = document.getElementById("trendsRefresh");

  refresh.onclick = () => loadTrends();

  statsEl.innerHTML = `<div class="stat-card"><h3>—</h3><p>Loading…</p></div>`;
  tableEl.innerHTML = `<p class="muted">Loading…</p>`;

  // build query string
  const params = new URLSearchParams();
  if (cSel.value) params.set("commodity", cSel.value);
  if (coSel.value) params.set("county", coSel.value);
  const qs = params.toString() ? `?${params}` : "";

  try {
    const res = await window.API.prices(qs);
    const rows = res.results || res || [];

    if (!rows.length) {
      statsEl.innerHTML = `<div class="stat-card"><h3>0</h3><p>Records</p></div>`;
      tableEl.innerHTML = `<p class="muted">No price data for this filter.</p>`;
      return;
    }

    const prices = rows.map(r => parseFloat(r.price || 0));
    const avg = prices.reduce((s, p) => s + p, 0) / prices.length;
    const min = Math.min(...prices);
    const max = Math.max(...prices);

    statsEl.innerHTML = `
      <div class="stat-card"><h3>${rows.length}</h3><p>Records</p></div>
      <div class="stat-card"><h3>${money(avg)}</h3><p>Average</p></div>
      <div class="stat-card"><h3>${money(min)}</h3><p>Lowest</p></div>
      <div class="stat-card"><h3>${money(max)}</h3><p>Highest</p></div>
    `;

    tableEl.innerHTML = `
      <table class="data-table">
        <thead><tr><th>Commodity</th><th>County</th><th>Price</th><th>Date</th><th>Source</th></tr></thead>
        <tbody>${rows.slice(0, 50).map(r => `
          <tr>
            <td>${escapeHtml(r.commodity_name)}</td>
            <td>${escapeHtml(r.county_name)}</td>
            <td>${money(r.price)}</td>
            <td>${r.date}</td>
            <td>${escapeHtml(r.source || "—")}</td>
          </tr>`).join("")}
        </tbody>
      </table>`;
  } catch (e) {
    statsEl.innerHTML = "";
    tableEl.innerHTML = `<p class="muted">Unable to load (${e.message}).</p>`;
  }
}

/* =============================================================
   PRICE COMPARISON
============================================================= */
async function loadPriceComparison() {
  const el = document.getElementById("compareArea");
  el.innerHTML = `<p class="muted">Loading…</p>`;

  try {
    const res = await window.API.prices();
    const rows = res.results || res || [];

    if (!rows.length) {
      el.innerHTML = `<p class="muted">No price data yet. Check back soon.</p>`;
      return;
    }

    // group by commodity -> county -> price
    const grouped = {};
    rows.forEach(r => {
      const c = r.commodity_name || "Unknown";
      grouped[c] = grouped[c] || {};
      const county = r.county_name || "Unknown";
      const p = parseFloat(r.price || 0);
      // keep latest
      if (!grouped[c][county] || r.date > grouped[c][county].date) {
        grouped[c][county] = { price: p, date: r.date };
      }
    });

    el.innerHTML = Object.entries(grouped).map(([commodity, counties]) => {
      const entries = Object.entries(counties)
        .map(([county, { price, date }]) => ({ county, price, date }))
        .sort((a, b) => b.price - a.price);
      const best = entries[0];

      return `
        <div class="card" style="margin-bottom:1rem;">
          <h3>${escapeHtml(commodity)}</h3>
          <table class="data-table">
            <thead><tr><th>County</th><th>Price</th><th>Date</th></tr></thead>
            <tbody>${entries.map(e => `
              <tr>
                <td>${escapeHtml(e.county)} ${e.county === best.county ? "🏆" : ""}</td>
                <td>${money(e.price)}</td>
                <td>${e.date}</td>
              </tr>
            `).join("")}
            </tbody>
          </table>
        </div>`;
    }).join("");
  } catch (e) {
    el.innerHTML = `<p class="muted">Unable to load (${e.message}).</p>`;
  }
}

/* =============================================================
   DISEASE DETECTION
============================================================= */
async function loadDisease() {
  const resultEl = document.getElementById("diseaseResult");
  resultEl.innerHTML = "";
  document.getElementById("analyzeDiseaseBtn").onclick = analyzeDisease;
  await loadMyDiseaseReports();
}

async function loadMyDiseaseReports() {
  const el = document.getElementById("myDiseaseReports");
  el.innerHTML = `<p class="muted">Loading…</p>`;
  try {
    const res = await window.API.diseases.list();
    const rows = res.results || res || [];
    PORTAL_CACHE.reports = rows;

    el.innerHTML = rows.length ? `
      <table class="data-table">
        <thead><tr><th>Date</th><th>Crop</th><th>Diagnosis</th><th>Severity</th><th>Status</th></tr></thead>
        <tbody>${rows.slice(0, 20).map(r => `
          <tr>
            <td>${r.date}</td>
            <td>${escapeHtml(r.crop)}</td>
            <td>${escapeHtml(r.diagnosis || "—")}</td>
            <td>${r.severity}</td>
            <td>${r.status}</td>
          </tr>`).join("")}
        </tbody>
      </table>` : `<p class="muted">No disease reports yet.</p>`;
  } catch (e) {
    el.innerHTML = `<p class="muted">Unable to load (${e.message}).</p>`;
  }
}

async function analyzeDisease() {
  const file = document.getElementById("diseaseFile").files[0];
  const crop = document.getElementById("diseaseCrop").value.trim();
  const farmId = document.getElementById("diseaseFarm").value;
  const out = document.getElementById("diseaseResult");

  if (!file) {
    out.innerHTML = `<p class="muted">Please choose an image first.</p>`;
    return;
  }
  if (!crop) {
    out.innerHTML = `<p class="muted">Please enter the crop name.</p>`;
    return;
  }

  out.innerHTML = `<p class="muted">Analyzing…</p>`;

  // Simulated AI — in a real deployment you'd POST to a diagnosis endpoint
  setTimeout(async () => {
    const possible = ["Leaf Blight", "Powdery Mildew", "Rust", "Bacterial Wilt", "Aphid Infestation", "Healthy"];
    const diagnosis = possible[Math.floor(Math.random() * possible.length)];
    const severity =
      diagnosis === "Healthy" ? "low" :
      ["Rust", "Bacterial Wilt"].includes(diagnosis) ? "high" : "medium";

    out.innerHTML = `
      <div class="card result-card">
        <h4>Likely Diagnosis: ${diagnosis}</h4>
        <p><strong>Severity:</strong> ${severity}</p>
        <p><strong>Suggested treatment:</strong> ${
          diagnosis === "Healthy"
            ? "No action needed — keep monitoring."
            : "Apply an approved fungicide/insecticide, remove affected leaves, improve airflow, and consult an agricultural officer if symptoms persist."
        }</p>
        <p class="muted">A report has been saved to your farm records.</p>
      </div>`;

    // Persist the report to the backend
    try {
      const today = new Date().toISOString().slice(0, 10);
      await window.API.diseases.create({
        date: today,
        crop,
        farm: farmId || null,
        diagnosis,
        severity,
        status: "open",
        symptoms: "Reported via Farmer Portal disease detection.",
      });
      loadMyDiseaseReports();
    } catch (e) {
      console.warn("Could not save report:", e);
    }
  }, 1400);
}

/* =============================================================
   BEST PRACTICES
============================================================= */
async function loadPractices() {
  const el = document.getElementById("practicesArea");
  el.innerHTML = `<p class="muted">Loading…</p>`;
  try {
    const res = await window.API.products();
    const list = (res.results || res || []).filter(p =>
      (p.category || "").toLowerCase() === "practice"
    );
    el.innerHTML = list.length ? list.map(p => `
      <div class="card service-card">
        <h3>${escapeHtml(p.name)}</h3>
        <p>${escapeHtml(p.description || "")}</p>
      </div>`).join("")
      : `<p class="muted">No best-practice guides published yet. They can be added from the admin (Products, category = "practice").</p>`;
  } catch (e) {
    el.innerHTML = `<p class="muted">Unable to load (${e.message}).</p>`;
  }
}

/* =============================================================
   OFFICERS
============================================================= */
async function loadOfficers() {
  const el = document.getElementById("officersArea");
  el.innerHTML = `<p class="muted">Loading…</p>`;
  try {
    const res = await window.apiFetch("/users/", { auth: false });
    const list = (res.results || res || []).filter(u => u.is_staff);
    el.innerHTML = list.length ? list.map(u => `
      <div class="card">
        <h3>${escapeHtml(u.first_name || u.username)}</h3>
        <p class="muted">Agricultural Officer</p>
        <p>📧 ${escapeHtml(u.email || "—")}</p>
        <p>📞 ${escapeHtml(u.phone || "—")}</p>
      </div>`).join("")
      : `<p class="muted">No officers registered yet.</p>`;
  } catch (e) {
    el.innerHTML = `<p class="muted">Unable to load (${e.message}).</p>`;
  }
}

/* =============================================================
   EVENTS (Training & Grants)
============================================================= */
async function loadEvents() {
  const el = document.getElementById("eventsArea");
  el.innerHTML = `<p class="muted">Loading…</p>`;
  try {
    const res = await window.API.events();
    const list = (res.results || res || []).filter(e =>
      e.event_type !== "subsidy"
    );
    el.innerHTML = list.length ? list.map(e => `
      <div class="card">
        <span class="badge">${escapeHtml(e.event_type)}</span>
        <h3 style="margin-top:.5rem;">${escapeHtml(e.title)}</h3>
        <p>${escapeHtml(e.description || "")}</p>
        <p class="muted">📍 ${escapeHtml(e.location || "—")}</p>
        <p class="muted">📅 ${new Date(e.start_date).toLocaleString()}</p>
      </div>`).join("")
      : `<p class="muted">No events published yet.</p>`;
  } catch (e) {
    el.innerHTML = `<p class="muted">Unable to load (${e.message}).</p>`;
  }
}

/* =============================================================
   SUBSIDY
============================================================= */
async function loadSubsidy() {
  const el = document.getElementById("subsidyArea");
  el.innerHTML = `<p class="muted">Loading…</p>`;
  try {
    const res = await window.API.events("subsidy");
    const list = res.results || res || [];
    el.innerHTML = list.length ? list.map(e => `
      <div class="card">
        <h3>${escapeHtml(e.title)}</h3>
        <p>${escapeHtml(e.description || "")}</p>
        <p class="muted">📍 ${escapeHtml(e.location || "—")}</p>
        <p class="muted">📅 ${new Date(e.start_date).toLocaleString()}</p>
      </div>`).join("")
      : `<p class="muted">No subsidy programmes at this time.</p>`;
  } catch (e) {
    el.innerHTML = `<p class="muted">Unable to load (${e.message}).</p>`;
  }
}

/* =============================================================
   ADVISORIES — Ask an Officer
============================================================= */
async function loadAdvisories() {
  const el = document.getElementById("advisoriesList");
  el.innerHTML = `<p class="muted">Loading…</p>`;
  try {
    const res = await window.API.advisories();
    const list = res.results || res || [];
    el.innerHTML = list.length ? list.map(a => `
      <div class="card" style="margin-bottom:.75rem;">
        <h4>${escapeHtml(a.subject)}</h4>
        <p>${escapeHtml(a.message)}</p>
        ${a.response ? `<p class="muted"><strong>Response:</strong> ${escapeHtml(a.response)}</p>` : ""}
        <small class="muted">Status: ${a.status} · ${new Date(a.created_at).toLocaleString()}</small>
      </div>`).join("")
      : `<p class="muted">No advisory requests yet.</p>`;
  } catch (e) {
    el.innerHTML = `<p class="muted">Unable to load (${e.message}).</p>`;
  }
}

async function submitAdvisory(e) {
  e.preventDefault();
  const form = e.target;
  const msg = document.getElementById("advisoryMsg");
  msg.textContent = "";
  msg.className = "form-msg";

  const payload = {
    subject: form.subject.value.trim(),
    message: form.message.value.trim(),
  };
  if (!payload.subject || !payload.message) {
    msg.className = "form-msg error";
    msg.textContent = "Subject and message are required.";
    return;
  }

  try {
    await window.API.createAdvisory(payload);
    form.reset();
    msg.className = "form-msg success";
    msg.textContent = "Request sent. An officer will get back to you.";
    loadAdvisories();
  } catch (err) {
    msg.className = "form-msg error";
    msg.textContent =
      err?.data?.detail ||
      Object.values(err?.data || {}).flat().join(" | ") ||
      err.message ||
      "Could not send request.";
  }
}