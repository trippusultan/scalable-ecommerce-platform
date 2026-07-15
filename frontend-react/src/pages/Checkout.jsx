import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useCart } from "../context/CartContext.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import SheenButton from "../components/SheenButton.jsx";

function glyph(name) {
  return (name || "•")[0].toUpperCase();
}

export default function Checkout() {
  const { cart, clear } = useCart();
  const { user } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [products, setProducts] = useState({});
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const ids = Object.keys(cart).map(Number);

  useEffect(() => {
    if (!user) {
      navigate("/cart");
      return;
    }
    if (!ids.length) {
      navigate("/cart");
      return;
    }
    api.get("/products/products").then((list) => {
      setProducts(Object.fromEntries(list.map((p) => [p.id, p])));
    });
  }, [user, ids.length]);

  const total = ids.reduce((sum, id) => {
    const p = products[id];
    return p ? sum + p.price * cart[id] : sum;
  }, 0);

  const placeOrder = async () => {
    if (busy) return;
    setBusy(true);
    setMsg("");
    try {
      // Sync client cart to the server cart-service, then checkout.
      // A missing/empty server cart must not abort the order — the backend
      // checkout reads from the cart-service, so we best-effort sync and
      // continue. Any hard error surfaces with a real message below.
      try {
        await api.del("/cart/cart");
      } catch { /* empty/already-cleared cart is fine */ }
      for (const id of ids) {
        try {
          await api.post("/cart/cart/items", { product_id: id, quantity: cart[id] });
        } catch (e) {
          throw new Error("Could not add " + (products[id]?.name || "item #" + id) + " to cart: " + (e?.message || e));
        }
      }
      const r = await api.post("/orders/checkout", {});
      clear();
      toast("Order placed — #" + (r?.order_id ?? ""));
      navigate("/orders");
    } catch (e) {
      setMsg(e?.message || "Checkout failed");
      setBusy(false);
    }
  };

  if (!user || !ids.length) return null;

  return (
    <>
      <div className="section-head">
        <h2>Checkout</h2>
      </div>
      <div className="list">
        {ids.map((id) => {
          const p = products[id];
          if (!p) return null;
          return (
            <div className="line" key={id}>
              <div className="glyph">{glyph(p.name)}</div>
              <div className="info">
                <h4>{p.name}</h4>
                <p>
                  ${Number(p.price).toFixed(2)} × {cart[id]}
                </p>
              </div>
              <div className="price">${Number(p.price * cart[id]).toFixed(2)}</div>
            </div>
          );
        })}
      </div>
      <div className="summary">
        <div>
          <div className="muted">Total due</div>
          <div className="total">${total.toFixed(2)}</div>
        </div>
        <SheenButton className="accent-btn checkout-btn" onClick={placeOrder} disabled={busy}>
          {busy ? "Placing order…" : "Place order"}
        </SheenButton>
      </div>
      <div className={"form-msg" + (msg ? " err" : "")} style={{ marginTop: 14 }}>
        {msg}
      </div>
    </>
  );
}
