document.addEventListener("DOMContentLoaded", async () => {
  if (document.body.dataset.page !== "farmer-profile") return;

  if (!window.isLoggedIn()) {
    window.location.href = "login.html";
    return;
  }

  const form = document.getElementById("profileForm");
  const msg  = document.getElementById("formMsg");

  // Load existing profile (or create blank)
  try {
    const p = await window.API.myProfile();
    if (p) {
      for (const [k, v] of Object.entries(p)) {
        const el = form.elements[k];
        if (el) el.value = v ?? "";
      }
    }
    const u = window.getUser();
    if (u) form.elements["phone_display"].value = u.phone || "";
  } catch (e) {
    console.warn("Could not load profile:", e);
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    msg.textContent = "";
    msg.className = "form-msg";

    const data = {};
    for (const el of form.elements) {
      if (el.name && el.name !== "phone_display") {
        const val = (el.value || "").trim();
        if (["gps_latitude", "gps_longitude", "date_of_birth"].includes(el.name)) {
          data[el.name] = val || null;
        } else {
          data[el.name] = val;
        }
      }
    }

    try {
      await window.API.saveProfile(data);
      const user = window.getUser();
      if (user) window.setUser({ ...user, profile_completed: true });
      msg.className = "form-msg success";
      msg.textContent = "Profile saved. Redirecting to dashboard…";
      setTimeout(() => (window.location.href = "dashboard.html"), 700);
    } catch (err) {
      msg.className = "form-msg error";
      msg.textContent =
        err?.data?.detail ||
        Object.values(err?.data || {}).flat().join(" | ") ||
        err.message ||
        "Save failed.";
    }
  });
});