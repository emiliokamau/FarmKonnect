/* Farmer Portal controller */
document.addEventListener("DOMContentLoaded", () => {
  if (document.body.dataset.page !== "farmer") return;
  guardAuth();

  document.querySelectorAll("[data-portal-tab]").forEach(btn => {
    btn.addEventListener("click", () => showTab(btn.dataset.portalTab));
  });
  showTab("trends");
});

const PORTAL_LOADERS = {
  trends: loadTrends,
  disease: loadDisease,
  practices: loadPractices,
  officers: loadOfficers,
  events: loadEvents,
  subsidy: loadSubsidy,
  compare: loadCompare,
};

function showTab(name) {
  document.querySelectorAll(".portal-panel").forEach(p => p.classList.remove("active"));
  document.querySelector(`#tab-${name}`)?.classList.add("active");
  document.querySelectorAll("[data-portal-tab]").forEach(b => b.classList.toggle("active", b.dataset.portalTab === name));
  PORTAL_LOADERS[name]?.();
}

/* --------- Market Trends --------- */
async function loadTrends() {
  const el = document.getElementById("trendsArea");
  el.innerHTML = "<p class='muted'>Loading market trends...</p>";
  try {
    const [commodities, prices] = await Promise.all([API.commodities(), API.prices()]);
    const cList = commodities.results || commodities;
    const pList = prices.results || prices;

    el.innerHTML = `
      <div class="filter-row">
        <label>Filter by commodity:
          <select id="trendFilter">
            <option value="">All</option>
            ${cList.map(c => `<option value="${c.name}">${c.name}</option>`).join("")}
          </select>
        </label>
      </div>
      <table class="data-table" id="trendsTable">
        <thead><tr><th>Commodity</th><th>County</th><th>Price (KSh)</th><th>Date</th></tr></thead>
        <tbody>${pList.map(p => `<tr>
          <td>${p.commodity_name || ""}</td>
          <td>${p.county_name || ""}</td>
          <td>${parseFloat(p.price).toFixed(2)}</td>
          <td>${p.date}</td>
        </tr>`).join("") || `<tr><td colspan="4" class="muted">No market data yet.</td></tr>`}</tbody>
      </table>
    `;
    document.getElementById("trendFilter").addEventListener("change", (e) => {
      const v = e.target.value.toLowerCase();
      document.querySelectorAll("#trendsTable tbody tr").forEach(tr => {
        tr.style.display = !v || tr.children[0].textContent.toLowerCase().includes(v) ? "" : "none";
      });
    });
  } catch {
    el.innerHTML = "<p class='muted'>Unable to load.</p>";
  }
}

/* --------- Disease Detection (mock AI) --------- */
function loadDisease() {
  const el = document.getElementById("diseaseArea");
  el.innerHTML = `
    <div class="card">
      <h3>Disease Detection</h3>
      <p>Upload a leaf or plant photo. Our AI will diagnose the likely disease.</p>
      <input type="file" id="diseaseFile" accept="image/*">
      <button class="btn-primary" onclick="analyzeDisease()">Analyze</button>
      <div id="diseaseResult" class="mt-1"></div>
    </div>`;
}
function analyzeDisease() {
  const f = document.getElementById("diseaseFile").files[0];
  const out = document.getElementById("diseaseResult");
  if (!f) return out.innerHTML = "<p class='muted'>Please choose an image.</p>";
  out.innerHTML = "<p class='muted'>Analyzing...</p>";
  setTimeout(() => {
    const possible = ["Leaf Blight", "Powdery Mildew", "Rust", "Healthy", "Bacterial Wilt", "Aphid Infestation"];
    const res = possible[Math.floor(Math.random() * possible.length)];
    out.innerHTML = `
      <div class="card result-card">
        <h4>Result: ${res}</h4>
        <p>Recommended treatment: apply approved fungicide, remove affected leaves, and improve airflow.</p>
      </div>`;
  }, 1200);
}

/* --------- Best Practices --------- */
async function loadPractices() {
  const el = document.getElementById("practicesArea");
  el.innerHTML = "<p class='muted'>Loading...</p>";
  try {
    const res = await API.products();
    const list = (res.results || res).filter(p => (p.category || "").toLowerCase() === "practice");
    el.innerHTML = list.length ? list.map(p => `
      <div class="card">
        <h4>${p.name}</h4>
        <p>${p.description || ""}</p>
      </div>`).join("") : "<p class='muted'>No best practices published yet. Add them via admin (Products, category='practice').</p>";
  } catch {
    el.innerHTML = "<p class='muted'>Unable to load.</p>";
  }
}

/* --------- Agricultural Officers --------- */
async function loadOfficers() {
  const el = document.getElementById("officersArea");
  el.innerHTML = "<p class='muted'>Loading...</p>";
  try {
    const users = await apiFetch("/users/", { auth: false });
    const list = (users.results || users).filter(u => u.is_staff);
    el.innerHTML = list.length ? list.map(u => `
      <div class="card">
        <h4>${u.first_name || u.username}</h4>
        <p>Email: ${u.email}</p>
        <p>Phone: ${u.phone || "N/A"}</p>
      </div>`).join("") : "<p class='muted'>No officers yet.</p>";
  } catch {
    el.innerHTML = "<p class='muted'>Unable to load officers.</p>";
  }
}

/* --------- Training Events & Grants --------- */
async function loadEvents() {
  const el = document.getElementById("eventsArea");
  el.innerHTML = "<p class='muted'>Loading...</p>";
  try {
    const res = await API.events();
    const list = res.results || res;
    el.innerHTML = list.length ? list.map(e => `
      <div class="card">
        <span class="badge">${e.event_type}</span>
        <h4>${e.title}</h4>
        <p>${e.description || ""}</p>
        <small class="muted">${e.location} · ${new Date(e.start_date).toLocaleString()}</small>
      </div>`).join("") : "<p class='muted'>No events published.</p>";
  } catch {
    el.innerHTML = "<p class='muted'>Unable to load.</p>";
  }
}

/* --------- Subsidized Fertilizer Programme --------- */
async function loadSubsidy() {
  const el = document.getElementById("subsidyArea");
  el.innerHTML = "<p class='muted'>Loading...</p>";
  try {
    const res = await API.events("subsidy");
    const list = res.results || res;
    el.innerHTML = list.length ? list.map(e => `
      <div class="card">
        <h4>${e.title}</h4>
        <p>${e.description || ""}</p>
        <small class="muted">${e.location}</small>
      </div>`).join("") : "<p class='muted'>No subsidy programmes at this time.</p>";
  } catch {
    el.innerHTML = "<p class='muted'>Unable to load.</p>";
  }
}

/* --------- Price Comparison --------- */
async function loadCompare() {
  const el = document.getElementById("compareArea");
  el.innerHTML = "<p class='muted'>Loading...</p>";
  try {
    const [commodities, prices] = await Promise.all([API.commodities(), API.prices()]);
    const cList = commodities.results || commodities;
    const pList = prices.results || prices;

    // group by commodity -> county -> price
    const grouped = {};
    pList.forEach(p => {
      grouped[p.commodity_name] = grouped[p.commodity_name] || {};
      grouped[p.commodity_name][p.county_name] = p.price;
    });

    el.innerHTML = Object.entries(grouped).map(([commodity, countyMap]) => {
      const entries = Object.entries(countyMap);
      const best = entries.reduce((a, b) => (parseFloat(a[1]) > parseFloat(b[1]) ? a : b));
      return `
        <div class="card">
          <h4>${commodity}</h4>
          <table class="data-table">
            <thead><tr><th>County</th><th>Price</th></tr></thead>
            <tbody>${entries.map(([c, v]) => `
              <tr><td>${c}</td><td>KSh ${parseFloat(v).toFixed(2)} ${c === best[0] ? "🏆" : ""}</td></tr>`).join("")}
            </tbody>
          </table>
        </div>`;
    }).join("") || "<p class='muted'>No data.</p>";
  } catch {
    el.innerHTML = "<p class='muted'>Unable to load.</p>";
  }
}