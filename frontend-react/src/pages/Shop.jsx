import { useEffect, useState, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api.js";
import { useToast } from "../context/ToastContext.jsx";
import ProductCard from "../components/ProductCard.jsx";
import SpotlightHeading from "../components/SpotlightHeading.jsx";

export default function Shop() {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [params, setParams] = useSearchParams();
  const { toast } = useToast();

  const cat = params.get("cat");
  const q = params.get("q");

  useEffect(() => {
    let active = true;
    api
      .get("/products/categories")
      .then((c) => active && setCategories(c))
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    const qs = new URLSearchParams();
    if (q) qs.set("q", q);
    if (cat) qs.set("category_id", cat);
    api
      .get("/products/products?" + qs.toString())
      .then((p) => {
        if (!active) return;
        setProducts(p);
        setLoading(false);
      })
      .catch((e) => {
        if (!active) return;
        toast("Could not load products — is the gateway running? (" + e.message + ")");
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [q, cat]);

  const setCat = (id) => {
    const next = new URLSearchParams(params);
    if (id) next.set("cat", id);
    else next.delete("cat");
    setParams(next);
  };

  return (
    <>
      <section className="hero">
        <SpotlightHeading text="Considered objects, quietly made." className="hero-title" />
        <p>A small catalogue over a real microservices backend — auth, cart, orders, payments, and service discovery, all live.</p>
        <div className="hero-meta">
          <div>
            Categories <b>{categories.length}</b>
          </div>
          <div>
            Products <b>{products.length}</b>
          </div>
          <div>Architecture <b>7 services + gateway</b></div>
        </div>
      </section>

      <div className="section-head">
        <h2>Catalogue</h2>
        <div className="filters" id="cat-filters">
          <button className={"chip" + (!cat ? " active" : "")} onClick={() => setCat(null)}>
            All
          </button>
          {categories.map((c) => (
            <button
              key={c.id}
              className={"chip" + (cat == c.id ? " active" : "")}
              onClick={() => setCat(c.id)}
            >
              {c.name}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="loading">
          <span className="spinner" /> Loading…
        </div>
      ) : products.length === 0 ? (
        <div className="empty">No products match your filters yet.</div>
      ) : (
        <div className="grid">
          {products.map((p) => (
            <ProductCard key={p.id} product={p} />
          ))}
        </div>
      )}
    </>
  );
}
