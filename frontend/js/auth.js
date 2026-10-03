/* ------------------------------------------------------------------
   FarmKonnect auth pages controller
   Handles: register.html, login.html, verify-otp.html
------------------------------------------------------------------ */

/* ------------------------- helpers ------------------------- */

function formatErr(err) {
  if (!err) return "Something went wrong";
  if (err.data) {
    const d = err.data;
    if (typeof d === "string") return d;
    if (d.detail) return d.detail;
    return Object.entries(d)
      .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : v}`)
      .join(" | ");
  }
  return err.message || "Something went wrong";
}

function guardGuest() {
  if (window.isLoggedIn && window.isLoggedIn()) {
    window.location.href = "dashboard.html";
  }
}

function setMsg(el, text, kind = "") {
  if (!el) return;
  el.textContent = text;
  el.className = `form-msg ${kind}`;
}

/* ------------------------- register ------------------------- */

async function handleRegister(e) {
  e.preventDefault();
  const form = e.target;
  const msg = document.getElementById("formMsg");
  setMsg(msg, "");

  const payload = {
    name: form.name.value.trim(),
    email: form.email.value.trim(),
    phone: form.phone.value.trim(),
    password: form.password.value,
    confirm_password: form.confirm_password.value,
  };

  if (payload.password !== payload.confirm_password) {
    return setMsg(msg, "Passwords do not match.", "error");
  }

  try {
    await window.API.register(payload);
    setMsg(msg, "Registration successful! Redirecting to OTP…", "success");
    sessionStorage.setItem("pending_identifier", payload.phone);
    sessionStorage.setItem("new_user", "1");   // <-- mark this as a fresh registration

    setTimeout(() => {
      window.location.href =
        `verify-otp.html?identifier=${encodeURIComponent(payload.phone)}`;
    }, 900);
  } catch (err) {
    setMsg(msg, formatErr(err), "error");
  }
}

/* ------------------------- login (phone/email + password) ------------------------- */

async function handleLogin(e) {
  e.preventDefault();
  const form = e.target;
  const msg = document.getElementById("formMsg");
  setMsg(msg, "Verifying…");

  const ident    = form.phone.value.trim();      // may be phone OR email
  const password = form.password.value;

  if (!ident || !password) {
    return setMsg(msg, "Phone/email and password are required.", "error");
  }

  try {
    const res = await window.API.loginPassword({ phone: ident, password });

    const identifier = res.identifier || ident;
    sessionStorage.setItem("pending_identifier", identifier);

    const channel = res.delivery?.channel;
    const note =
      channel === "sms"   ? "OTP sent by SMS." :
      channel === "email" ? "OTP sent to your email." :
                            "OTP sent.";

    setMsg(msg, note + " Redirecting…", "success");

    setTimeout(() => {
      window.location.href =
        `verify-otp.html?identifier=${encodeURIComponent(identifier)}`;
    }, 700);
  } catch (err) {
    setMsg(msg, formatErr(err), "error");
  }
}

/* ------------------------- verify otp ------------------------- */

async function handleVerifyOtp(e) {
  e.preventDefault();
  const form = e.target;
  const msg = document.getElementById("formMsg");
  setMsg(msg, "");

  const identifier = form.phone.value.trim();
  const otp        = form.otp.value.trim();

  if (!/^\d{6}$/.test(otp)) {
    return setMsg(msg, "Enter a 6-digit code.", "error");
  }

  try {
    const res = await window.API.verifyOtp(identifier, otp);
    window.setToken(res.token);
    window.setUser(res.user);
    sessionStorage.removeItem("pending_identifier");

    const isNew = sessionStorage.getItem("new_user") === "1";
    sessionStorage.removeItem("new_user");

    // If profile not completed → go to profile setup
    if (!res.profile_completed || isNew) {
      window.location.href = "farmer-profile.html";
    } else {
      window.location.href = "dashboard.html";
    }
  } catch (err) {
    setMsg(msg, formatErr(err), "error");
  }
}
/* ------------------------- resend otp ------------------------- */

async function handleResendOtp(e) {
  e.preventDefault();
  const msg = document.getElementById("formMsg");
  const ident =
    document.getElementById("phone").value.trim() ||
    sessionStorage.getItem("pending_identifier");

  if (!ident) return setMsg(msg, "No identifier on file — start over.", "error");

  setMsg(msg, "Resending…");
  try {
    await window.API.requestOtp(ident);
    setMsg(msg, "New OTP sent.", "success");
  } catch (err) {
    setMsg(msg, formatErr(err), "error");
  }
}

/* ------------------------- page bootstrapping ------------------------- */

document.addEventListener("DOMContentLoaded", () => {
  const page = document.body.dataset.page;

  /* ---- register.html ---- */
  if (page === "register") {
    guardGuest();
    const form = document.getElementById("registerForm");
    if (form) form.addEventListener("submit", handleRegister);
  }

  /* ---- login.html ---- */
  if (page === "login") {
    guardGuest();
    const form = document.getElementById("loginForm");
    if (!form) {
      console.error("loginForm not found in DOM");
      return;
    }
    form.addEventListener("submit", handleLogin);
  }

  /* ---- verify-otp.html ---- */
  if (page === "verify-otp") {
    guardGuest();

    const params = new URLSearchParams(window.location.search);
    const identifier =
      params.get("identifier") ||
      params.get("phone") ||
      sessionStorage.getItem("pending_identifier") ||
      "";

    const phoneInput = document.getElementById("phone");
    if (phoneInput) phoneInput.value = identifier;

    const shown = document.getElementById("targetPhone");
    if (shown && identifier) shown.textContent = identifier;

    const form = document.getElementById("verifyForm");
    if (form) form.addEventListener("submit", handleVerifyOtp);

    const resend = document.getElementById("resendOtp");
    if (resend) resend.addEventListener("click", handleResendOtp);

    const otpInput = document.querySelector("input[name='otp']");
    if (otpInput) otpInput.focus();
  }
});