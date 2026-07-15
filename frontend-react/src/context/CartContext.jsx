import { createContext, useContext, useState, useCallback, useEffect } from "react";

const CartContext = createContext(null);

// Client-side cart (guest browsing). On checkout we sync this to the
// cart-service before calling orders/checkout. Keys: productId -> qty.
export function CartProvider({ children }) {
  const [cart, setCart] = useState({});

  useEffect(() => {
    try {
      const c = JSON.parse(localStorage.getItem("cart") || "{}");
      setCart(c && typeof c === "object" ? c : {});
    } catch {
      setCart({});
    }
  }, []);

  const save = useCallback((next) => {
    setCart(next);
    localStorage.setItem("cart", JSON.stringify(next));
  }, []);

  const add = useCallback(
    (id, qty = 1) => {
      setCart((prev) => {
        const next = { ...prev, [id]: (prev[id] || 0) + qty };
        localStorage.setItem("cart", JSON.stringify(next));
        return next;
      });
    },
    []
  );

  const setQty = useCallback((id, qty) => {
    setCart((prev) => {
      const next = { ...prev };
      if (qty <= 0) delete next[id];
      else next[id] = qty;
      localStorage.setItem("cart", JSON.stringify(next));
      return next;
    });
  }, []);

  const remove = useCallback((id) => {
    setCart((prev) => {
      const next = { ...prev };
      delete next[id];
      localStorage.setItem("cart", JSON.stringify(next));
      return next;
    });
  }, []);

  const clear = useCallback(() => {
    localStorage.removeItem("cart");
    setCart({});
  }, []);

  const count = Object.values(cart).reduce((a, b) => a + b, 0);

  return (
    <CartContext.Provider value={{ cart, add, setQty, remove, clear, count }}>
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart must be used within CartProvider");
  return ctx;
}
