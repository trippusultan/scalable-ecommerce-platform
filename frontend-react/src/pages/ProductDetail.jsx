import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api.js";
import { useCart } from "../context/CartContext.jsx";
import { useToast } from "../context/ToastContext.jsx";

export default function ProductDetail() {
  const { id } = useParams();
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const { add } = useCart();
  const { toast } = useToast();

  useEffect(() => {
    let active = true;
    setLoading(true);
    api
      .get("/products/products/" + id)
      .then((p) => active && setProduct(p))
      .catch(() => {})
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [id]);

  if (loading) return <div className="loading"><span className="spinner" /> Loading…</div>;
  if (!product) return <div className="empty">Product not found.</div>;

  const glyph = (product.name || "•")[0].toUpperCase();

  return (
    <>
      <Link className="muted" to="/">
        ← Back to catalogue
      </Link>
      <div style={{ display: "flex", gap: 32, marginTop: 20, flexWrap: "wrap" }}>
        <div className="thumb" style={{ width: 340, aspectRatio: "1/1", flex: "0 0 auto" }}>
          <span className="glyph" style={{ fontSize: 72 }}>
            {glyph}
          </span>
        </div>
        <div className="center-col">
          <div className="cat-tag">{product.category_name || "Item"}</div>
          <h1 style={{ fontFamily: "var(--serif)", fontWeight: 500, fontSize: 38, margin: "8px 0 10px" }}>
            {product.name}
          </h1>
          <p className="muted" style={{ fontSize: 16 }}>
            {product.description || "No description."}
          </p>
          <div className="price" style={{ fontSize: 28, margin: "18px 0" }}>
            ${Number(product.price).toFixed(2)}
          </div>
          <div className="meta-pill">{product.stock} in stock</div>
          <div style={{ marginTop: 22, display: "flex", gap: 12, alignItems: "center" }}>
            <button
              className="accent-btn"
              onClick={() => {
                add(product.id, 1);
                toast("Added to cart");
              }}
            >
              Add to cart
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
