/* ------------------------------------------------------------------
   FarmKonnect POS controller
------------------------------------------------------------------ */

const POS_USER_KEY = "fk_pos_settings";
let POS_CACHE = { sales: [], products: [], purchases: [] };

/* ---------------- Bootstrap ---------------- */
document.addEventListener("DOMContentLoaded", async () => {
  if (document.body.dataset.page !== "pos") return;

  if (!window.isLoggedIn()) {
    window.location.href = "login.html";
    return;
  }

  const user = window.getUser();
  const posUser = document.getElementById("posUser");
  if (posUser) posUser.textContent = user?.first_name || user?.username || "User";

  // sidebar toggles
  document.querySelectorAll(".nav-group > .nav-group-title").forEach(t => {
    t.addEventListener("click", () => t.parentElement.classList.toggle("open"));
  });

  // section switching
  document.querySelectorAll("[data-pos-section]").forEach(link => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      showPosSection(link.dataset.posSection);
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

  showPosSection("dashboard");
});

function showPosSection(name) {
  document.querySelectorAll(".content-section").forEach(s => s.classList.remove("active"));
  document.getElementById(`pos-${name}`)?.classList.add("active");

  document.querySelectorAll("[data-pos-section]").forEach(l =>
    l.classList.toggle("active", l.dataset.posSection === name)
  );

  const titles = {
    dashboard: "Dashboard", sales: "Sales", products: "Products",
    customers: "Customers", purchases: "Purchases",
    reports: "Reports", settings: "Settings",
  };
  const titleEl = document.getElementById("posTitle");
  if (titleEl) titleEl.textContent = titles[name] || name;

  ({
    dashboard: posDashboard,
    sales:     posSales,
    products:  posProducts,
    customers: posCustomers,
    purchases: posPurchases,
    reports:   posReports,
    settings:  posSettings,
  }[name])?.();
}

/* ---------------- Helpers ---------------- */
async function loadAll() {
  const safe = (p) => p.catch(() => ({ results: [] }));
  const [sales, products, purchases] = await Promise.all([
    safe(window.API.sales.list()),
    safe(window.API.products()),
    safe(window.API.purchases.list()),
  ]);
  POS_CACHE.sales     = sales.results     || sales     || [];
  POS_CACHE.products  = products.results  || products  || [];
  POS_CACHE.purchases = purchases.results || purchases || [];
  return POS_CACHE;
}

function money(n) {
  return "KSh " + parseFloat(n || 0).toLocaleString(undefined, {
    minimumFractionDigits: 2, maximumFractionDigits: 2,
  });
}

/* ---------------- Dashboard ---------------- */
async function posDashboard() {
  const el = document.getElementById("posStats");
  const recent = document.getElementById("recentSales");
  el.innerHTML = `<div class="stat-card"><h3>—</h3><p>Loading…</p></div>`;

  await loadAll();

  const sales = POS_CACHE.sales;
  const products = POS_CACHE.products;
  const revenue = sales.reduce((s, x) => s + parseFloat(x.amount || 0), 0);

  const todayStr = new Date().toISOString().slice(0, 10);
  const todaySales = sales.filter(s => s.date === todayStr);
  const todayRevenue = todaySales.reduce((s, x) => s + parseFloat(x.amount || 0), 0);

  el.innerHTML = `
    <div class="stat-card"><h3>${sales.length}</h3><p>Total Sales</p></div>
    <div class="stat-card"><h3>${money(revenue)}</h3><p>Total Revenue</p></div>
    <div class="stat-card"><h3>${todaySales.length}</h3><p>Sales Today</p></div>
    <div class="stat-card"><h3>${money(todayRevenue)}</h3><p>Revenue Today</p></div>
    <div class="stat-card"><h3>${products.length}</h3><p>Products</p></div>
    <div class="stat-card"><h3>${products.filter(p => p.stock <= 5).length}</h3><p>Low Stock</p></div>
  `;

  const last5 = sales.slice(0, 5);
  recent.innerHTML = last5.length ? `
    <table class="data-table">
      <thead><tr><th>Date</th><th>Product</th><th>Qty</th><th>Amount</th><th>Customer</th></tr></thead>
      <tbody>${last5.map(s => `
        <tr>
          <td>${s.date}</td>
          <td>${s.product}</td>
          <td>${s.quantity} ${s.unit || ""}</td>
          <td>${money(s.amount)}</td>
          <td>${s.customer || "—"}</td>
        </tr>`).join("")}
      </tbody>
    </table>` : `<p class="muted">No sales yet.</p>`;
}

/* ---------------- Sales ---------------- */
async function posSales() {
  const wrap = document.getElementById("salesTable");
  wrap.innerHTML = `<p class="muted">Loading…</p>`;

  await loadAll();

  const render = (rows) => {
    wrap.innerHTML = rows.length ? `
      <table class="data-table">
        <thead>
          <tr>
            <th>Date</th><th>Product</th><th>Qty</th><th>Unit</th>
            <th>Price</th><th>Amount</th><th>Customer</th><th>Payment</th><th></th>
          </tr>
        </thead>
        <tbody>${rows.map(s => `
          <tr>
            <td>${s.date}</td>
            <td>${s.product}</td>
            <td>${s.quantity}</td>
            <td>${s.unit || ""}</td>
            <td>${money(s.price)}</td>
            <td>${money(s.amount)}</td>
            <td>${s.customer || "—"}</td>
            <td>${s.payment_method}</td>
            <td style="white-space:nowrap;">
              <button class="btn-outline" data-edit="${s.id}" style="padding:.3rem .7rem;font-size:.8rem;">Edit</button>
              <button class="btn-danger"  data-del="${s.id}" style="padding:.3rem .7rem;font-size:.8rem;">Delete</button>
            </td>
          </tr>`).join("")}
        </tbody>
      </table>` : `<p class="muted">No sales yet. Click <strong>+ New Sale</strong> to record one.</p>`;

    wrap.querySelectorAll("[data-edit]").forEach(b =>
      b.addEventListener("click", () => {
        const row = POS_CACHE.sales.find(x => String(x.id) === b.dataset.edit);
        openSaleForm(row);
      })
    );
    wrap.querySelectorAll("[data-del]").forEach(b =>
      b.addEventListener("click", async () => {
        if (!confirm("Delete this sale?")) return;
        try { await window.API.sales.remove(b.dataset.del); posSales(); }
        catch (e) { alert("Delete failed: " + e.message); }
      })
    );
  };

  render(POS_CACHE.sales);

  document.getElementById("addSaleBtn").onclick = () => openSaleForm(null);

  const filter = document.getElementById("salesFilter");
  filter.oninput = () => {
    const q = filter.value.toLowerCase();
    render(POS_CACHE.sales.filter(s =>
      Object.values(s).some(v => String(v ?? "").toLowerCase().includes(q))
    ));
  };
}

/* ---------------- Sale modal ---------------- */
function openSaleForm(record) {
  const isEdit = !!record;
  const backdrop = document.createElement("div");
  backdrop.className = "modal-backdrop";
  backdrop.style.cssText =
    "position:fixed;inset:0;background:rgba(0,0,0,.45);display:flex;align-items:center;" +
    "justify-content:center;z-index:100;padding:1rem;";

  const modal = document.createElement("div");
  modal.style.cssText =
    "background:#fff;border-radius:12px;max-width:560px;width:100%;max-height:90vh;" +
    "overflow-y:auto;padding:1.5rem;box-shadow:0 20px 40px rgba(0,0,0,.25);";

  const today = new Date().toISOString().slice(0, 10);

  modal.innerHTML = `
    <h3>${isEdit ? "Edit" : "New"} Sale</h3>
    <form class="form" id="saleForm">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">
        <label>Date<input type="date" name="date" required value="${record?.date || today}"></label>
        <label>Product<input name="product" required value="${record?.product || ""}"></label>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">
        <label>Quantity<input type="number" step="any" name="quantity" value="${record?.quantity || ""}"></label>
        <label>Unit<input name="unit" value="${record?.unit || "kg"}"></label>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">
        <label>Unit Price<input type="number" step="any" name="price" value="${record?.price || ""}"></label>
        <label>Total Amount<input type="number" step="any" name="amount" value="${record?.amount || ""}"></label>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">
        <label>Customer<input name="customer" value="${record?.customer || ""}"></label>
        <label>Payment
          <select name="payment_method">
            ${["cash","mpesa","card","credit"].map(o =>
              `<option value="${o}" ${record?.payment_method === o ? "selected" : ""}>${o}</option>`
            ).join("")}
          </select>
        </label>
      </div>
      <div style="display:flex;gap:.5rem;margin-top:1rem;">
        <button type="submit" class="btn-primary">Save</button>
        <button type="button" class="btn-outline" id="cancelBtn">Cancel</button>
      </div>
    </form>`;

  backdrop.appendChild(modal);
  document.body.appendChild(backdrop);

  const form = modal.querySelector("#saleForm");
  form.querySelector("#cancelBtn").onclick = () => backdrop.remove();

  // auto-calc amount when quantity/price change
  const recalc = () => {
    const q = parseFloat(form.quantity.value) || 0;
    const p = parseFloat(form.price.value) || 0;
    if (q && p) form.amount.value = (q * p).toFixed(2);
  };
  form.quantity.addEventListener("input", recalc);
  form.price.addEventListener("input", recalc);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = {};
    for (const el of form.elements) {
      if (!el.name) continue;
      data[el.name] = el.value === "" ? null : el.value;
    }
    try {
      if (isEdit) await window.API.sales.update(record.id, data);
      else        await window.API.sales.create(data);
      backdrop.remove();
      posSales();
    } catch (err) {
      alert("Save failed: " + JSON.stringify(err.data || err.message));
    }
  });
}

/* ---------------- Products ---------------- */
async function posProducts() {
  const wrap = document.getElementById("productsTable");
  wrap.innerHTML = `<p class="muted">Loading…</p>`;
  await loadAll();

  const render = (rows) => {
    wrap.innerHTML = rows.length ? `
      <table class="data-table">
        <thead>
          <tr><th>Name</th><th>SKU</th><th>Price</th><th>Stock</th><th>Category</th><th></th></tr>
        </thead>
        <tbody>${rows.map(p => `
          <tr>
            <td>${p.name}</td>
            <td>${p.sku}</td>
            <td>${money(p.price)}</td>
            <td>${p.stock}</td>
            <td>${p.category || "—"}</td>
            <td style="white-space:nowrap;">
              <button class="btn-outline" data-edit="${p.id}" style="padding:.3rem .7rem;font-size:.8rem;">Edit</button>
              <button class="btn-danger"  data-del="${p.id}" style="padding:.3rem .7rem;font-size:.8rem;">Delete</button>
            </td>
          </tr>`).join("")}
        </tbody>
      </table>` : `<p class="muted">No products yet.</p>`;

    wrap.querySelectorAll("[data-edit]").forEach(b =>
      b.addEventListener("click", () => {
        const row = POS_CACHE.products.find(x => String(x.id) === b.dataset.edit);
        openProductForm(row);
      })
    );
    wrap.querySelectorAll("[data-del]").forEach(b =>
      b.addEventListener("click", async () => {
        if (!confirm("Delete this product?")) return;
        try { await window.API.deleteProduct(b.dataset.del); posProducts(); }
        catch (e) { alert("Delete failed: " + e.message); }
      })
    );
  };

  render(POS_CACHE.products);
  document.getElementById("addProductBtn").onclick = () => openProductForm(null);

  const filter = document.getElementById("productsFilter");
  filter.oninput = () => {
    const q = filter.value.toLowerCase();
    render(POS_CACHE.products.filter(p =>
      Object.values(p).some(v => String(v ?? "").toLowerCase().includes(q))
    ));
  };
}

function openProductForm(record) {
  const isEdit = !!record;
  const backdrop = document.createElement("div");
  backdrop.className = "modal-backdrop";
  backdrop.style.cssText =
    "position:fixed;inset:0;background:rgba(0,0,0,.45);display:flex;align-items:center;" +
    "justify-content:center;z-index:100;padding:1rem;";

  const modal = document.createElement("div");
  modal.style.cssText =
    "background:#fff;border-radius:12px;max-width:520px;width:100%;" +
    "padding:1.5rem;box-shadow:0 20px 40px rgba(0,0,0,.25);";

  modal.innerHTML = `
    <h3>${isEdit ? "Edit" : "New"} Product</h3>
    <form class="form" id="prodForm">
      <label>Name<input name="name" required value="${record?.name || ""}"></label>
      <label>Description<textarea name="description" rows="2">${record?.description || ""}</textarea></label>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">
        <label>Price<input type="number" step="any" name="price" required value="${record?.price || ""}"></label>
        <label>Stock<input type="number" name="stock" value="${record?.stock ?? 0}"></label>
      </div>
      <label>Category<input name="category" value="${record?.category || ""}"></label>
      <label>Image URL<input name="image_url" value="${record?.image_url || ""}"></label>
      <div style="display:flex;gap:.5rem;margin-top:1rem;">
        <button type="submit" class="btn-primary">Save</button>
        <button type="button" class="btn-outline" id="cancelBtn">Cancel</button>
      </div>
    </form>`;

  backdrop.appendChild(modal);
  document.body.appendChild(backdrop);

  const form = modal.querySelector("#prodForm");
  form.querySelector("#cancelBtn").onclick = () => backdrop.remove();

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = {};
    for (const el of form.elements) {
      if (!el.name) continue;
      data[el.name] = el.value === "" ? null : el.value;
    }
    try {
      if (isEdit) await window.API.updateProduct(record.id, data);
      else        await window.API.createProduct(data);
      backdrop.remove();
      posProducts();
    } catch (err) {
      alert("Save failed: " + JSON.stringify(err.data || err.message));
    }
  });
}

/* ---------------- Customers (derived from sales) ---------------- */
async function posCustomers() {
  const wrap = document.getElementById("customersTable");
  wrap.innerHTML = `<p class="muted">Loading…</p>`;
  await loadAll();

  const map = new Map();
  POS_CACHE.sales.forEach(s => {
    const name = (s.customer || "Walk-in").trim();
    if (!map.has(name)) map.set(name, { name, count: 0, total: 0, lastDate: s.date });
    const c = map.get(name);
    c.count++;
    c.total += parseFloat(s.amount || 0);
    if (s.date > c.lastDate) c.lastDate = s.date;
  });
  const rows = Array.from(map.values()).sort((a, b) => b.total - a.total);

  const render = (list) => {
    wrap.innerHTML = list.length ? `
      <table class="data-table">
        <thead><tr><th>Customer</th><th>Purchases</th><th>Total Spent</th><th>Last Purchase</th></tr></thead>
        <tbody>${list.map(c => `
          <tr>
            <td>${c.name}</td>
            <td>${c.count}</td>
            <td>${money(c.total)}</td>
            <td>${c.lastDate}</td>
          </tr>`).join("")}
        </tbody>
      </table>` : `<p class="muted">No customers yet.</p>`;
  };

  render(rows);

  const filter = document.getElementById("customersFilter");
  filter.oninput = () => {
    const q = filter.value.toLowerCase();
    render(rows.filter(c => c.name.toLowerCase().includes(q)));
  };
}

/* ---------------- Purchases ---------------- */
async function posPurchases() {
  const wrap = document.getElementById("purchasesTable");
  wrap.innerHTML = `<p class="muted">Loading…</p>`;
  await loadAll();

  const render = (rows) => {
    wrap.innerHTML = rows.length ? `
      <table class="data-table">
        <thead>
          <tr><th>Date</th><th>Item</th><th>Qty</th><th>Supplier</th><th>Cost</th><th></th></tr>
        </thead>
        <tbody>${rows.map(p => `
          <tr>
            <td>${p.purchase_date}</td>
            <td>${p.item}</td>
            <td>${p.quantity || "—"}</td>
            <td>${p.supplier || "—"}</td>
            <td>${money(p.cost)}</td>
            <td style="white-space:nowrap;">
              <button class="btn-outline" data-edit="${p.id}" style="padding:.3rem .7rem;font-size:.8rem;">Edit</button>
              <button class="btn-danger"  data-del="${p.id}" style="padding:.3rem .7rem;font-size:.8rem;">Delete</button>
            </td>
          </tr>`).join("")}
        </tbody>
      </table>` : `<p class="muted">No purchases yet.</p>`;

    wrap.querySelectorAll("[data-edit]").forEach(b =>
      b.addEventListener("click", () => {
        const row = POS_CACHE.purchases.find(x => String(x.id) === b.dataset.edit);
        openPurchaseForm(row);
      })
    );
    wrap.querySelectorAll("[data-del]").forEach(b =>
      b.addEventListener("click", async () => {
        if (!confirm("Delete this purchase?")) return;
        try { await window.API.purchases.remove(b.dataset.del); posPurchases(); }
        catch (e) { alert("Delete failed: " + e.message); }
      })
    );
  };

  render(POS_CACHE.purchases);
  document.getElementById("addPurchaseBtn").onclick = () => openPurchaseForm(null);

  const filter = document.getElementById("purchasesFilter");
  filter.oninput = () => {
    const q = filter.value.toLowerCase();
    render(POS_CACHE.purchases.filter(p =>
      Object.values(p).some(v => String(v ?? "").toLowerCase().includes(q))
    ));
  };
}

function openPurchaseForm(record) {
  const isEdit = !!record;
  const backdrop = document.createElement("div");
  backdrop.className = "modal-backdrop";
  backdrop.style.cssText =
    "position:fixed;inset:0;background:rgba(0,0,0,.45);display:flex;align-items:center;" +
    "justify-content:center;z-index:100;padding:1rem;";

  const modal = document.createElement("div");
  modal.style.cssText =
    "background:#fff;border-radius:12px;max-width:520px;width:100%;" +
    "padding:1.5rem;box-shadow:0 20px 40px rgba(0,0,0,.25);";

  const today = new Date().toISOString().slice(0, 10);
  modal.innerHTML = `
    <h3>${isEdit ? "Edit" : "New"} Purchase</h3>
    <form class="form" id="purchForm">
      <label>Date<input type="date" name="purchase_date" required value="${record?.purchase_date || today}"></label>
      <label>Item<input name="item" required value="${record?.item || ""}"></label>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">
        <label>Quantity<input name="quantity" value="${record?.quantity || ""}"></label>
        <label>Cost<input type="number" step="any" name="cost" value="${record?.cost || ""}"></label>
      </div>
      <label>Supplier<input name="supplier" value="${record?.supplier || ""}"></label>
      <label>Notes<textarea name="notes" rows="2">${record?.notes || ""}</textarea></label>
      <div style="display:flex;gap:.5rem;margin-top:1rem;">
        <button type="submit" class="btn-primary">Save</button>
        <button type="button" class="btn-outline" id="cancelBtn">Cancel</button>
      </div>
    </form>`;

  backdrop.appendChild(modal);
  document.body.appendChild(backdrop);

  const form = modal.querySelector("#purchForm");
  form.querySelector("#cancelBtn").onclick = () => backdrop.remove();

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = {};
    for (const el of form.elements) {
      if (!el.name) continue;
      data[el.name] = el.value === "" ? null : el.value;
    }
    try {
      if (isEdit) await window.API.purchases.update(record.id, data);
      else        await window.API.purchases.create(data);
      backdrop.remove();
      posPurchases();
    } catch (err) {
      alert("Save failed: " + JSON.stringify(err.data || err.message));
    }
  });
}

/* ---------------- Reports ---------------- */
async function posReports() {
  await loadAll();

  // default: last 30 days
  const from = document.getElementById("reportFrom");
  const to = document.getElementById("reportTo");
  if (!from.value) {
    const d = new Date(); d.setDate(d.getDate() - 30);
    from.value = d.toISOString().slice(0, 10);
  }
  if (!to.value) to.value = new Date().toISOString().slice(0, 10);

  document.getElementById("runReportBtn").onclick = () => renderReport();

  if (!document.getElementById("reportsStats").dataset.done) {
    renderReport();
  }
}

function renderReport() {
  const fromStr = document.getElementById("reportFrom").value;
  const toStr   = document.getElementById("reportTo").value;
  const statsEl = document.getElementById("reportsStats");
  const byProductEl = document.getElementById("reportsByProduct");

  const inRange = (d) => (!fromStr || d >= fromStr) && (!toStr || d <= toStr);

  const sales = POS_CACHE.sales.filter(s => inRange(s.date));
  const purchases = POS_CACHE.purchases.filter(p => inRange(p.purchase_date));

  const revenue = sales.reduce((s, x) => s + parseFloat(x.amount || 0), 0);
  const cost    = purchases.reduce((s, x) => s + parseFloat(x.cost || 0), 0);
  const profit  = revenue - cost;

  statsEl.innerHTML = `
    <div class="stat-card"><h3>${sales.length}</h3><p>Sales</p></div>
    <div class="stat-card"><h3>${money(revenue)}</h3><p>Revenue</p></div>
    <div class="stat-card"><h3>${money(cost)}</h3><p>Purchases</p></div>
    <div class="stat-card"><h3>${money(profit)}</h3><p>Profit</p></div>
  `;

  const map = new Map();
  sales.forEach(s => {
    const p = s.product || "Unknown";
    if (!map.has(p)) map.set(p, { product: p, qty: 0, total: 0 });
    const m = map.get(p);
    m.qty += parseFloat(s.quantity || 0);
    m.total += parseFloat(s.amount || 0);
  });
  const rows = Array.from(map.values()).sort((a, b) => b.total - a.total);

  byProductEl.innerHTML = rows.length ? `
    <table class="data-table">
      <thead><tr><th>Product</th><th>Quantity Sold</th><th>Revenue</th></tr></thead>
      <tbody>${rows.map(r => `
        <tr><td>${r.product}</td><td>${r.qty}</td><td>${money(r.total)}</td></tr>
      `).join("")}
      </tbody>
    </table>` : `<p class="muted">No sales in this range.</p>`;

  statsEl.dataset.done = "1";
}

/* ---------------- Settings ---------------- */
function posSettings() {
  const el = document.getElementById("settingsArea");
  const s = JSON.parse(localStorage.getItem(POS_USER_KEY) || "{}");

  el.innerHTML = `
    <div class="card" style="max-width:520px;">
      <h3>POS Settings</h3>
      <form id="posSettingsForm" class="form">
        <label>Business Name<input name="business" value="${s.business || "FarmKonnect POS"}"></label>
        <label>Currency<input name="currency" value="${s.currency || "KSh"}"></label>
        <label>Tax Rate (%)<input type="number" step="any" name="tax" value="${s.tax ?? 0}"></label>
        <label>Receipt Footer<input name="footer" value="${s.footer || "Thank you for your business!"}"></label>
        <div style="display:flex;gap:.5rem;margin-top:1rem;">
          <button type="submit" class="btn-primary">Save Settings</button>
        </div>
        <p id="settingsMsg" class="form-msg"></p>
      </form>
    </div>`;

  el.querySelector("#posSettingsForm").addEventListener("submit", (e) => {
    e.preventDefault();
    const f = e.target;
    localStorage.setItem(POS_USER_KEY, JSON.stringify({
      business: f.business.value,
      currency: f.currency.value,
      tax: f.tax.value,
      footer: f.footer.value,
    }));
    const msg = el.querySelector("#settingsMsg");
    msg.className = "form-msg success";
    msg.textContent = "Settings saved.";
    setTimeout(() => { msg.textContent = ""; }, 2000);
  });
}