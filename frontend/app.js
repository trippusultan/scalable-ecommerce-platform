/* Clean matte storefront — vanilla SPA over the e-commerce microservices gateway. */
(function () {
  "use strict";

  const API = ""; // same-origin (gateway serves /ui/*)

  // ---------- helpers ----------
  const $ = (sel) => document.querySelector(sel);
  const esc = (s) =>
    String(s == null ? "" : s).replace(/[&<>\"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
    );

  function toast(msg) {
    const t = $("#toast");
    t.textContent = msg;
    t.hidden = false;
    clearTimeout(toast._t);
    toast._t = setTimeout(() => (t.hidden = true), 2200);
  }

  async function api(path, opts = {}) {
    const headers = Object.assign({}, opts.headers || {});
    const tok = localStorage.getItem("token");
    if (tok) headers["Authorization"] = "Bearer " + tok;
    if (opts.body && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
    const res = await fetch(API + path, Object.assign({}, opts, { headers }));
    let data = null;
    try { data = await res.json(); } catch (e) { /* no body */ }
    if (!res.ok) {
      const detail = (data && (data.detail || data.message)) || ("HTTP " + res.status);
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return data;
  }

  // ---------- auth state ----------
  function currentUser() {
    const u = localStorage.getItem("user");
    const t = localStorage.getItem("token");
    return u && t ? JSON.parse(u) : null;
  }
  function setAuth(user, token) {
    localStorage.setItem("user", JSON.stringify(user));
    localStorage.setItem("token", token);
    renderAuth();
  }
  function clearAuth() {
    localStorage.removeItem("user");
    localStorage.removeItem("token");
    renderAuth();
  }

  function renderAuth() {
    const u = currentUser();
    const btn = $("#auth-btn");
    const orders = $(".nav-orders");
    if (u) {
      btn.textContent = u.full_name ? u.full_name.split(" ")[0] : u.username;
      btn.onclick = () => { if (confirm("Sign out, " + esc(u.username) + "?")) { clearAuth(); toast("Signed out"); router(); } };
      orders.hidden = false;
    } else {
      btn.textContent = "Sign in";
      btn.onclick = () => openAuth("login");
      orders.hidden = true;
    }
    refreshCartCount();
  }

  // ---------- cart (client-side, in-memory + localStorage) ----------
  let cart = {};
  try { cart = JSON.parse(localStorage.getItem("cart") || "{}"); } catch (e) { cart = {}; }
  function saveCart() { localStorage.setItem("cart", JSON.stringify(cart)); refreshCartCount(); }
  function refreshCartCount() {
    const n = Object.values(cart).reduce((a, b) => a + b, 0);
    $("#cart-count").textContent = n;
  }
  function addToCart(id, qty = 1) {
    cart[id] = (cart[id] || 0) + qty;
    saveCart(); toast("Added to cart");
  }

  // ---------- auth modal ----------
  let authMode = "login";
  function openAuth(mode) {
    authMode = mode;
    $("#auth-modal").hidden = false;
    setAuthTab(mode);
    $("#auth-msg").textContent = "";
  }
  function closeAuth() { $("#auth-modal").hidden = true; }
  function setAuthTab(mode) {
    authMode = mode;
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === mode));
    const reg = mode === "register";
    $("#auth-email").hidden = !reg;
    $("#auth-fullname").hidden = !reg;
    $("#auth-password").setAttribute("autocomplete", reg ? "new-password" : "current-password");
    $("#auth-submit").textContent = reg ? "Create account" : "Sign in";
    $("#auth-msg").textContent = "";
  }
  $("#auth-close").onclick = closeAuth;
  $("#auth-modal").addEventListener("click", (e) => { if (e.target.id === "auth-modal") closeAuth(); });
  document.querySelectorAll(".tab").forEach((t) => (t.onclick = () => setAuthTab(t.dataset.tab)));

  $("#auth-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const msg = $("#auth-msg");
    msg.className = "form-msg";
    msg.textContent = "";
    const username = $("#auth-username").value.trim();
    const password = $("#auth-password").value;
    try {
      if (authMode === "register") {
        const body = {
          username, password,
          email: $("#auth-email").value.trim(),
          full_name: $("#auth-fullname").value.trim(),
        };
        const r = await api("/api/users/register", { method: "POST", body: JSON.stringify(body) });
        setAuth({ username, full_name: body.full_name }, r.access_token);
      } else {
        const r = await api("/api/users/login", { method: "POST", body: JSON.stringify({ username, password }) });
        setAuth({ username }, r.access_token);
      }
      closeAuth();
      toast("Welcome" + (authMode === "register" ? " — account created" : ""));
      router();
    } catch (err) {
      msg.className = "form-msg err";
      msg.textContent = err.message || "Authentication failed";
    }
  });

  // ---------- search ----------
  let searchQ = "";
  $("#search-form").addEventListener("submit", (e) => { e.preventDefault(); searchQ = $("#search-input").value.trim(); router(); });
  $("#search-input").addEventListener("input", (e) => { searchQ = e.target.value.trim(); if (location.hash === "#/" || location.hash === "" ) router(); });

  // ---------- router ----------
  function parseHash() {
    const h = location.hash.replace(/^#/, "") || "/";
    const [path, qs] = h.split("?");
    const params = new URLSearchParams(qs || "");
    return { path, params };
  }

  async function router() {
    const { path } = parseHash();
    const view = $("#view");
    if (path.startsWith("/product/")) return renderProduct(view, parseInt(path.split("/")[2], 10));
    if (path === "/cart") return renderCart(view);
    if (path === "/orders") return renderOrders(view);
    if (path === "/checkout") return renderCheckout(view);
    return renderShop(view);
  }

  // ---------- views ----------
  function loading() { return '<div class="empty"><span class="spinner"></span></div>'; }

  async function renderShop(view) {
    view.innerHTML = `
      <section class="hero">
        <h1>Considered objects, quietly made.</h1>
        <p>A small catalogue over a real microservices backend — auth, cart, orders, payments, and service discovery, all live.</p>
        <div class="hero-meta">
          <div>Categories <b id="cat-count">—</b></div>
          <div>Products <b id="prod-count">—</b></div>
          <div>Architecture <b>7 services + gateway</b></div>
        </div>
      </section>
      <div class="section-head">
        <h2>Catalogue</h2>
        <div class="filters" id="cat-filters"></div>
      </div>
      <div id="grid-host">${loading()}</div>`;

    let categories = [];
    try { categories = await api("/api/products/categories"); } catch (e) {}
    const active = new URLSearchParams(location.hash.split("?")[1] || "").get("cat");
    const fc = $("#cat-filters");
    const all = document.createElement("button");
    all.className = "chip" + (!active ? " active" : "");
    all.textContent = "All";
    all.onclick = () => { location.hash = "#/"; };
    fc.appendChild(all);
    categories.forEach((c) => {
      const b = document.createElement("button");
      b.className = "chip" + (active == c.id ? " active" : "");
      b.textContent = esc(c.name);
      b.onclick = () => { location.hash = "#/?cat=" + c.id; };
      fc.appendChild(b);
    });
    $("#cat-count").textContent = categories.length;

    loadProducts(view);
  }

  async function loadProducts(view) {
    const host = $("#grid-host");
    if (!host) return;
    const { params } = parseHash();
    const qs = new URLSearchParams();
    if (searchQ) qs.set("q", searchQ);
    if (params.get("cat")) qs.set("category_id", params.get("cat"));
    let products = [];
    try {
      products = await api("/api/products/products?" + qs.toString());
    } catch (e) {
      host.innerHTML = '<div class="empty">Could not load products — is the gateway running? (' + esc(e.message) + ")</div>";
      return;
    }
    const total = $("#prod-count");
    if (total) total.textContent = products.length;
    if (!products.length) {
      host.innerHTML = '<div class="empty">No products match your filters yet.</div>';
      return;
    }
    host.innerHTML = '<div class="grid">' + products.map(cardHTML).join("") + "</div>";
    host.querySelectorAll("[data-add]").forEach((b) => {
      b.onclick = () => addToCart(parseInt(b.dataset.add, 10));
    });
  }

  function cardHTML(p) {
    const glyph = esc((p.name || "•")[0].toUpperCase());
    return `
      <div class="card">
        <a class="thumb" href="#/product/${p.id}" data-link><span class="glyph">${glyph}</span></a>
        <div class="cat-tag">${esc(p.category_name || "Item")}</div>
        <h3><a href="#/product/${p.id}" data-link>${esc(p.name)}</a></h3>
        <p class="desc">${esc(p.description || "")}</p>
        <div class="row">
          <div class="price">$${Number(p.price).toFixed(2)} <small>/ ea</small></div>
          <button class="add-btn" data-add="${p.id}">Add</button>
        </div>
      </div>`;
  }

  async function renderProduct(view, id) {
    view.innerHTML = loading();
    let p;
    try { p = await api("/api/products/products/" + id); } catch (e) {
      view.innerHTML = '<div class="empty">Product not found.</div>'; return;
    }
    const glyph = esc((p.name || "•")[0].toUpperCase());
    view.innerHTML = `
      <a class="muted" href="#/" data-link>← Back to catalogue</a>
      <div style="display:flex;gap:32px;margin-top:20px;flex-wrap:wrap;">
        <div class="thumb" style="width:340px;aspect-ratio:1/1;flex:0 0 auto;">
          <span class="glyph" style="font-size:72px;">${glyph}</span>
        </div>
        <div class="center-col">
          <div class="cat-tag">${esc(p.category_name || "Item")}</div>
          <h1 style="font-family:var(--serif);font-weight:500;font-size:38px;margin:8px 0 10px;">${esc(p.name)}</h1>
          <p class="muted" style="font-size:16px;">${esc(p.description || "No description.")}</p>
          <div class="price" style="font-size:28px;margin:18px 0;">$${Number(p.price).toFixed(2)}</div>
          <div class="meta-pill">${p.stock} in stock</div>
          <div style="margin-top:22px;display:flex;gap:12px;align-items:center;">
            <button class="accent-btn" id="pd-add" data-add="${p.id}">Add to cart</button>
          </div>
        </div>
      </div>`;
    const addBtn = view.querySelector("#pd-add");
    if (addBtn) addBtn.addEventListener("click", () => addToCart(parseInt(addBtn.dataset.add, 10)));
  }

  async function renderCart(view) {
    const ids = Object.keys(cart).map(Number);
    view.innerHTML = '<div class="section-head"><h2>Your cart</h2></div><div id="cart-host">' + loading() + "</div>";
    const host = $("#cart-host");
    if (!ids.length) { host.innerHTML = '<div class="empty">Your cart is empty. <a class="status-ok" href="#/" data-link>Browse the catalogue →</a></div>'; return; }
    let products = [];
    try { products = await api("/api/products/products"); } catch (e) {}
    const byId = Object.fromEntries(products.map((p) => [p.id, p]));
    let total = 0;
    const rows = ids.map((id) => {
      const p = byId[id];
      const qty = cart[id];
      if (!p) return "";
      total += p.price * qty;
      return `
        <div class="line">
          <div class="glyph">${esc((p.name || "•")[0].toUpperCase())}</div>
          <div class="info"><h4>${esc(p.name)}</h4><p>$${Number(p.price).toFixed(2)} each</p></div>
          <div class="qty">
            <button data-dec="${id}">−</button><span>${qty}</span><button data-inc="${id}">+</button>
          </div>
          <div class="price">$${Number(p.price * qty).toFixed(2)}</div>
          <button class="chip" data-rm="${id}">Remove</button>
        </div>`;
    }).join("");
    host.innerHTML = `
      <div class="list">${rows}</div>
      <div class="summary">
        <div><div class="muted">Subtotal</div><div class="total">$${total.toFixed(2)}</div></div>
        <button class="accent-btn checkout-btn" id="go-checkout">Checkout</button>
      </div>`;
    host.querySelectorAll("[data-inc]").forEach((b) =>
      b.addEventListener("click", () => { cart[+b.dataset.inc] = (cart[+b.dataset.inc] || 0) + 1; saveCart(); renderCart(view); }));
    host.querySelectorAll("[data-dec]").forEach((b) =>
      b.addEventListener("click", () => { const id = +b.dataset.dec; cart[id] = (cart[id] || 0) - 1; if (cart[id] <= 0) delete cart[id]; saveCart(); renderCart(view); }));
    host.querySelectorAll("[data-rm]").forEach((b) =>
      b.addEventListener("click", () => { delete cart[+b.dataset.rm]; saveCart(); renderCart(view); }));
    const co = host.querySelector("#go-checkout");
    if (co) co.onclick = () => {
      if (!currentUser()) { toast("Please sign in to check out"); openAuth("login"); return; }
      location.hash = "#/checkout";
    };
  }

  async function renderCheckout(view) {
    const u = currentUser();
    if (!u) { location.hash = "#/cart"; return; }
    const ids = Object.keys(cart).map(Number);
    if (!ids.length) { location.hash = "#/cart"; return; }
    view.innerHTML = '<div class="section-head"><h2>Checkout</h2></div><div id="co-host">' + loading() + "</div>";
    const host = $("#co-host");
    let products = [];
    try { products = await api("/api/products/products"); } catch (e) {}
    const byId = Object.fromEntries(products.map((p) => [p.id, p]));
    let total = 0;
    const rows = ids.map((id) => {
      const p = byId[id]; if (!p) return "";
      const qty = cart[id]; total += p.price * qty;
      return `<div class="line"><div class="glyph">${esc((p.name||"•")[0].toUpperCase())}</div>
        <div class="info"><h4>${esc(p.name)}</h4><p>$${Number(p.price).toFixed(2)} × ${qty}</p></div>
        <div class="price">$${Number(p.price*qty).toFixed(2)}</div></div>`;
    }).join("");
    host.innerHTML = `
      <div class="list">${rows}</div>
      <div class="summary"><div><div class="muted">Total due</div><div class="total">$${total.toFixed(2)}</div></div>
      <button class="accent-btn checkout-btn" id="pay-btn">Place order</button></div>
      <div class="form-msg" id="co-msg" style="margin-top:14px;"></div>`;
    $("#pay-btn").onclick = async () => {
      const msg = $("#co-msg"); msg.className = "form-msg"; msg.textContent = "";
      const payBtn = $("#pay-btn"); payBtn.disabled = true; payBtn.textContent = "Placing order…";
      try {
        // Sync the client-side cart to the server cart-service, then checkout.
        // Clear any stale server cart first so quantities are exact.
        try { await api("/api/cart/cart", { method: "DELETE" }); } catch (e) { /* empty cart is fine */ }
        for (const id of ids) {
          await api("/api/cart/cart/items", {
            method: "POST",
            body: JSON.stringify({ product_id: id, quantity: cart[id] }),
          });
        }
        const r = await api("/api/orders/checkout", { method: "POST" });
        cart = {}; saveCart();
        toast("Order placed — #" + r.order_id);
        location.hash = "#/orders";
      } catch (e) {
        msg.className = "form-msg err"; msg.textContent = e.message || "Checkout failed";
        payBtn.disabled = false; payBtn.textContent = "Place order";
      }
    };
  }

  async function renderOrders(view) {
    const u = currentUser();
    if (!u) { openAuth("login"); view.innerHTML = '<div class="empty">Sign in to view your orders.</div>'; return; }
    view.innerHTML = '<div class="section-head"><h2>Your orders</h2></div><div id="ord-host">' + loading() + "</div>";
    const host = $("#ord-host");
    let orders = [];
    try { orders = await api("/api/orders/orders"); } catch (e) {
      host.innerHTML = '<div class="empty">Could not load orders (' + esc(e.message) + ")</div>"; return;
    }
    if (!orders.length) { host.innerHTML = '<div class="empty">No orders yet. <a class="status-ok" href="#/" data-link>Go shopping →</a></div>'; return; }
    host.innerHTML = '<div class="list">' + orders.map((o) => `
      <div class="line">
        <div class="glyph">#</div>
        <div class="info"><h4>Order #${o.id}</h4>
          <p>${o.items.length} item(s) · ${new Date(o.created_at).toLocaleDateString()}</p></div>
        <div class="muted">${esc(o.status)}</div>
        <div class="price">$${Number(o.total).toFixed(2)}</div>
      </div>`).join("") + "</div>";
  }

  // live service health in footer
  async function refreshHealth() {
    try {
      const r = await api("/health");
      const up = Object.values(r.services).filter((v) => v === "ok").length;
      $("#footer-health").textContent = "services: " + up + "/" + Object.keys(r.services).length + " up";
    } catch (e) { $("#footer-health").textContent = "services: gateway unreachable"; }
  }

  // ---------- boot ----------
  window.addEventListener("hashchange", router);
  renderAuth();
  router();
  refreshHealth();
  setInterval(refreshHealth, 6000);
})();
