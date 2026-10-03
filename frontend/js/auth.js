/* Auth page controllers: register, login, otp */

async function handleRegister(e) {
  e.preventDefault();
  const form = e.target;
  const msg = document.getElementById("formMsg");
  msg.textContent = "";
  msg.className = "form-msg";

  const payload = {
    name: form.name.value.trim(),
    email: form.email.value.trim(),
    phone: form.phone.value.trim(),
    password: form.password.value,
    confirm_password: form.confirm_password.value,
  };

  try {
    const res = await API.register(payload);
    msg.className = "form-msg success";
    msg.textContent = "Registration successful! Redirecting to OTP verification...";
    sessionStorage.setItem("pending_phone", payload.phone);
    if (res.otp_debug) sessionStorage.setItem("dev_otp", res.otp_debug);
    setTimeout(() => (window.location.href = `verify-otp.html?phone=${encodeURIComponent(payload.phone)}`), 1000);
  } catch (err) {
    msg.className = "form-msg error";
    msg.textContent = formatErr(err);
  }
}

async function handleRequestOtp(e) {
  e.preventDefault();
  const msg = document.getElementById("formMsg");
  const phone = e.target.phone.value.trim();
  try {
    const res = await API.requestOtp(phone);
    msg.className = "form-msg success";
    msg.textContent = "OTP sent. Check your phone.";
    sessionStorage.setItem("pending_phone", phone);
    if (res.otp_debug) sessionStorage.setItem("dev_otp", res.otp_debug);
    setTimeout(() => (window.location.href = `verify-otp.html?phone=${encodeURIComponent(phone)}`), 800);
  } catch (err) {
    msg.className = "form-msg error";
    msg.textContent = formatErr(err);
  }
}

async function handleVerifyOtp(e) {
  e.preventDefault();
  const msg = document.getElementById("formMsg");
  const params = new URLSearchParams(window.location.search);
  const phone = e.target.phone.value.trim() || params.get("phone");
  const otp = e.target.otp.value.trim();

  try {
    const res = await API.verifyOtp(phone, otp);
    setToken(res.token);
    setUser(res.user);
    window.location.href = "dashboard.html";
  } catch (err) {
    msg.className = "form-msg error";
    msg.textContent = formatErr(err);
  }
}

function formatErr(err) {
  if (!err || !err.data) return err.message || "Something went wrong";
  const d = err.data;
  if (typeof d === "string") return d;
  if (d.detail) return d.detail;
  return Object.entries(d).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : v}`).join(" | ");
}

function guardAuth() {
  if (!isLoggedIn()) window.location.href = "login.html";
}
function guardGuest() {
  if (isLoggedIn()) window.location.href = "dashboard.html";
}

document.addEventListener("DOMContentLoaded", () => {
  const page = document.body.dataset.page;
  if (page === "register") {
    guardGuest();
    document.getElementById("registerForm").addEventListener("submit", handleRegister);
  }
  if (page === "login") {
    guardGuest();
    document.getElementById("otpForm").addEventListener("submit", handleRequestOtp);
    const pwForm = document.getElementById("pwForm");
    if (pwForm) pwForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const msg = document.getElementById("formMsg");
      try {
        const res = await API.loginPassword({
          username: e.target.username.value.trim(),
          password: e.target.password.value,
        });
        setToken(res.token); setUser(res.user);
        window.location.href = "dashboard.html";
      } catch (err) {
        msg.className = "form-msg error";
        msg.textContent = formatErr(err);
      }
    });
  }
  if (page === "verify-otp") {
    guardGuest();
    const params = new URLSearchParams(window.location.search);
    const phone = params.get("phone") || sessionStorage.getItem("pending_phone");
    if (phone) document.getElementById("phone").value = phone;
    const devOtp = sessionStorage.getItem("dev_otp");
    if (devOtp) {
      const hint = document.getElementById("devHint");
      if (hint) hint.textContent = `DEV OTP: ${devOtp}`;
    }
    document.getElementById("verifyForm").addEventListener("submit", handleVerifyOtp);
  }
});