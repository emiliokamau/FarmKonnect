/**
 * FarmKonnect API client
 */

const API_BASE = window.RENDER_EXTERNAL_URL ? `${window.RENDER_EXTERNAL_URL}/api` : "/api";
const TOKEN_KEY = "fk_token";
const USER_KEY  = "fk_user";

function getToken()    { return localStorage.getItem(TOKEN_KEY); }
function setToken(t)   { t ? localStorage.setItem(TOKEN_KEY, t)
                          : localStorage.removeItem(TOKEN_KEY); }
function getUser()     { const r = localStorage.getItem(USER_KEY);
                         return r ? JSON.parse(r) : null; }
function setUser(u)    { u ? localStorage.setItem(USER_KEY, JSON.stringify(u))
                          : localStorage.removeItem(USER_KEY); }
function isLoggedIn()  { return !!getToken(); }
function logout()      { setToken(null); setUser(null); window.location.href = "login.html"; }

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

/* Helper that builds standard CRUD for a resource path */
function crud(base) {
  return {
    list:   ()       => apiFetch(`${base}`),
    get:    (id)     => apiFetch(`${base}${id}/`),
    create: (data)   => apiFetch(`${base}`,        { method: "POST",   body: data }),
    update: (id, d)  => apiFetch(`${base}${id}/`,  { method: "PATCH",  body: d }),
    remove: (id)     => apiFetch(`${base}${id}/`,  { method: "DELETE" }),
  };
}

const API = {
  // auth
  register:       (p) => apiFetch("/auth/register/",     { method: "POST", body: p, auth: false }),
  requestOtp:     (i) => apiFetch("/auth/request-otp/",  { method: "POST", body: { phone: i, email: i }, auth: false }),
  verifyOtp:      (i, otp) => apiFetch("/auth/verify-otp/", { method: "POST",
                                                              body: { phone: i, email: i, otp },
                                                              auth: false }),
  loginPassword:  (p) => apiFetch("/auth/login/",        { method: "POST", body: p, auth: false }),
  logout:         ()  => apiFetch("/auth/logout/",       { method: "POST" }).catch(() => {}),
  me:             ()  => apiFetch("/auth/me/"),
  myProfile:      ()  => apiFetch("/farmer/profile/"),
  saveProfile:    (p) => apiFetch("/farmer/profile/",    { method: "PUT", body: p }),

  // reference
  counties:       ()  => apiFetch("/counties/",    { auth: false }),
  commodities:    ()  => apiFetch("/commodities/", { auth: false }),
  prices:         (p = "") => apiFetch(`/prices/${p}`, { auth: false }),
  priceTrends:    (cid) => apiFetch(`/prices/trends/${cid ? `?commodity=${cid}` : ""}`, { auth: false }),
  // Global & Local Events — search/filter, summary counts, attendance details
  events: {
    all:       ()                => apiFetch("/events/?window=all", { auth: false }),
    list:      (query = "")      => apiFetch(`/events/${query ? `?${query}` : ""}`, { auth: false }),
    summary:   ()                => apiFetch("/events/summary/", { auth: false }),
    detail:    (id)              => apiFetch(`/events/${id}/`, { auth: false }),
    join:      (id, payload = {}) => apiFetch(`/events/${id}/join/`, {
                                      method: "POST", body: payload, auth: isLoggedIn(),
                                    }),
    joinInfo:  (id)              => apiFetch(`/events/${id}/join/`, { auth: isLoggedIn() }),
    register:  (payload)         => apiFetch("/event-registrations/", { method: "POST", body: payload, auth: isLoggedIn() }),
    registrations: ()            => apiFetch("/event-registrations/"),
    cancel:    (id, reference)   => apiFetch(`/event-registrations/${id}/cancel/`, {
                                      method: "POST", body: { reference }, auth: isLoggedIn(),
                                    }),
  },

  // advisories
  advisories:     ()  => apiFetch("/advisories/"),
  createAdvisory: (p) => apiFetch("/advisories/", { method: "POST", body: p }),

  // marketplace
  products:       ()      => apiFetch("/products/", { auth: false }),
  createProduct:  (p)     => apiFetch("/products/",          { method: "POST",  body: p }),
  updateProduct:  (id, p) => apiFetch(`/products/${id}/`,    { method: "PATCH", body: p }),
  deleteProduct:  (id)    => apiFetch(`/products/${id}/`,    { method: "DELETE" }),
  listings:       ()      => apiFetch("/listings/", { auth: false }),
  createListing:  (p)     => apiFetch("/listings/", { method: "POST", body: p }),

  orders:         ()  => apiFetch("/orders/"),
  createOrder:    (o) => apiFetch("/orders/",          { method: "POST", body: o }),
  payOrder:       (id) => apiFetch(`/orders/${id}/pay/`, { method: "POST" }),

  pricesCsv:      ()  => apiFetch("/prices_csv/", { auth: false }),

  // ---- FMS (all CRUD) ----
  farms:      crud("/farms/"),
  crops:      crud("/crops/"),
  plantings:  crud("/plantings/"),
  inputs:     crud("/farm-inputs/"),
  diseases:   crud("/diseases/"),
  harvests:   crud("/harvests/"),
  inventory:  crud("/inventory/"),
  sales:      crud("/sales/"),
  purchases:  crud("/purchases/"),
  weather:    crud("/weather/"),
  visits:     crud("/visits/"),
  finance:    crud("/finance/"),

  // ---- Crop & plant photos (multipart uploads) ----
  diseasePhotos: {
    list:   (reportId) => apiFetch(`/disease-photos/${reportId ? `?report=${reportId}` : ""}`),
    add:    (data)     => apiFetch("/disease-photos/", { method: "POST", body: data }),
    remove: (id)       => apiFetch(`/disease-photos/${id}/`, { method: "DELETE" }),
  },
  /** Attach extra angles to an existing report: files under `images`. */
  addDiseasePhotos: (reportId, formData) =>
    apiFetch(`/diseases/${reportId}/add_photos/`, { method: "POST", body: formData }),
  /** Queue a report for disease analysis. */
  analyseDisease:   (reportId) => apiFetch(`/diseases/${reportId}/analyse/`, { method: "POST" }),
  pendingDiseases:  ()         => apiFetch("/diseases/pending/"),
};

window.getToken   = getToken;
window.setToken   = setToken;
window.getUser    = getUser;
window.setUser    = setUser;
window.isLoggedIn = isLoggedIn;
window.logout     = logout;
window.apiFetch   = apiFetch;
window.API        = API;