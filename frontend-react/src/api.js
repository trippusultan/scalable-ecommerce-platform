// Thin API client over the gateway.
// In dev the gateway is same-origin (serves this SPA at /ui/ and proxies /api).
// In prod the SPA is hosted on Firebase Hosting, so we call the deployed
// gateway directly via VITE_API_BASE (e.g. https://ecom-gateway.onrender.com).
// Falls back to same-origin /api when VITE_API_BASE is unset (dev / Docker).

const API_BASE = (import.meta.env.VITE_API_BASE || "").replace(/\/$/, "");
const PREFIX = API_BASE ? API_BASE + "/api" : "/api";

async function request(path, opts = {}) {
  const headers = Object.assign({}, opts.headers || {});
  const tok = localStorage.getItem("token");
  if (tok) headers["Authorization"] = "Bearer " + tok;
  if (opts.body && !headers["Content-Type"]) headers["Content-Type"] = "application/json";

  const res = await fetch(PREFIX + path, Object.assign({}, opts, { headers }));
  let data = null;
  try {
    data = await res.json();
  } catch (e) {
    /* no body */
  }
  if (!res.ok) {
    const detail = (data && (data.detail || data.message)) || "HTTP " + res.status;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export const api = {
  get: (p) => request(p),
  post: (p, body) => request(p, { method: "POST", body: JSON.stringify(body) }),
  patch: (p, body) => request(p, { method: "PATCH", body: JSON.stringify(body) }),
  del: (p) => request(p, { method: "DELETE" }),
};

export function token() {
  return localStorage.getItem("token");
}
