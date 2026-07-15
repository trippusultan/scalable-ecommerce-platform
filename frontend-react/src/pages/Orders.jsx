import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import { api } from "../api.js";

function money(n) {
  return "$" + Number(n).toFixed(2);
}
function fmtDate(s) {
  try {
    return new Date(s).toLocaleString(undefined, {
      year: "numeric", month: "short", day: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return s;
  }
}
// Status → timeline steps for a small progress indicator.
const STAGES = ["pending", "paid", "confirmed", "shipped", "delivered"];
function stageIndex(status) {
  const i = STAGES.indexOf((status || "").toLowerCase());
  return i < 0 ? 0 : i;
}

export default function Orders() {
  const { user } = useAuth();
  const { toast } = useToast();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openId, setOpenId] = useState(null);

  useEffect(() => {
    if (!user) return;
    let active = true;
    setLoading(true);
    const token = localStorage.getItem("token");
    // NOTE: route through the shared api client. The gateway path is
    // /api/orders/orders (order-service root /orders 404s); the api client
    // prepends VITE_API_BASE so this hits the backend, not the Firebase
    // SPA fallback (which would return index.html -> "<!DOCTYPE" JSON error).
    api
      .get("/orders/orders")
      .then((o) => {
        if (!active) return;
        // newest first
        setOrders([...o].sort((a, b) => b.id - a.id));
        if (o.length) setOpenId(o[0].id);
      })
      .catch((e) => active && toast("Could not load orders (" + (e?.message || e) + ")"))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [user]);

  if (!user)
    return <div className="empty">Sign in to view your orders.</div>;
  if (loading)
    return (
      <div className="loading">
        <span className="spinner" /> Loading…
      </div>
    );

  return (
    <>
      <div className="section-head">
        <h2>Your orders</h2>
        <span className="muted">{orders.length} order{orders.length === 1 ? "" : "s"}</span>
      </div>
      {orders.length === 0 ? (
        <div className="empty">
          No orders yet. <Link className="status-ok" to="/">Browse the catalogue →</Link>
        </div>
      ) : (
        <div className="orders-list">
          {orders.map((o) => {
            const items = o.items || [];
            const stage = stageIndex(o.status);
            const expanded = openId === o.id;
            return (
              <div className="order-card" key={o.id}>
                <button
                  className="order-head"
                  onClick={() => setOpenId(expanded ? null : o.id)}
                  aria-expanded={expanded}
                >
                  <div className="order-id">Order #{o.id}</div>
                  <div className="order-date">{fmtDate(o.created_at)}</div>
                  <div className={"order-status status-" + (o.status || "pending")}>
                    {o.status}
                  </div>
                  <div className="order-total">{money(o.total)}</div>
                  <div className="order-chevron">{expanded ? "−" : "+"}</div>
                </button>

                {expanded && (
                  <div className="order-body">
                    <div className="order-track">
                      {STAGES.map((st, i) => (
                        <div
                          key={st}
                          className={"track-step" + (i <= stage ? " done" : "")}
                        >
                          <span className="track-dot" />
                          <span className="track-label">{st}</span>
                        </div>
                      ))}
                    </div>

                    <div className="order-items">
                      {items.map((it, idx) => (
                        <div className="order-item" key={idx}>
                          <div className="oi-name">
                            {it.name || "Item #" + it.product_id}
                            {!it.name && it.product_id ? (
                              <span className="oi-sub">product #{it.product_id}</span>
                            ) : null}
                          </div>
                          <div className="oi-qty">×{it.quantity ?? it.qty ?? 1}</div>
                          <div className="oi-price">
                            {money((it.price ?? 0) * (it.quantity ?? it.qty ?? 1))}
                          </div>
                        </div>
                      ))}
                    </div>

                    <div className="order-summary">
                      <div>
                        <span className="muted">Items</span> {items.length}
                      </div>
                      <div className="order-grand">
                        Total <b>{money(o.total)}</b>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}
