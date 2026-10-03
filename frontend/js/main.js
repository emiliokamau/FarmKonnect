/* Homepage: load dynamic services cards + latest market snapshot */
document.addEventListener("DOMContentLoaded", async () => {
  if (document.body.dataset.page !== "home") return;

  // Services cards — you can manage these via admin by creating Products with category="service"
  const grid = document.getElementById("servicesGrid");
  try {
    const products = await API.products();
    const services = (products.results || products).slice(0, 6);
    if (services.length === 0) {
      grid.innerHTML = `<p class="muted">No services published yet. Add them from the admin panel.</p>`;
      return;
    }
    grid.innerHTML = services.map(p => `
      <div class="card service-card">
        <div class="service-icon">🌾</div>
        <h3>${p.name}</h3>
        <p>${p.description || "All-in-one agricultural service."}</p>
      </div>
    `).join("");
  } catch (err) {
    grid.innerHTML = `<p class="muted">Unable to load services.</p>`;
  }
});