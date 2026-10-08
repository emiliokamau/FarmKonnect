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

  // Photo picker: camera capture, gallery or drag-and-drop, with previews.
  const host = document.getElementById("diseaseImagePicker");
  if (host && !window.__diseasePicker) {
    window.__diseasePicker = window.ImagePicker.mount(host, {
      label: "Photos of the affected plant",
      multiple: true,
      max: 5,
      stages: window.ImagePicker.DISEASE_STAGES,
      help: "Up to 5 photos: a close-up of the affected part, the whole plant, and the wider field. " +
            "Photos are shrunk on your phone before sending, so they upload faster.",
      onChange: ({ message, kind }) => {
        const note = document.getElementById("diseaseResult");
        if (kind === "error") note.innerHTML = `<p class="muted">${escapeHtml(message)}</p>`;
      },
    });
  }

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
        <thead><tr>
          <th>Photo</th><th>Date</th><th>Crop</th><th>Diagnosis</th>
          <th>Severity</th><th>Status</th><th></th>
        </tr></thead>
        <tbody>${rows.slice(0, 20).map(r => `
          <tr>
            <td class="thumb-cell">${reportThumb(r)}</td>
            <td>${escapeHtml(r.date)}</td>
            <td>${escapeHtml(r.crop)}</td>
            <td>${r.diagnosis
                  ? escapeHtml(r.diagnosis)
                  : `<span class="badge badge-pending">Awaiting review</span>`}</td>
            <td>${escapeHtml(r.severity)}</td>
            <td>${escapeHtml(r.status)}</td>
            <td>${r.image_src
                  ? `<button class="btn-outline" data-view-report="${r.id}"
                       style="padding:.25rem .6rem;font-size:.78rem;">View</button>`
                  : ""}</td>
          </tr>`).join("")}
        </tbody>
      </table>` : `<p class="muted">No disease reports yet.</p>`;

    el.querySelectorAll("[data-view-report]").forEach(b => {
      b.addEventListener("click", () => {
        const row = rows.find(x => String(x.id) === String(b.dataset.viewReport));
        if (row) showReportPhotos(row);
      });
    });
  } catch (e) {
    el.innerHTML = `<p class="muted">Unable to load (${e.message}).</p>`;
  }
}

/* Thumbnail for a report row, with a count badge when several photos exist. */
function reportThumb(report) {
  const src = report.image_src;
  if (!src) return `<span class="muted">—</span>`;
  const extra = report.photo_count > 1 ? `<span class="thumb-count">+${report.photo_count - 1}</span>` : "";
  return `<span class="thumb-wrap">
            <img src="${escapeHtml(src)}" alt="${escapeHtml(report.crop)} photo" loading="lazy">
            ${extra}
          </span>`;
}

/* Full set of photos for one report, opened in a lightbox. */
function showReportPhotos(report) {
  const photos = [report.image_src, ...(report.photos || []).map(p => p.image_src)].filter(Boolean);
  if (!photos.length) return;

  const backdrop = document.createElement("div");
  backdrop.className = "modal-backdrop";
  backdrop.style.cssText =
    "position:fixed;inset:0;background:rgba(0,0,0,.72);display:flex;align-items:center;" +
    "justify-content:center;z-index:120;padding:1rem;";
  backdrop.innerHTML = `
    <div style="background:#fff;border-radius:12px;max-width:820px;width:100%;max-height:92vh;overflow-y:auto;padding:1.25rem;">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:1rem;">
        <h3 style="margin:0;">${escapeHtml(report.crop)} — ${photos.length} photo${photos.length === 1 ? "" : "s"}</h3>
        <button class="btn-outline" id="closeReportPhotos" style="padding:.35rem .8rem;">Close</button>
      </div>
      <p class="muted" style="margin:.5rem 0 1rem;">
        ${escapeHtml(report.diagnosis || "Awaiting review")}
        ${report.treatment ? `· ${escapeHtml(report.treatment)}` : ""}
      </p>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:.75rem;">
        ${photos.map((src, i) => {
          const stage = i === 0
            ? (report.photo_stage_display || "")
            : ((report.photos[i - 1] || {}).photo_stage || "");
          return `<figure style="margin:0;">
            <img src="${escapeHtml(src)}" alt="report photo ${i + 1}" loading="lazy"
                 style="width:100%;border-radius:10px;border:1px solid var(--border);">
            ${stage ? `<figcaption class="muted" style="font-size:.8rem;">${escapeHtml(stage)}</figcaption>` : ""}
          </figure>`;
        }).join("")}
      </div>
    </div>`;
  document.body.appendChild(backdrop);
  const close = () => backdrop.remove();
  backdrop.querySelector("#closeReportPhotos").addEventListener("click", close);
  backdrop.addEventListener("click", e => { if (e.target === backdrop) close(); });
  document.addEventListener("keydown", function esc(e) {
    if (e.key === "Escape") { close(); document.removeEventListener("keydown", esc); }
  });
}

async function analyzeDisease() {
  const out = document.getElementById("diseaseResult");
  const crop = document.getElementById("diseaseCrop").value.trim();
  const variety = document.getElementById("diseaseVariety").value.trim();
  const growth = document.getElementById("diseaseGrowth").value.trim();
  const affected = document.getElementById("diseaseAffected").value.trim();
  const symptoms = document.getElementById("diseaseSymptoms").value.trim();
  const farmId = document.getElementById("diseaseFarm").value;
  const wantsAnalysis = document.getElementById("diseaseRequestAnalysis").checked;
  const picker = window.__diseasePicker;

  if (!crop) {
    out.innerHTML = `<p class="muted">Please enter the crop name.</p>`;
    return;
  }
  if (!picker || !picker.hasFiles()) {
    out.innerHTML = `<p class="muted">Please add at least one photo of the affected plant.</p>`;
    return;
  }

  const btn = document.getElementById("analyzeDiseaseBtn");
  btn.disabled = true;
  out.innerHTML = `<p class="muted">Uploading ${picker.files().length} photo(s)…</p>`;

  try {
    const today = new Date().toISOString().slice(0, 10);

    // Photos are stored first, so the report is never saved without its evidence.
    const fd = new FormData();
    fd.append("date", today);
    fd.append("crop", crop);
    fd.append("variety", variety);
    fd.append("growth_stage", growth);
    fd.append("affected_area", affected);
    fd.append("symptoms", symptoms || "Reported via Farmer Portal disease detection.");
    fd.append("status", "open");
    if (farmId) fd.append("farm", farmId);
    if (wantsAnalysis) fd.append("needs_analysis", "true");
    picker.appendTo(fd, "image", "images");

    const report = await window.API.diseases.create(fd);

    // Any extra angles beyond the first go on as additional photos.
    const extras = picker.files().slice(1);
    if (extras.length) {
      const extraFd = new FormData();
      const stages = picker.selections.map(s => s.stage).slice(1);
      extras.forEach(f => extraFd.append("images", f));
      stages.forEach(s => extraFd.append("photo_stage", s || ""));
      try {
        await window.API.addDiseasePhotos(report.id, extraFd);
      } catch (e) {
        console.warn("Extra photos were not saved:", e);
      }
    }

    if (wantsAnalysis && report.id) {
      try { await window.API.analyseDisease(report.id); } catch (e) { console.warn(e); }
    }

    out.innerHTML = `
      <div class="card result-card">
        <h4>Photos received — report #${report.id}</h4>
        <p><strong>Crop:</strong> ${escapeHtml(crop)}${variety ? ` (${escapeHtml(variety)})` : ""}</p>
        <p><strong>Photos attached:</strong> ${extras.length + 1}</p>
        <p>${wantsAnalysis
              ? "An agricultural officer or the diagnosis service will review the photos and record a diagnosis. " +
                "You can see the outcome under <em>My Recent Reports</em>."
              : "Saved to your farm records."}</p>
      </div>`;

    if (picker.clear) picker.clear();
    ["diseaseVariety", "diseaseGrowth", "diseaseAffected", "diseaseSymptoms"].forEach(id => {
      const f = document.getElementById(id);
      if (f) f.value = "";
    });
    loadMyDiseaseReports();
  } catch (e) {
    const detail = e?.data
      ? Object.entries(e.data).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : v}`).join(" | ")
      : e.message;
    out.innerHTML = `<p class="muted">Could not save the report — ${escapeHtml(detail)}</p>`;
  } finally {
    btn.disabled = false;
  }
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
    const res = await window.API.events.all();
    const list = (res.results || res || []).filter(e => e.event_type !== "subsidy");
    const upcoming = list.filter(e => {
      const when = new Date(e.end_date || e.start_date);
      return !isNaN(when) && when >= new Date();
    });
    const shown = (upcoming.length ? upcoming : list).slice(0, 6);
    el.innerHTML = shown.length ? shown.map(e => `
      <div class="card">
        <span class="badge">${escapeHtml(e.event_type_display || e.event_type)}</span>
        ${e.scope === "global" ? `<span class="badge" style="margin-left:.25rem;">🌍 Global</span>` : ""}
        ${e.cost === "free" ? `<span class="badge" style="margin-left:.25rem;">Free</span>` : ""}
        <h3 style="margin-top:.5rem;">${escapeHtml(e.title)}</h3>
        ${e.host ? `<p class="muted" style="margin:0;">🏛️ ${escapeHtml(e.host)}</p>` : ""}
        <p>${escapeHtml(e.description || "")}</p>
        <p class="muted">📍 ${escapeHtml(e.location || "Online")}</p>
        <p class="muted">📅 ${new Date(e.start_date).toLocaleString()}</p>
        <p class="muted">${escapeHtml(e.join_mode_display || "Details from host")}</p>
        <a class="btn-primary" style="margin-top:.5rem;"
           href="events.html?event=${encodeURIComponent(e.id)}">Register / Join</a>
      </div>`).join("")
      : `<p class="muted">No events published yet. <a href="events.html">Browse global &amp; local events</a>.</p>`;
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
    const res = await window.API.events.list("event_type=subsidy");
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