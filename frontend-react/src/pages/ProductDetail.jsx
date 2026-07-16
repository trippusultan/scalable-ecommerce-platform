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
      <div className="product-detail">
        <div className="thumb">
          <span className="glyph" style={{ fontSize: "clamp(48px, 12vw, 72px)" }}>
            {glyph}
          </span>
        </div>
        <div className="center-col">
          <div className="cat-tag">{product.category_name || "Item"}</div>
          <h1>{product.name}</h1>
          <p className="muted" style={{ fontSize: 16 }}>
            {product.description || "No description."}
          </p>
          <div className="price">${Number(product.price).toFixed(2)}</div>
          <div className="meta-pill">{product.stock} in stock</div>
          <div className="actions">
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
