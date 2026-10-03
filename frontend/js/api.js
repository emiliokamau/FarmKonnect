/**
 * FarmKonnect API client
 * All frontend calls funnel through this file.
 * Adjust API_BASE to point to your DRF backend.
 */
const API_BASE = "http://127.0.0.1:8000/api";

const TOKEN_KEY = "fk_token";
const USER_KEY = "fk_user";

/* ------------------ Token helpers ------------------ */
function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}
function setToken(t) {
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
}
function getUser() {
  const raw = localStorage.getItem(USER_KEY);
  return raw ? JSON.parse(raw) : null;
}
function setUser(u) {
  if (u) localStorage.setItem(USER_KEY, JSON.stringify(u));
  else localStorage.removeItem(USER_KEY);
}
function isLoggedIn() {
  return !!getToken();
}
function logout() {
  setToken(null);
  setUser(null);
  window.location.href = "login.html";
}

/* ------------------ Core fetch ------------------ */
async function apiFetch(path, { method = "GET", body, headers = {}, auth = true } = {}) {
  const opts = { method, headers: { ...headers } };
  if (body !== undefined && !(body instanceof FormData)) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  } else if (body instanceof FormData) {
    opts.body = body;
  }
  if (auth) {
    const t = getToken();
    if (t) opts.headers["Authorization"] = `Token ${t}`;
  }

  const res = await fetch(`${API_BASE}${path}`, opts);
  const text = await res.text();
  let data;
  try { data = text ? JSON.parse(text) : {}; } catch { data = { raw: text }; }
  if (!res.ok) {
    const err = new Error(data.detail || `HTTP ${res.status}`);
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

/* ------------------ Endpoints ------------------ */
const API = {
  // ---- auth ----
  register: (payload) => apiFetch("/auth/register/", { method: "POST", body: payload, auth: false }),
  requestOtp: (phone) => apiFetch("/auth/request-otp/", { method: "POST", body: { phone }, auth: false }),
  verifyOtp: (phone, otp) => apiFetch("/auth/verify-otp/", { method: "POST", body: { phone, otp }, auth: false }),
  loginPassword: (payload) => apiFetch("/auth/login/", { method: "POST", body: payload, auth: false }),
  logout: () => apiFetch("/auth/logout/", { method: "POST" }).catch(() => {}),
  me: () => apiFetch("/auth/me/"),

  // ---- reference ----
  counties: () => apiFetch("/counties/", { auth: false }),
  commodities: () => apiFetch("/commodities/", { auth: false }),
  prices: (params = "") => apiFetch(`/prices/${params}`, { auth: false }),
  priceTrends: (commodityId) => apiFetch(`/prices/trends/${commodityId ? `?commodity=${commodityId}` : ""}`, { auth: false }),
  events: (type) => apiFetch(`/events/${type ? `?event_type=${type}` : ""}`, { auth: false }),

  // ---- advisories ----
  advisories: () => apiFetch("/advisories/"),
  createAdvisory: (payload) => apiFetch("/advisories/", { method: "POST", body: payload }),

  // ---- POS / Marketplace ----
  products: () => apiFetch("/products/", { auth: false }),
  createProduct: (p) => apiFetch("/products/", { method: "POST", body: p }),
  updateProduct: (id, p) => apiFetch(`/products/${id}/`, { method: "PATCH", body: p }),
  deleteProduct: (id) => apiFetch(`/products/${id}/`, { method: "DELETE" }),

  listings: () => apiFetch("/listings/", { auth: false }),
  createListing: (p) => apiFetch("/listings/", { method: "POST", body: p }),

  orders: () => apiFetch("/orders/"),
  createOrder: (o) => apiFetch("/orders/", { method: "POST", body: o }),
  payOrder: (id) => apiFetch(`/orders/${id}/pay/`, { method: "POST" }),

  // ---- csv ----
  pricesCsv: () => apiFetch("/prices_csv/", { auth: false }),
};