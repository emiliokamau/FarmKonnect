/* Dashboard page controller */
document.addEventListener("DOMContentLoaded", () => {
  if (document.body.dataset.page !== "dashboard") return;
  guardAuth();

  const user = getUser();
  document.getElementById("welcomeName").textContent = user?.first_name || user?.username || "Farmer";

  // mobile nav toggle
  document.querySelectorAll("[data-toggle]").forEach(btn => {
    btn.addEventListener("click", () => {
      const target = document.querySelector(btn.dataset.toggle);
      target?.classList.toggle("open");
    });
  });

  // sidebar dropdowns
  document.querySelectorAll(".nav-group > .nav-group-title").forEach(t => {
    t.addEventListener("click", () => t.parentElement.classList.toggle("open"));
  });

  // section switching (SPA-ish)
  document.querySelectorAll("[data-section]").forEach(link => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      showSection(link.dataset.section);
    });
  });

  // logout
  document.querySelectorAll("[data-logout]").forEach(b => b.addEventListener("click", async () => {
    await API.logout();
    logout();
  }));

  // default
  showSection("overview");
});

const SECTION_LOADERS = {
  overview: loadOverview,
  fields: loadFields,
  tasks: loadTasks,
  equipment: loadEquipment,
  reports: loadReports,
  workers: loadWorkers,
  advisories: loadAdvisories,
};

function showSection(name) {
  document.querySelectorAll(".content-section").forEach(s => s.classList.remove("active"));
  document.querySelector(`#sec-${name}`)?.classList.add("active");
  document.querySelectorAll("[data-section]").forEach(l => l.classList.toggle("active", l.dataset.section === name));
  const title = document.getElementById("pageTitle");
  if (title) title.textContent = name.charAt(0).toUpperCase() + name.slice(1);
  const loader = SECTION_LOADERS[name];
  if (loader) loader();
}

/* ---- Overview ---- */
async function loadOverview() {
  const el = document.getElementById("overviewStats");
  el.innerHTML = `<div class="stat-card"><h3>—</h3><p>Loading...</p></div>`;
  try {
    const [orders, products, advisories] = await Promise.all([
      API.orders().catch(() => ({ results: [] })),
      API.products().catch(() => ({ results: [] })),
      API.advisories().catch(() => ({ results: [] })),
    ]);
    const ordersList = orders.results || orders;
    const productsList = products.results || products;
    const advList = advisories.results || advisories;
    const revenue = ordersList.reduce((s, o) => s + parseFloat(o.total || 0), 0);
    el.innerHTML = `
      <div class="stat-card"><h3>${ordersList.length}</h3><p>Orders</p></div>
      <div class="stat-card"><h3>${productsList.length}</h3><p>Products</p></div>
      <div class="stat-card"><h3>KSh ${revenue.toFixed(2)}</h3><p>Revenue</p></div>
      <div class="stat-card"><h3>${advList.length}</h3><p>Advisories</p></div>
    `;
  } catch {
    el.innerHTML = `<p class="muted">Unable to load stats.</p>`;
  }
}

/* ---- LocalStorage-backed Farm Management (frontend CRUD) ---- */
const farmStore = {
  get(key) { return JSON.parse(localStorage.getItem(`fk_${key}`) || "[]"); },
  set(key, arr) { localStorage.setItem(`fk_${key}`, JSON.stringify(arr)); },
  add(key, item) { const a = this.get(key); item.id = Date.now(); a.push(item); this.set(key, a); },
  remove(key, id) { this.set(key, this.get(key).filter(x => x.id !== id)); },
};

const FARM_TABLES = {
  fields:  { el: "fieldsTable",  cols: ["name", "size", "crop", "location"], placeholders: ["Field name", "Size (acres)", "Crop", "Location"] },
  tasks:   { el: "tasksTable",   cols: ["title", "assignee", "due", "status"], placeholders: ["Task title", "Assignee", "Due date", "Status"] },
  equipment: { el: "equipmentTable", cols: ["name", "type", "condition"], placeholders: ["Equipment name", "Type", "Condition"] },
  reports: { el: "reportsTable", cols: ["title", "period", "summary"], placeholders: ["Report title", "Period", "Summary"] },
  workers: { el: "workersTable", cols: ["name", "role", "phone"], placeholders: ["Worker name", "Role", "Phone"] },
};

function renderFarmTable(key) {
  const cfg = FARM_TABLES[key];
  const table = document.getElementById(cfg.el);
  if (!table) return;
  const rows = farmStore.get(key);
  table.innerHTML = `
    <thead><tr>${cfg.cols.map(c => `<th>${c}</th>`).join("")}<th></th></tr></thead>
    <tbody>
      ${rows.map(r => `
        <tr>
          ${cfg.cols.map(c => `<td>${r[c] ?? ""}</td>`).join("")}
          <td><button class="btn-danger" onclick="deleteFarmRow('${key}', ${r.id})">Delete</button></td>
        </tr>`).join("") || `<tr><td colspan="${cfg.cols.length + 1}" class="muted">No records yet.</td></tr>`}
    </tbody>
  `;
}
function deleteFarmRow(key, id) {
  farmStore.remove(key, id);
  renderFarmTable(key);
}
function addFarmRow(key) {
  const cfg = FARM_TABLES[key];
  const values = cfg.cols.map(c => prompt(cfg.placeholders[cfg.cols.indexOf(c)] || c));
  if (values.some(v => v === null)) return;
  const obj = {};
  cfg.cols.forEach((c, i) => obj[c] = values[i]);
  farmStore.add(key, obj);
  renderFarmTable(key);
}

function loadFields()    { renderFarmTable("fields"); }
function loadTasks()     { renderFarmTable("tasks"); }
function loadEquipment() { renderFarmTable("equipment"); }
function loadReports()   { renderFarmTable("reports"); }
function loadWorkers()   { renderFarmTable("workers"); }

/* ---- Advisories ---- */
async function loadAdvisories() {
  const el = document.getElementById("advisoriesList");
  el.innerHTML = "<p class='muted'>Loading...</p>";
  try {
    const res = await API.advisories();
    const list = res.results || res;
    el.innerHTML = list.length ? list.map(a => `
      <div class="card">
        <h4>${a.subject}</h4>
        <p>${a.message}</p>
        <small class="muted">Status: ${a.status} · ${new Date(a.created_at).toLocaleString()}</small>
      </div>`).join("") : `<p class="muted">No advisories yet.</p>`;
  } catch {
    el.innerHTML = "<p class='muted'>Unable to load.</p>";
  }
}