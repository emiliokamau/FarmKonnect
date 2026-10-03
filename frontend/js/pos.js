/* POS Page Controller */
document.addEventListener("DOMContentLoaded", () => {
  if (document.body.dataset.page !== "pos") return;
  guardAuth();

  const user = getUser();
  document.getElementById("posUser").textContent = user?.first_name || user?.username || "User";

  document.querySelectorAll("[data-pos-section]").forEach(link => {
    link.addEventListener("click", e => {
      e.preventDefault();
      showPosSection(link.dataset.posSection);
    });
  });

  document.querySelectorAll("[data-logout]").forEach(b => b.addEventListener("click", async () => {
    await API.logout(); logout();
  }));

  showPosSection("dashboard");
});

function showPosSection(name) {
  document.querySelectorAll(".content-section").forEach(s => s.classList.remove("active"));
  document.querySelector(`#pos-${name}`)?.classList.add("active");
  document.querySelectorAll("[data-pos-section]").forEach(l => l.classList.toggle("active", l.dataset.posSection === name));
  const loaders = {
    dashboard: posDashboard,
    sales: posSales,
    products: posProducts,
    customers: posCustomers,
    reports: posReports,
    settings: posSettings,
  };
  loaders[name]?.();
}

async function posDashboard() {
  const el = document.getElementById("posStats");
  try {
    const [orders, products] = await Promise.all([API.orders(), API.products()]);
    const oList = orders.results || orders;
    const pList = products.results || products;
    const revenue = oList.reduce((s, o) => s + parseFloat(o.total || 0), 0);
    el.innerHTML = `
      <div class="stat-card"><h3>${oList.length}</h3><p>Total Sales</p></div>
      <div class="stat-card"><h3>KSh ${revenue.toFixed(2)}</h3><p>Revenue</p></div>
      <div class="stat-card"><h3>${pList.length}</h3><p>Products</p></div>
      <div class="stat-card"><h3>${pList.filter(p => p.stock <= 5).length}</h3><p>Low Stock</p></div>
    `;
  } catch {
    el.innerHTML = `<p class="muted">Unable to load.</p>`;
  }
}

async function posSales() {
  const el = document.getElementById("salesTable");
  el.innerHTML = "<p class='muted'>Loading...</p>";
  try {
    const res = await API.orders();
    const list = res.results || res;
    el.innerHTML = `
      <table class="data-table">
        <thead><tr><th>#</th><th>Customer</th><th>Total</th><th>Status</th><th>Date</th><th></th></tr></thead>
        <tbody>${list.map(o => `
          <tr>
            <td>${o.id}</td>
            <td>${o.customer_name || "-"}</td>
            <td>KSh ${parseFloat(o.total).toFixed(2)}</td>
            <td><span class="badge badge-${o.status}">${o.status}</span></td>
            <td>${new Date(o.created_at).toLocaleDateString()}</td>
            <td>${o.status === "pending" ? `<button class="btn-primary" onclick="markPaid(${o.id})">Mark Paid</button>` : ""}</td>
          </tr>`).join("") || `<tr><td colspan="6" class="muted">No orders yet.</td></tr>`}
        </tbody>
      </table>`;
  } catch {
    el.innerHTML = "<p class='muted'>Unable to load.</p>";
  }
}
async function markPaid(id) { await API.payOrder(id); posSales(); }

async function posProducts() {
  const el = document.getElementById("productsTable");
  el.innerHTML = "<p class='muted'>Loading...</p>";
  try {
    const res = await API.products();
    const list = res.results || res;
    el.innerHTML = `
      <div class="mb-1"><button class="btn-primary" onclick="addProductPrompt()">+ New Product</button></div>
      <table class="data-table">
        <thead><tr><th>Name</th><th>SKU</th><th>Price</th><th>Stock</th><th>Category</th><th></th></tr></thead>
        <tbody>${list.map(p => `
          <tr>
            <td>${p.name}</td>
            <td>${p.sku}</td>
            <td>KSh ${parseFloat(p.price).toFixed(2)}</td>
            <td>${p.stock}</td>
            <td>${p.category || "-"}</td>
            <td><button class="btn-danger" onclick="removeProduct(${p.id})">Delete</button></td>
          </tr>`).join("") || `<tr><td colspan="6" class="muted">No products.</td></tr>`}
        </tbody>
      </table>`;
  } catch {
    el.innerHTML = "<p class='muted'>Unable to load (requires admin role).</p>";
  }
}
async function addProductPrompt() {
  const name = prompt("Product name"); if (!name) return;
  const price = prompt("Price"); if (!price) return;
  const stock = prompt("Stock", "0") || "0";
  const category = prompt("Category") || "";
  try {
    await API.createProduct({ name, price, stock, category });
    posProducts();
  } catch (e) { alert(formatErr(e)); }
}
async function removeProduct(id) {
  if (!confirm("Delete this product?")) return;
  try { await API.deleteProduct(id); posProducts(); }
  catch (e) { alert(formatErr(e)); }
}

function posCustomers() {
  const el = document.getElementById("customersTable");
  const customers = JSON.parse(localStorage.getItem("fk_customers") || "[]");
  el.innerHTML = `
    <div class="mb-1"><button class="btn-primary" onclick="addCustomerPrompt()">+ New Customer</button></div>
    <table class="data-table">
      <thead><tr><th>Name</th><th>Phone</th><th>Email</th><th></th></tr></thead>
      <tbody>${customers.map((c, i) => `
        <tr><td>${c.name}</td><td>${c.phone}</td><td>${c.email || "-"}</td>
            <td><button class="btn-danger" onclick="removeCustomer(${i})">Delete</button></td></tr>
      `).join("") || `<tr><td colspan="4" class="muted">No customers.</td></tr>`}
      </tbody>
    </table>`;
}
function addCustomerPrompt() {
  const name = prompt("Customer name"); if (!name) return;
  const phone = prompt("Phone"); if (!phone) return;
  const email = prompt("Email") || "";
  const arr = JSON.parse(localStorage.getItem("fk_customers") || "[]");
  arr.push({ name, phone, email });
  localStorage.setItem("fk_customers", JSON.stringify(arr));
  posCustomers();
}
function removeCustomer(i) {
  const arr = JSON.parse(localStorage.getItem("fk_customers") || "[]");
  arr.splice(i, 1);
  localStorage.setItem("fk_customers", JSON.stringify(arr));
  posCustomers();
}

async function posReports() {
  const el = document.getElementById("reportsArea");
  const res = await API.orders();
  const list = res.results || res;
  const byStatus = list.reduce((a, o) => { a[o.status] = (a[o.status] || 0) + 1; return a; }, {});
  el.innerHTML = `
    <div class="stat-card"><h3>${list.length}</h3><p>Total Orders</p></div>
    ${Object.entries(byStatus).map(([k, v]) => `<div class="stat-card"><h3>${v}</h3><p>${k}</p></div>`).join("")}
  `;
}

function posSettings() {
  const el = document.getElementById("settingsArea");
  const s = JSON.parse(localStorage.getItem("fk_pos_settings") || "{}");
  el.innerHTML = `
    <form id="settingsForm" class="form">
      <label>Business Name <input name="business" value="${s.business || 'FarmKonnect POS'}"></label>
      <label>Currency <input name="currency" value="${s.currency || 'KSh'}"></label>
      <label>Tax (%) <input name="tax" type="number" value="${s.tax || 0}"></label>
      <button class="btn-primary">Save</button>
    </form>`;
  document.getElementById("settingsForm").addEventListener("submit", e => {
    e.preventDefault();
    const f = e.target;
    localStorage.setItem("fk_pos_settings", JSON.stringify({
      business: f.business.value, currency: f.currency.value, tax: f.tax.value,
    }));
    alert("Saved.");
  });
}