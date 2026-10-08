/**
 * FarmKonnect — Global & Local Events
 *
 * One page that lists worldwide and nearby agricultural events, lets a farmer
 * search/filter them, and gives a single-click path to attend: Google Meet,
 * Zoom, WhatsApp, livestream, phone dial-in or an in-person venue.
 *
 * Hosts control everything from the Django admin (Event + EventRegistration).
 */
document.addEventListener("DOMContentLoaded", () => {
  const state = {
    events: [],
    demo: false,
    scope: "",
    search: "",
    type: "",
    joinMode: "",
    cost: "",
    online: false,
    past: false,
    registered: loadRegistered(), // { eventId: {reference, ...} } remembered locally
  };

  const el = (id) => document.getElementById(id);
  const grid = el("evGrid");

  /* ------------------------------------------------------------------
     Small helpers
  ------------------------------------------------------------------ */
  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function loadRegistered() {
    try { return JSON.parse(localStorage.getItem("fk_event_registrations") || "{}"); }
    catch { return {}; }
  }
  function saveRegistered() {
    try { localStorage.setItem("fk_event_registrations", JSON.stringify(state.registered)); } catch { /* ignore */ }
  }

  function formatDateParts(iso) {
    const d = new Date(iso);
    if (isNaN(d)) return { day: "–", month: "", weekday: "", full: "Date to be announced", time: "" };
    return {
      day: d.getDate(),
      month: d.toLocaleString(undefined, { month: "short" }).toUpperCase(),
      weekday: d.toLocaleString(undefined, { weekday: "short" }),
      full: d.toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" }),
      time: d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" }),
    };
  }

  function dateRangeText(ev) {
    const start = formatDateParts(ev.start_date);
    if (!ev.end_date) return `${start.full} · ${start.time}`;
    const end = new Date(ev.end_date);
    if (isNaN(end)) return `${start.full} · ${start.time}`;
    const sameDay = new Date(ev.start_date).toDateString() === end.toDateString();
    return sameDay
      ? `${start.full} · ${start.time}`
      : `${start.full} → ${end.toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" })}`;
  }

  const JOIN_ICONS = {
    google_meet: "🎥", zoom: "🎥", teams: "🎥", whatsapp: "💬",
    livestream: "📺", website: "🌐", in_person: "📍", phone: "📞",
  };

  function daysUntil(iso) {
    const d = new Date(iso);
    if (isNaN(d)) return null;
    return Math.ceil((d - new Date()) / 86400000);
  }

  /* ------------------------------------------------------------------
     Access details — the shared block used by the modal and the card
  ------------------------------------------------------------------ */
  function accessDetailsHtml(ev, opts = {}) {
    const icon = JOIN_ICONS[ev.join_mode] || "🌐";
    const label = escapeHtml(ev.join_mode_display || "Details from host");
    const link = ev.join_link || "";
    const code = ev.join_code || "";
    const rows = [];

    rows.push(`<div class="ev-access-row"><span class="ev-access-icon">${icon}</span>
      <div><strong>${label}</strong>${ev.location ? `<div class="muted ev-small">${escapeHtml(ev.location)}</div>` : ""}</div></div>`);

    if (link && ev.join_mode !== "in_person") {
      rows.push(`<div class="ev-access-row"><span class="ev-access-icon">🔗</span>
        <div class="ev-access-link"><a href="${escapeHtml(link)}" target="_blank" rel="noopener">${escapeHtml(link)}</a></div></div>`);
    }
    if (code) {
      rows.push(`<div class="ev-access-row"><span class="ev-access-icon">🔑</span>
        <div>Access code / PIN: <strong>${escapeHtml(code)}</strong></div></div>`);
    }
    if (ev.join_mode === "in_person" && ev.access_link) {
      rows.push(`<div class="ev-access-row"><span class="ev-access-icon">📝</span>
        <div>${escapeHtml(ev.access_link)}</div></div>`);
    }
    if (ev.registration_url && (!link || opts.alwaysShowRegistration)) {
      rows.push(`<div class="ev-access-row"><span class="ev-access-icon">🌐</span>
        <div><a href="${escapeHtml(ev.registration_url)}" target="_blank" rel="noopener">Host registration page</a></div></div>`);
    }
    if (ev.source_url) {
      rows.push(`<div class="ev-access-row ev-access-source"><span class="ev-access-icon">ℹ️</span>
        <div class="muted ev-small">Details per host — <a href="${escapeHtml(ev.source_url)}" target="_blank" rel="noopener">open the official event page</a> to confirm dates.</div></div>`);
    }
    return rows.join("");
  }

  function joinButtonLabel(ev) {
    if (ev.is_past) return "View details";
    switch (ev.join_mode) {
      case "google_meet": return "Join via Google Meet";
      case "zoom": return "Join via Zoom";
      case "teams": return "Join via Teams";
      case "whatsapp": return "Join WhatsApp group";
      case "livestream": return "Watch livestream";
      case "in_person": return ev.registration_required ? "Register for a place" : "Get venue details";
      case "phone": return "Get dial-in details";
      default: return "Register on host site";
    }
  }

  /* ------------------------------------------------------------------
     Data loading
  ------------------------------------------------------------------ */
  async function fetchEvents() {
    if (state.demo) return DEMO_EVENTS;

    const params = new URLSearchParams();
    if (state.scope) params.set("scope", state.scope);
    if (state.search) params.set("search", state.search);
    if (state.type) params.set("event_type", state.type);
    if (state.joinMode) params.set("join_mode", state.joinMode);
    if (state.online) params.set("online", "1");
    if (state.cost === "free") params.set("free", "1");
    params.set("window", state.past ? "all" : "upcoming");

    const query = params.toString();
    const res = await API.events.list(query);
    return res.results || res || [];
  }

  async function loadSummary() {
    const box = el("evSummary");
    if (state.demo) {
      box.innerHTML = summaryChips(DEMO_EVENTS);
      return;
    }
    try {
      const s = await API.events.summary();
      box.innerHTML = [
        chip(`${s.total} events still open`),
        chip(`🌍 ${s.global} global`),
        chip(`📍 ${s.local} local`),
        chip(`💻 ${s.online} online`),
        chip(`🆓 ${s.free} free`),
      ].join("");
    } catch {
      box.innerHTML = summaryChips(state.events);
    }
  }

  const chip = (text) => `<span class="ev-chip">${escapeHtml(text)}</span>`;

  function summaryChips(events) {
    return [
      chip(`${events.length} events still open`),
      chip(`🌍 ${events.filter((e) => e.scope === "global").length} global`),
      chip(`📍 ${events.filter((e) => e.scope === "local").length} local`),
      chip(`💻 ${events.filter((e) => e.is_online).length} online`),
    ].join("");
  }

  /* ------------------------------------------------------------------
     Rendering
  ------------------------------------------------------------------ */
  function cardHtml(ev) {
    const d = formatDateParts(ev.start_date);
    const soon = daysUntil(ev.start_date);
    const badges = [
      `<span class="badge ev-scope-${ev.scope}">${ev.scope === "global" ? "🌍 Global" : "📍 Local"}</span>`,
      `<span class="badge ev-badge-plain">${escapeHtml(ev.event_type_display || ev.event_type)}</span>`,
    ];
    if (ev.is_online) badges.push(`<span class="badge ev-badge-plain">💻 Online</span>`);
    if (ev.cost === "free") badges.push(`<span class="badge ev-badge-free">Free</span>`);
    if (ev.cost === "paid") badges.push(`<span class="badge ev-badge-paid">Paid</span>`);
    if (ev.scope === "global" && ev.is_online) badges.push(`<span class="badge ev-badge-anywhere">Attend from anywhere</span>`);
    if (ev.is_past) badges.push(`<span class="badge ev-badge-past">Past</span>`);
    if (ev.is_full) badges.push(`<span class="badge ev-badge-full">Full</span>`);
    if (soon !== null && soon >= 0 && soon <= 7 && !ev.is_past) {
      badges.push(`<span class="badge ev-badge-soon">${soon === 0 ? "Today" : soon === 1 ? "Tomorrow" : `In ${soon} days`}</span>`);
    }

    const place = [ev.region, ev.country].filter(Boolean).join(", ") || ev.location || "Online";
    const mine = state.registered[ev.id];
    const spots = ev.capacity
      ? `<span class="muted ev-small">${ev.registrations_count}/${ev.capacity} registered</span>`
      : "";

    return `
      <article class="card ev-card${ev.is_past ? " ev-card-past" : ""}">
        <div class="ev-card-top">
          <div class="ev-date">
            <span class="ev-date-day">${d.day}</span>
            <span class="ev-date-month">${escapeHtml(d.month)}</span>
          </div>
          <div class="ev-badges">${badges.join("")}</div>
        </div>

        <h3 class="ev-title">${escapeHtml(ev.title)}</h3>
        ${ev.host ? `<p class="ev-host">🏛️ ${escapeHtml(ev.host)}</p>` : ""}

        <p class="ev-meta">📅 ${escapeHtml(dateRangeText(ev))}</p>
        <p class="ev-meta">📍 ${escapeHtml(place)}</p>
        <p class="ev-meta">${JOIN_ICONS[ev.join_mode] || "🌐"} ${escapeHtml(ev.join_mode_display || "Details from host")}</p>

        <p class="ev-desc">${escapeHtml(ev.description || "")}</p>

        ${ev.tag_list && ev.tag_list.length
          ? `<div class="ev-tags">${ev.tag_list.slice(0, 5).map((t) => `<span class="ev-tag">${escapeHtml(t)}</span>`).join("")}</div>`
          : ""}

        ${spots}
        ${mine ? `<p class="ev-mine">✅ Registered — reference <strong>${escapeHtml(mine.reference)}</strong></p>` : ""}

        <div class="ev-actions">
          <button class="btn-primary ev-btn-join" data-join="${ev.id}">${escapeHtml(joinButtonLabel(ev))}</button>
          ${
            ev.is_past
              ? ""
              : mine
                ? `<button class="btn-outline ev-btn-details" data-details="${ev.id}">My access details</button>`
                : `<button class="btn-outline ev-btn-register" data-register="${ev.id}">Register</button>`
          }
        </div>
      </article>`;
  }

  function render() {
    const count = el("evResultCount");
    const filters = el("evActiveFilters");
    const bits = [];
    if (state.scope) bits.push(state.scope === "global" ? "Global" : "Local");
    if (state.search) bits.push(`“${state.search}”`);
    if (state.type) bits.push(el("evType").selectedOptions[0].textContent);
    if (state.joinMode) bits.push(el("evJoinMode").selectedOptions[0].textContent);
    if (state.online) bits.push("Online only");
    if (state.cost === "free") bits.push("Free only");
    if (state.past) bits.push("Including past");
    filters.innerHTML = bits.map((b) => `<span class="ev-filter-pill">${escapeHtml(b)}</span>`).join("");

    if (!state.events.length) {
      count.textContent = "No events found.";
      grid.innerHTML = `
        <div class="ev-empty">
          <p>😕 No events match your search.</p>
          <p class="muted">Try a different keyword, switch to “All events”, or tick “Include past events”.</p>
          <button class="btn-outline" id="evEmptyReset" type="button">Clear all filters</button>
        </div>`;
      const r = el("evEmptyReset");
      if (r) r.addEventListener("click", resetFilters);
      return;
    }

    const sorted = [...state.events].sort((a, b) => new Date(a.start_date) - new Date(b.start_date));
    count.textContent = `${sorted.length} event${sorted.length === 1 ? "" : "s"} found`;
    grid.innerHTML = sorted.map(cardHtml).join("");
    wireCardButtons();
  }

  function wireCardButtons() {
    grid.querySelectorAll("[data-join]").forEach((b) => {
      b.addEventListener("click", () => handleJoin(b.dataset.join, b));
    });
    grid.querySelectorAll("[data-register]").forEach((b) => {
      b.addEventListener("click", () => openRegister(b.dataset.register));
    });
    grid.querySelectorAll("[data-details]").forEach((b) => {
      b.addEventListener("click", () => {
        const ev = findEvent(b.dataset.details);
        if (ev) showExistingRegistration(ev);
      });
    });
  }

  const findEvent = (id) => state.events.find((e) => String(e.id) === String(id));

  /* ------------------------------------------------------------------
     Join flow
  ------------------------------------------------------------------ */
  async function handleJoin(id, button) {
    const ev = findEvent(id);
    if (!ev) return;

    const link = ev.join_link;
    const isOnline = ev.join_mode !== "in_person";

    // Decide whether a place must be booked first.
    let needsRegistration = ev.registration_required && !state.registered[ev.id];
    // A public livestream or a free drop-in never needs a booking.
    if (ev.join_mode === "livestream" && !ev.registration_required) needsRegistration = false;
    if (ev.is_past) needsRegistration = false;

    if (needsRegistration) {
      openRegister(id);
      return;
    }

    if (isOnline && link) {
      window.open(link, "_blank", "noopener");
      flashButton(button, "Opening…");
      return;
    }

    openRegister(id);
  }

  function flashButton(button, text) {
    if (!button) return;
    const original = button.textContent;
    button.textContent = text;
    button.disabled = true;
    setTimeout(() => { button.textContent = original; button.disabled = false; }, 1500);
  }

  /* ------------------------------------------------------------------
     Registration modal
  ------------------------------------------------------------------ */
  const modal = el("evModal");
  const formPane = el("evModalForm");
  const successPane = el("evModalSuccess");

  function openRegister(id) {
    const ev = findEvent(id);
    if (!ev) return;

    formPane.hidden = false;
    successPane.hidden = true;
    el("evFormMsg").textContent = "";
    el("evFormMsg").className = "form-msg";
    el("evEventId").value = ev.id;
    el("evModalTitle").textContent = "Register for this event";
    el("evModalSubtitle").innerHTML =
      `<strong>${escapeHtml(ev.title)}</strong><br>${escapeHtml(dateRangeText(ev))} · ${escapeHtml(ev.location || "Online")}` +
      `${ev.registration_deadline ? `<br>Registration closes ${escapeHtml(new Date(ev.registration_deadline).toLocaleDateString())}` : ""}`;

    // Pre-fill for signed-in farmers.
    const user = typeof getUser === "function" ? getUser() : null;
    if (user) {
      if (!el("evName").value) el("evName").value = [user.first_name, user.last_name].filter(Boolean).join(" ") || user.username || "";
      if (!el("evPhone").value) el("evPhone").value = user.phone || "";
      if (!el("evEmail").value) el("evEmail").value = user.email || "";
    }

    modal.hidden = false;
    document.body.style.overflow = "hidden";
    setTimeout(() => el("evName").focus(), 50);
  }

  function closeModal() {
    modal.hidden = true;
    document.body.style.overflow = "";
  }

  function showExistingRegistration(ev) {
    const saved = state.registered[ev.id];
    if (!saved) return openRegister(ev.id);
    showSuccess(ev, saved);
  }

  function showSuccess(ev, saved) {
    formPane.hidden = true;
    successPane.hidden = false;
    modal.hidden = false;
    document.body.style.overflow = "hidden";

    el("evSuccessFor").innerHTML =
      `Your place at <strong>${escapeHtml(ev.title)}</strong> is saved. ` +
      `${escapeHtml(dateRangeText(ev))} · ${escapeHtml(ev.location || "Online")}`;
    el("evReference").textContent = saved.reference || "—";
    el("evAccessBox").innerHTML = accessDetailsHtml(ev);

    const joinNow = el("evJoinNow");
    if (ev.join_link && ev.join_mode !== "in_person") {
      joinNow.href = ev.join_link;
      joinNow.hidden = false;
      joinNow.textContent = joinButtonLabel(ev);
    } else {
      joinNow.hidden = true;
    }

    el("evSuccessNote").textContent = ev.join_code
      ? "Keep this reference and access code — you'll need them to join."
      : "Keep this reference safe. The host may ask for it at the venue or on the call.";
  }

  async function submitRegistration(event) {
    event.preventDefault();
    const btn = el("evSubmitBtn");
    const msg = el("evFormMsg");
    const id = el("evEventId").value;
    const ev = findEvent(id);
    const payload = {
      event: Number(id),
      full_name: el("evName").value.trim(),
      phone: el("evPhone").value.trim(),
      email: el("evEmail").value.trim(),
      county: el("evCounty").value.trim(),
      organisation: el("evOrg").value.trim(),
      wants_reminder: el("evReminder").checked,
    };

    msg.className = "form-msg";
    msg.textContent = "Saving your place…";
    btn.disabled = true;

    const saved = {
      reference: "FK-LOCAL",
      full_name: payload.full_name,
      phone: payload.phone,
    };

    if (state.demo) {
      saved.reference = "FK-" + Math.random().toString(36).slice(2, 8).toUpperCase();
    } else {
      try {
        const res = await API.events.register(payload);
        saved.reference = res.reference || saved.reference;
        saved.status = res.status;
      } catch (err) {
        btn.disabled = false;
        msg.className = "form-msg error";
        msg.textContent = registrationError(err);
        return;
      }
    }

    state.registered[id] = saved;
    saveRegistered();
    btn.disabled = false;
    render();
    showSuccess(ev, saved);
  }

  function registrationError(err) {
    const data = err && err.data;
    if (data && typeof data === "object") {
      const first = Object.values(data)[0];
      if (Array.isArray(first)) return first[0];
      if (typeof first === "string") return first;
    }
    if (err && err.message) return err.message;
    return "Could not save your registration. Please try again.";
  }

  /* ------------------------------------------------------------------
     Filters
  ------------------------------------------------------------------ */
  function resetFilters() {
    state.scope = "";
    state.search = "";
    state.type = "";
    state.joinMode = "";
    state.cost = "";
    state.online = false;
    state.past = false;
    el("evSearch").value = "";
    el("evType").value = "";
    el("evJoinMode").value = "";
    el("evCost").value = "";
    el("evOnline").checked = false;
    el("evPast").checked = false;
    document.querySelectorAll(".ev-scope-toggle button").forEach((b, i) => b.classList.toggle("active", i === 0));
    refresh();
  }

  let debounce;
  function refresh() {
    grid.innerHTML = `<p class="muted">Loading events…</p>`;
    fetchEvents()
      .then((events) => { state.events = events; render(); })
      .catch((err) => {
        grid.innerHTML = `<div class="ev-empty"><p>⚠️ Could not load events (${escapeHtml(err.message || err)}).</p>
          <button class="btn-outline" id="evRetry" type="button">Try again</button></div>`;
        const r = el("evRetry");
        if (r) r.addEventListener("click", refresh);
      });
  }

  /* ------------------------------------------------------------------
     Wiring
  ------------------------------------------------------------------ */
  el("evSearch").addEventListener("input", (e) => {
    state.search = e.target.value.trim();
    el("evSearchClear").hidden = !state.search;
    clearTimeout(debounce);
    debounce = setTimeout(refresh, 300);
  });

  el("evSearchClear").addEventListener("click", () => {
    el("evSearch").value = "";
    state.search = "";
    el("evSearchClear").hidden = true;
    refresh();
  });

  document.querySelectorAll(".ev-scope-toggle button").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".ev-scope-toggle button").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.scope = btn.dataset.scope || "";
      refresh();
    });
  });

  el("evType").addEventListener("change", (e) => { state.type = e.target.value; refresh(); });
  el("evJoinMode").addEventListener("change", (e) => { state.joinMode = e.target.value; refresh(); });
  el("evCost").addEventListener("change", (e) => { state.cost = e.target.value; refresh(); });
  el("evOnline").addEventListener("change", (e) => { state.online = e.target.checked; refresh(); });
  el("evPast").addEventListener("change", (e) => { state.past = e.target.checked; refresh(); });
  el("evReset").addEventListener("click", resetFilters);

  el("evModalClose").addEventListener("click", closeModal);
  el("evDone").addEventListener("click", closeModal);
  modal.addEventListener("click", (e) => { if (e.target === modal) closeModal(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !modal.hidden) closeModal(); });
  el("evRegisterForm").addEventListener("submit", submitRegistration);

  el("evCopyDetails").addEventListener("click", async () => {
    const text = el("evAccessBox").innerText + "\nReference: " + el("evReference").textContent;
    try {
      await navigator.clipboard.writeText(text);
      el("evCopyDetails").textContent = "Copied ✓";
      setTimeout(() => { el("evCopyDetails").textContent = "Copy details"; }, 1600);
    } catch {
      el("evCopyDetails").textContent = "Copy failed";
      setTimeout(() => { el("evCopyDetails").textContent = "Copy details"; }, 1600);
    }
  });

  // Signed-in state in the navbar.
  const slot = el("evAuthSlot");
  const user = typeof getUser === "function" ? getUser() : null;
  if (user) {
    slot.innerHTML = `<a href="farmer-portal.html">👤 ${escapeHtml(user.first_name || user.username || "My account")}</a>`;
  } else {
    slot.innerHTML = `<a href="login.html">Login</a>
      <a href="register.html" class="btn-primary" style="padding:.45rem 1rem;">Register</a>`;
  }

  /* ==================================================================
     Offline preview data — mirrors the shape of the live API so the page
     stays usable (and demoable) when the backend is down.
  ================================================================== */
  function demoDate(daysAhead) {
    const d = new Date();
    d.setDate(d.getDate() + daysAhead);
    d.setHours(10, 0, 0, 0);
    return d.toISOString();
  }

  const DEMO_EVENTS = [
    {
      id: "d1", title: "Norman E. Borlaug International Dialogue (World Food Prize)",
      host: "World Food Prize Foundation", scope: "global", event_type: "conference",
      event_type_display: "Conference / Summit", join_mode: "livestream",
      join_mode_display: "Livestream / YouTube", is_online: true, cost: "free", cost_display: "Free",
      location: "Des Moines, Iowa, USA + Online", country: "United States", region: "Iowa",
      start_date: demoDate(19), description: "Global dialogue on feeding a growing world: smallholder productivity, climate resilience and agrifood investment. Plenaries are livestreamed free.",
      tags: "food security, policy, smallholder", tag_list: ["food security", "policy", "smallholder"],
      join_link: "", join_code: "", registration_required: false, registration_url: "https://www.worldfoodprize.org/",
      source_url: "https://www.worldfoodprize.org/", registrations_count: 0, capacity: null,
    },
    {
      id: "d2", title: "FAO Global Conference on Smart Farming",
      host: "Food and Agriculture Organization (FAO)", scope: "global", event_type: "conference",
      event_type_display: "Conference / Summit", join_mode: "website",
      join_mode_display: "Register on host website", is_online: true, cost: "free", cost_display: "Free",
      location: "Rome, Italy + Online", country: "Italy", region: "Rome",
      start_date: demoDate(40), description: "Using data and technology for sustainable agrifood systems — AI, IoT, precision agriculture — with a focus on access for small-scale farmers, women and youth.",
      tags: "smart farming, digital, AI", tag_list: ["smart farming", "digital", "AI"],
      join_link: "", join_code: "", registration_required: true,
      registration_url: "https://www.fao.org/events/detail/global-conference-on-smart-farming/en",
      source_url: "https://www.fao.org/events/detail/global-conference-on-smart-farming/en",
      registrations_count: 0, capacity: null,
    },
    {
      id: "d3", title: "Post-Harvest Loss & Storage Management Webinar",
      host: "FarmKonnect Agri Advisory", scope: "local", event_type: "webinar",
      event_type_display: "Webinar", join_mode: "google_meet", join_mode_display: "Google Meet",
      is_online: true, cost: "free", cost_display: "Free", location: "Online", country: "Nigeria",
      start_date: demoDate(4), description: "Cut post-harvest losses: hermetic storage, moisture measurement, aflatoxin prevention and warehouse receipts. Dial-in available.",
      tags: "post-harvest, storage, aflatoxin", tag_list: ["post-harvest", "storage", "aflatoxin"],
      join_link: "https://meet.google.com/fk-postharvest-clinic", join_code: "harvest",
      registration_required: true, registration_url: "https://meet.google.com/fk-postharvest-clinic",
      source_url: "", registrations_count: 128, capacity: 500,
    },
    {
      id: "d4", title: "Free Farmers Capacity Building Workshop (Kwara State)",
      host: "Ayosifam Hub & Kwara ADP", scope: "local", event_type: "training",
      event_type_display: "Training / Workshop", join_mode: "in_person", join_mode_display: "In person (venue)",
      is_online: false, cost: "free", cost_display: "Free", location: "Ilorin, Kwara State, Nigeria",
      country: "Nigeria", region: "Kwara", start_date: demoDate(11),
      description: "Free practical training with the Kwara State ADP: good agronomic practice, input use, record keeping and market access. Places are limited.",
      tags: "training, Kwara, agronomy", tag_list: ["training", "Kwara", "agronomy"],
      join_link: "", join_code: "", registration_required: true,
      registration_url: "https://ayosifamhub.com.ng/", source_url: "https://ayosifamhub.com.ng/",
      registrations_count: 64, capacity: 150,
    },
    {
      id: "d5", title: "Growtech West Africa — Agriculture & Agri-Tech Expo",
      host: "Growtech Events", scope: "local", event_type: "expo",
      event_type_display: "Exhibition / Expo", join_mode: "website", join_mode_display: "Register on host website",
      is_online: false, cost: "free", cost_display: "Free", location: "Landmark Centre, Lagos, Nigeria",
      country: "Nigeria", region: "Lagos", start_date: demoDate(26),
      description: "West Africa's premier agriculture and agri-tech expo: machinery, inputs, irrigation, processing equipment and digital farming tools, with live demos.",
      tags: "expo, agritech, machinery", tag_list: ["expo", "agritech", "machinery"],
      join_link: "", join_code: "", registration_required: true,
      registration_url: "https://www.growtechevents.com/west-africa/",
      source_url: "https://www.growtechevents.com/west-africa/", registrations_count: 0, capacity: null,
    },
    {
      id: "d6", title: "AgriPoultry & Livestock Farmers' Clinic (Lagos)",
      host: "Lagos State Agricultural Development Programme", scope: "local", event_type: "training",
      event_type_display: "Training / Workshop", join_mode: "whatsapp", join_mode_display: "WhatsApp Group",
      is_online: false, cost: "free", cost_display: "Free", location: "Agege, Lagos State, Nigeria",
      country: "Nigeria", region: "Lagos", start_date: demoDate(14),
      description: "Biosecurity, feed formulation with local ingredients, vaccination schedules, record keeping and market-ready production planning.",
      tags: "poultry, livestock, biosecurity", tag_list: ["poultry", "livestock", "biosecurity"],
      join_link: "https://wa.me/2340000000000", join_code: "", registration_required: true,
      registration_url: "https://lagosagric.gov.ng/", source_url: "https://lagosagric.gov.ng/",
      registrations_count: 42, capacity: 100,
    },
  ];

  /* ------------------------------------------------------------------
     Boot — runs last so every helper and the demo data are initialised.
  ------------------------------------------------------------------ */
  (async function boot() {
    const wantsDemo = new URLSearchParams(location.search).get("demo") === "1";
    if (wantsDemo) {
      state.demo = true;
    } else {
      try {
        await API.events.list("window=upcoming");
      } catch {
        state.demo = true;
      }
    }

    if (state.demo) {
      const note = el("evDemoNote");
      note.hidden = false;
      note.innerHTML = "🧪 <strong>Preview mode</strong> — the FarmKonnect API is not reachable from this page, " +
        "so sample events are shown. Start the backend and reload to see live events and real availability.";
    }

    await loadSummary();
    await refresh();

    // Deep link from the portal: events.html?event=12 opens that event's booking.
    const wanted = new URLSearchParams(location.search).get("event");
    if (wanted) {
      const match = findEvent(wanted) || state.events.find((e) => String(e.id) === String(wanted));
      if (match) {
        match.registration_required ? openRegister(match.id) : handleJoin(match.id, null);
      }
    }
  })();
});
