import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useCart } from "../context/CartContext.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";

function glyph(name) {
  return (name || "•")[0].toUpperCase();
}

export default function Cart() {
  const { cart, setQty, remove } = useCart();
  const { user } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [products, setProducts] = useState({});
  const [loading, setLoading] = useState(true);

  const ids = Object.keys(cart).map(Number);

  useEffect(() => {
    let active = true;
    if (!ids.length) {
      setProducts({});
      setLoading(false);
      return;
    }
    setLoading(true);
    api
      .get("/products/products")
      .then((list) => {
        if (!active) return;
        const byId = Object.fromEntries(list.map((p) => [p.id, p]));
        setProducts(byId);
        setLoading(false);
      })
      .catch(() => {
        if (!active) return;
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [cart]);

  const total = ids.reduce((sum, id) => {
    const p = products[id];
    return p ? sum + p.price * cart[id] : sum;
  }, 0);

  if (!ids.length)
    return (
      <div className="section-head">
        <h2>Your cart</h2>
      </div>
    );

  return (
    <>
      <div className="section-head">
        <h2>Your cart</h2>
      </div>
      {loading ? (
        <div className="loading"><span className="spinner" /> Loading…</div>
      ) : (
        <>
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
                  <div className="qty">
                    <button onClick={() => setQty(id, cart[id] - 1)} aria-label="Decrease">
                      −
                    </button>
                    <span>{cart[id]}</span>
                    <button onClick={() => setQty(id, cart[id] + 1)} aria-label="Increase">
                      +
                    </button>
                  </div>
                  <div className="price">${Number(p.price * cart[id]).toFixed(2)}</div>
                  <button className="rm" onClick={() => remove(id)}>
                    Remove
                  </button>
                </div>
              );
            })}
          </div>
          <div className="summary">
            <div>
              <div className="muted">Subtotal</div>
              <div className="total">${total.toFixed(2)}</div>
            </div>
            <button
              className="accent-btn checkout-btn"
              onClick={() => {
                if (!user) {
                  toast("Please sign in to check out");
                  return;
                }
                navigate("/checkout");
              }}
            >
              Checkout
            </button>
          </div>
        </>
      )}
    </>
  );
}
