/* ------------------------------------------------------------------
   FarmKonnect FMS dashboard controller
------------------------------------------------------------------ */

const FMS_MODULES = {
  farms: {
    title: "Farms", endpoint: "farms",
    columns: [
      { key: "name", label: "Farm Name" },
      { key: "size", label: "Size" },
      { key: "size_unit", label: "Unit" },
      { key: "soil_type", label: "Soil" },
      { key: "ownership_type", label: "Ownership" },
      { key: "irrigation_available", label: "Irrigated", type: "bool" },
    ],
    fields: [
      { key: "name", label: "Farm Name", required: true },
      { key: "location", label: "Location" },
      { key: "size", label: "Size", type: "number" },
      { key: "size_unit", label: "Unit", default: "acres" },
      { key: "soil_type", label: "Soil Type", type: "select",
        options: ["sandy","loam","clay","silt","peat","chalk"] },
      { key: "ownership_type", label: "Ownership", type: "select",
        options: ["owned","leased","family","communal"] },
      { key: "water_source", label: "Water Source" },
      { key: "irrigation_available", label: "Irrigation Available", type: "bool" },
      { key: "gps_latitude", label: "GPS Latitude", type: "number" },
      { key: "gps_longitude", label: "GPS Longitude", type: "number" },
    ],
  },
  crops: {
    title: "Crop Records", endpoint: "crops",
    columns: [
      { key: "photo", label: "Photo", type: "thumb" },
      { key: "crop", label: "Crop" },
      { key: "variety", label: "Variety" },
      { key: "planting_date", label: "Planted" },
      { key: "expected_harvest", label: "Expected Harvest" },
      { key: "area", label: "Area" },
    ],
    fields: [
      { key: "farm", label: "Farm", type: "farm_select", required: true },
      { key: "crop", label: "Crop", required: true },
      { key: "variety", label: "Variety" },
      { key: "planting_date", label: "Planting Date", type: "date" },
      { key: "expected_harvest", label: "Expected Harvest", type: "date" },
      { key: "area", label: "Area", type: "number" },
      { key: "area_unit", label: "Unit", default: "acres" },
      { key: "seed_source", label: "Seed Source" },
      { key: "notes", label: "Notes", type: "textarea" },
      { key: "image", label: "Crop / field photo", type: "image", multiple: false,
        help: "A photo of the crop or the field helps officers advise you. Taken in daylight, close enough to see the leaves." },
      { key: "photo_url", label: "…or paste an image link", type: "url" },
    ],
  },
  plantings: {
    title: "Planting Activities", endpoint: "plantings",
    columns: [
      { key: "date", label: "Date" },
      { key: "crop", label: "Crop" },
      { key: "seed_variety", label: "Variety" },
      { key: "area_planted", label: "Area" },
      { key: "planting_method", label: "Method" },
    ],
    fields: [
      { key: "farm", label: "Farm", type: "farm_select", required: true },
      { key: "date", label: "Date", type: "date", required: true },
      { key: "crop", label: "Crop", required: true },
      { key: "seed_variety", label: "Seed Variety" },
      { key: "area_planted", label: "Area Planted", type: "number" },
      { key: "seed_quantity", label: "Seed Quantity" },
      { key: "planting_method", label: "Planting Method" },
      { key: "responsible_person", label: "Responsible Person" },
      { key: "notes", label: "Notes", type: "textarea" },
    ],
  },
  inputs: {
    title: "Farm Inputs", endpoint: "farm-inputs",
    columns: [
      { key: "name", label: "Input" },
      { key: "input_type", label: "Type" },
      { key: "quantity", label: "Quantity" },
      { key: "cost", label: "Cost" },
      { key: "application_date", label: "Applied" },
    ],
    fields: [
      { key: "farm", label: "Farm", type: "farm_select", required: true },
      { key: "name", label: "Input Name", required: true },
      { key: "input_type", label: "Type", type: "select",
        options: ["fertilizer","pesticide","herbicide","fungicide","seed","other"] },
      { key: "quantity", label: "Quantity" },
      { key: "cost", label: "Cost", type: "number" },
      { key: "application_date", label: "Application Date", type: "date" },
      { key: "crop", label: "Crop" },
      { key: "notes", label: "Notes", type: "textarea" },
    ],
  },
  diseases: {
    title: "Disease & Pest Reports", endpoint: "diseases",
    columns: [
      { key: "photo", label: "Photo", type: "thumb" },
      { key: "date", label: "Date" },
      { key: "crop", label: "Crop" },
      { key: "diagnosis", label: "Diagnosis" },
      { key: "severity", label: "Severity" },
      { key: "status", label: "Status" },
    ],
    fields: [
      { key: "farm", label: "Farm", type: "farm_select" },
      { key: "date", label: "Date", type: "date", required: true },
      { key: "crop", label: "Crop", required: true },
      { key: "variety", label: "Variety" },
      { key: "growth_stage", label: "Growth stage", placeholder: "e.g. seedling, flowering" },
      { key: "symptoms", label: "Symptoms", type: "textarea",
        placeholder: "What do you see? e.g. yellow spots on lower leaves, wilting in the afternoon" },
      { key: "affected_area", label: "How much is affected?", placeholder: "e.g. about a quarter of the field" },
      { key: "image", label: "Photos of the affected plant", type: "image", multiple: true, max: 5,
        stages: true,
        help: "Add up to 5 photos from different angles — a close-up of the leaf, the whole plant, and the wider field. This helps get the diagnosis right." },
      { key: "photo_url", label: "…or paste an image link", type: "url" },
      { key: "diagnosis", label: "Diagnosis", placeholder: "Leave blank if you want it reviewed" },
      { key: "severity", label: "Severity", type: "select", options: ["low","medium","high"] },
      { key: "treatment", label: "Treatment", type: "textarea" },
      { key: "status", label: "Status", type: "select", options: ["open","treated","resolved"] },
    ],
  },
  harvests: {
    title: "Harvests", endpoint: "harvests",
    columns: [
      { key: "crop", label: "Crop" },
      { key: "harvest_date", label: "Date" },
      { key: "quantity", label: "Quantity" },
      { key: "unit", label: "Unit" },
      { key: "grade", label: "Grade" },
    ],
    fields: [
      { key: "farm", label: "Farm", type: "farm_select" },
      { key: "crop", label: "Crop", required: true },
      { key: "harvest_date", label: "Harvest Date", type: "date", required: true },
      { key: "quantity", label: "Quantity", type: "number" },
      { key: "unit", label: "Unit", default: "kg" },
      { key: "grade", label: "Grade", type: "select", options: ["A","B","C"] },
      { key: "storage_facility", label: "Storage Facility" },
      { key: "notes", label: "Notes", type: "textarea" },
    ],
  },
  inventory: {
    title: "Inventory", endpoint: "inventory",
    columns: [
      { key: "product", label: "Product" },
      { key: "quantity", label: "Quantity" },
      { key: "unit", label: "Unit" },
      { key: "storage_location", label: "Location" },
      { key: "updated_at", label: "Updated" },
    ],
    fields: [
      { key: "farm", label: "Farm", type: "farm_select" },
      { key: "product", label: "Product", required: true },
      { key: "quantity", label: "Quantity", type: "number" },
      { key: "unit", label: "Unit", default: "kg" },
      { key: "storage_location", label: "Storage Location" },
    ],
  },
  sales: {
    title: "Sales", endpoint: "sales",
    columns: [
      { key: "date", label: "Date" },
      { key: "product", label: "Product" },
      { key: "quantity", label: "Qty" },
      { key: "unit", label: "Unit" },
      { key: "amount", label: "Amount" },
      { key: "payment_method", label: "Payment" },
    ],
    fields: [
      { key: "date", label: "Date", type: "date", required: true },
      { key: "product", label: "Product", required: true },
      { key: "quantity", label: "Quantity", type: "number" },
      { key: "unit", label: "Unit", default: "kg" },
      { key: "price", label: "Unit Price", type: "number" },
      { key: "amount", label: "Total Amount", type: "number" },
      { key: "customer", label: "Customer" },
      { key: "payment_method", label: "Payment Method", type: "select",
        options: ["cash","mpesa","card","credit"] },
    ],
  },
  purchases: {
    title: "Purchases", endpoint: "purchases",
    columns: [
      { key: "purchase_date", label: "Date" },
      { key: "item", label: "Item" },
      { key: "quantity", label: "Qty" },
      { key: "supplier", label: "Supplier" },
      { key: "cost", label: "Cost" },
    ],
    fields: [
      { key: "purchase_date", label: "Purchase Date", type: "date", required: true },
      { key: "item", label: "Item", required: true },
      { key: "quantity", label: "Quantity" },
      { key: "supplier", label: "Supplier" },
      { key: "cost", label: "Cost", type: "number" },
      { key: "notes", label: "Notes", type: "textarea" },
    ],
  },
  weather: {
    title: "Weather Log", endpoint: "weather",
    columns: [
      { key: "date", label: "Date" },
      { key: "rainfall_mm", label: "Rainfall (mm)" },
      { key: "temperature_c", label: "Temp (°C)" },
      { key: "humidity_pct", label: "Humidity (%)" },
    ],
    fields: [
      { key: "farm", label: "Farm", type: "farm_select" },
      { key: "date", label: "Date", type: "date", required: true },
      { key: "rainfall_mm", label: "Rainfall (mm)", type: "number" },
      { key: "temperature_c", label: "Temperature (°C)", type: "number" },
      { key: "humidity_pct", label: "Humidity (%)", type: "number" },
      { key: "notes", label: "Notes" },
    ],
  },
  visits: {
    title: "Extension Visits", endpoint: "visits",
    columns: [
      { key: "date", label: "Date" },
      { key: "officer", label: "Officer" },
      { key: "follow_up_date", label: "Follow-Up" },
    ],
    fields: [
      { key: "officer", label: "Officer", required: true },
      { key: "date", label: "Date", type: "date", required: true },
      { key: "recommendations", label: "Recommendations", type: "textarea" },
      { key: "follow_up_date", label: "Follow-Up Date", type: "date" },
    ],
  },
  finance: {
    title: "Financial Records", endpoint: "finance",
    columns: [
      { key: "date", label: "Date" },
      { key: "income", label: "Income" },
      { key: "expenses", label: "Expenses" },
      { key: "profit", label: "Profit" },
      { key: "loans", label: "Loans" },
      { key: "subsidies", label: "Subsidies" },
    ],
    fields: [
      { key: "date", label: "Date", type: "date", required: true },
      { key: "income", label: "Income", type: "number" },
      { key: "expenses", label: "Expenses", type: "number" },
      { key: "loans", label: "Loans", type: "number" },
      { key: "insurance", label: "Insurance", type: "number" },
      { key: "subsidies", label: "Subsidies", type: "number" },
      { key: "notes", label: "Notes", type: "textarea" },
    ],
  },
};

let FARM_CACHE = [];

async function fetchFarms() {
  try {
    const res = await window.API.farms.list();
    FARM_CACHE = res.results || res || [];
  } catch { FARM_CACHE = []; }
  return FARM_CACHE;
}

document.addEventListener("DOMContentLoaded", async () => {
  if (document.body.dataset.page !== "dashboard") return;
  if (!window.isLoggedIn()) { window.location.href = "login.html"; return; }

  const user = window.getUser();
  const welcome = document.getElementById("welcomeName");
  if (welcome) welcome.textContent = user?.first_name || user?.username || "Farmer";

  // profile completion check
  if (user && user.profile_completed === false) {
    window.location.href = "farmer-profile.html";
    return;
  }

  await fetchFarms();   // prime the farm dropdown cache

  // sidebar toggle
  document.querySelectorAll(".nav-group > .nav-group-title").forEach(t => {
    t.addEventListener("click", () => t.parentElement.classList.toggle("open"));
  });

  // section switching
  document.querySelectorAll("[data-section]").forEach(link => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      showSection(link.dataset.section);
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

  showSection("overview");
});

function showSection(name) {
  document.querySelectorAll(".content-section").forEach(s => s.classList.remove("active"));
  const sec = document.getElementById(`sec-${name}`);
  if (sec) sec.classList.add("active");

  document.querySelectorAll("[data-section]").forEach(l =>
    l.classList.toggle("active", l.dataset.section === name)
  );

  const title = document.getElementById("pageTitle");
  if (title) title.textContent = FMS_MODULES[name]?.title || name.charAt(0).toUpperCase() + name.slice(1);

  if (name === "overview") loadOverview();
  else if (FMS_MODULES[name]) renderModule(name);
}

/* ---------------- Overview ---------------- */
async function loadOverview() {
  const el = document.getElementById("overviewStats");
  if (!el) return;
  el.innerHTML = `<div class="stat-card"><h3>—</h3><p>Loading…</p></div>`;

  const safe = (p) => p.catch(() => ({ results: [] }));
  try {
    const [farms, crops, harvests, sales, purchases, diseases] = await Promise.all([
      safe(window.API.farms.list()),
      safe(window.API.crops.list()),
      safe(window.API.harvests.list()),
      safe(window.API.sales.list()),
      safe(window.API.purchases.list()),
      safe(window.API.diseases.list()),
    ]);
    const cnt = (r) => (r.results || r || []).length;
    const sum = (r, k) => (r.results || r || []).reduce((s, x) => s + parseFloat(x[k] || 0), 0);

    el.innerHTML = `
      <div class="stat-card"><h3>${cnt(farms)}</h3><p>Farms</p></div>
      <div class="stat-card"><h3>${cnt(crops)}</h3><p>Crop Records</p></div>
      <div class="stat-card"><h3>${cnt(harvests)}</h3><p>Harvests</p></div>
      <div class="stat-card"><h3>KSh ${sum(sales, "amount").toFixed(2)}</h3><p>Sales Revenue</p></div>
      <div class="stat-card"><h3>KSh ${sum(purchases, "cost").toFixed(2)}</h3><p>Purchase Cost</p></div>
      <div class="stat-card"><h3>${cnt(diseases)}</h3><p>Disease Reports</p></div>
    `;
  } catch {
    el.innerHTML = `<p class="muted">Unable to load stats.</p>`;
  }
}

/* ---------------- Generic module renderer ---------------- */
async function renderModule(name) {
  const cfg = FMS_MODULES[name];
  const el = document.getElementById(`sec-${name}`);
  if (!el || !cfg) return;

  el.innerHTML = `
    <div class="mb-1" style="display:flex;justify-content:space-between;align-items:center;">
      <button class="btn-primary" id="addBtn">+ Add ${cfg.title.replace(/s$/, "")}</button>
      <input type="search" id="filterInput" placeholder="Filter…"
             style="padding:.5rem .75rem;border-radius:8px;border:1px solid var(--border);">
    </div>
    <div id="tableWrap"><p class="muted">Loading…</p></div>
  `;

  el.querySelector("#addBtn").addEventListener("click", () => openForm(name, null));

  let rows = [];
  try {
    const res = await window.API[cfg.endpoint].list();
    rows = res.results || res || [];
  } catch (e) {
    el.querySelector("#tableWrap").innerHTML =
      `<p class="muted">Unable to load (${e.message}).</p>`;
    return;
  }

  const render = (list) => {
    const table = `
      <table class="data-table">
        <thead><tr>${cfg.columns.map(c => `<th>${c.label}</th>`).join("")}<th></th></tr></thead>
        <tbody>
          ${list.map(r => `
            <tr>
              ${cfg.columns.map(c => {
                if (c.type === "thumb") {
                  const src = r.image_src || "";
                  const extra = r.photo_count > 1 ? `<span class="thumb-count">+${r.photo_count - 1}</span>` : "";
                  return `<td class="thumb-cell">${src
                    ? `<span class="thumb-wrap"><img src="${src}" alt="photo" loading="lazy"
                         onerror="this.parentElement.classList.add('thumb-broken')">${extra}</span>`
                    : `<span class="muted">—</span>`}</td>`;
                }
                let v = r[c.key];
                if (c.type === "bool") v = v ? "Yes" : "No";
                if (v === null || v === undefined) v = "";
                return `<td>${v}</td>`;
              }).join("")}
              <td style="white-space:nowrap;">
                <button class="btn-outline" data-edit="${r.id}" style="padding:.3rem .7rem;font-size:.8rem;">Edit</button>
                <button class="btn-danger" data-del="${r.id}" style="padding:.3rem .7rem;font-size:.8rem;">Delete</button>
              </td>
            </tr>`).join("") ||
            `<tr><td colspan="${cfg.columns.length + 1}" class="muted">No records yet.</td></tr>`}
        </tbody>
      </table>`;
    el.querySelector("#tableWrap").innerHTML = table;
    el.querySelectorAll("[data-edit]").forEach(b => {
      const id = b.dataset.edit;
      b.addEventListener("click", () => {
        const row = rows.find(x => String(x.id) === String(id));
        openForm(name, row);
      });
    });
    el.querySelectorAll("[data-del]").forEach(b => {
      const id = b.dataset.del;
      b.addEventListener("click", async () => {
        if (!confirm("Delete this record?")) return;
        try {
          await window.API[cfg.endpoint].remove(id);
          renderModule(name);
        } catch (e) { alert("Delete failed: " + e.message); }
      });
    });
  };

  render(rows);

  const filter = el.querySelector("#filterInput");
  filter.addEventListener("input", () => {
    const q = filter.value.toLowerCase();
    const filtered = rows.filter(r =>
      Object.values(r).some(v => String(v ?? "").toLowerCase().includes(q))
    );
    render(filtered);
  });
}

/* ---------------- Modal form ---------------- */
function openForm(name, record) {
  const cfg = FMS_MODULES[name];
  const isEdit = !!record;

  const backdrop = document.createElement("div");
  backdrop.className = "modal-backdrop";
  backdrop.style.cssText =
    "position:fixed;inset:0;background:rgba(0,0,0,.45);display:flex;align-items:center;" +
    "justify-content:center;z-index:100;padding:1rem;";

  const modal = document.createElement("div");
  modal.style.cssText =
    "background:#fff;border-radius:12px;max-width:600px;width:100%;max-height:90vh;" +
    "overflow-y:auto;padding:1.5rem;box-shadow:0 20px 40px rgba(0,0,0,.25);";

  const heading = document.createElement("h3");
  heading.textContent = `${isEdit ? "Edit" : "Add"} ${cfg.title.replace(/s$/, "")}`;
  modal.appendChild(heading);

  const form = document.createElement("form");
  form.className = "form";

  // Image fields are built by the shared ImagePicker instead of as plain inputs.
  const pickers = {};
  const mountedPickers = [];

  cfg.fields.forEach(f => {
    if (f.type === "image") {
      const wrap = document.createElement("div");
      wrap.className = "form-image-field";
      form.appendChild(wrap);
      mountedPickers.push({ field: f, wrap });
      return;
    }

    const label = document.createElement("label");
    label.textContent = f.label;

    let input;
    if (f.type === "textarea") {
      input = document.createElement("textarea");
      input.rows = 2;
    } else if (f.type === "select") {
      input = document.createElement("select");
      const blank = document.createElement("option");
      blank.value = ""; blank.textContent = "—";
      input.appendChild(blank);
      (f.options || []).forEach(o => {
        const opt = document.createElement("option");
        opt.value = o; opt.textContent = o;
        input.appendChild(opt);
      });
    } else if (f.type === "farm_select") {
      input = document.createElement("select");
      const blank = document.createElement("option");
      blank.value = ""; blank.textContent = "—";
      input.appendChild(blank);
      FARM_CACHE.forEach(farm => {
        const opt = document.createElement("option");
        opt.value = farm.id;
        opt.textContent = `${farm.name} (${farm.size} ${farm.size_unit})`;
        input.appendChild(opt);
      });
    } else if (f.type === "bool") {
      input = document.createElement("input");
      input.type = "checkbox";
    } else {
      input = document.createElement("input");
      input.type = f.type === "number" ? "number" : f.type === "date" ? "date" : "text";
      if (f.type === "number") input.step = "any";
      if (f.placeholder) input.placeholder = f.placeholder;
    }

    input.name = f.key;
    if (f.required) input.required = true;

    // prefill
    if (record) {
      const val = record[f.key];
      if (f.type === "bool") input.checked = !!val;
      else if (val !== null && val !== undefined) input.value = val;
    } else if (f.default !== undefined && f.type !== "bool") {
      input.value = f.default;
    }

    label.appendChild(input);
    form.appendChild(label);
  });

  const actions = document.createElement("div");
  actions.style.cssText = "display:flex;gap:.5rem;margin-top:1rem;";
  actions.innerHTML = `
    <button type="submit" class="btn-primary">Save</button>
    <button type="button" class="btn-outline" id="cancelBtn">Cancel</button>
  `;
  form.appendChild(actions);
  modal.appendChild(form);
  backdrop.appendChild(modal);
  document.body.appendChild(backdrop);

  // Image pickers need to be in the document before they can measure/show previews.
  mountedPickers.forEach(({ field, wrap }) => {
    const existing = record && record.image_src
      ? [{ src: record.image_src, caption: "", stage: record.photo_stage || "" }]
      : [];
    pickers[field.key] = window.ImagePicker.mount(wrap, {
      label: field.label,
      help: field.help,
      multiple: field.multiple !== false,
      max: field.max || (field.multiple === false ? 1 : 5),
      stages: field.stages ? window.ImagePicker.DISEASE_STAGES : [],
      value: existing,
    });
  });

  form.querySelector("#cancelBtn").addEventListener("click", () => backdrop.remove());

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    // Any chosen photo means we must submit multipart instead of JSON.
    const withImages = Object.values(pickers).some(p => p.hasFiles());
    const recordId = record && record.id;

    try {
      if (withImages) {
        const fd = new FormData();
        cfg.fields.forEach(f => {
          if (f.type === "image") return;
          const el = form.elements[f.key];
          if (!el) return;
          const v = f.type === "bool" ? el.checked : el.value;
          // Multipart sends empty strings as ""; blank optional values are cleared.
          fd.append(f.key, v === null || v === undefined ? "" : v);
        });
        Object.entries(pickers).forEach(([key, picker]) => {
          picker.appendTo(fd, key, "images");
        });

        if (recordId) await window.API[cfg.endpoint].update(recordId, fd);
        else          await window.API[cfg.endpoint].create(fd);
      } else {
        const data = {};
        cfg.fields.forEach(f => {
          if (f.type === "image") return;
          const el = form.elements[f.key];
          if (!el) return;
          let v;
          if (f.type === "bool") v = el.checked;
          else v = el.value === "" ? null : el.value;
          data[f.key] = v;
        });

        if (recordId) await window.API[cfg.endpoint].update(recordId, data);
        else          await window.API[cfg.endpoint].create(data);
      }

      backdrop.remove();
      renderModule(name);
    } catch (err) {
      const detail = err?.data
        ? Object.entries(err.data).map(([k,v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : v}`).join(" | ")
        : err.message;
      alert("Save failed: " + detail);
    }
  });
}