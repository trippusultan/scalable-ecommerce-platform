import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { useCart } from "../context/CartContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import AuthModal from "./AuthModal.jsx";
import SpotlightHeading from "./SpotlightHeading.jsx";
import { BRAND } from "../brand.js";

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const { count } = useCart();
  const { toast } = useToast();
  const [authOpen, setAuthOpen] = useState(false);
  const [health, setHealth] = useState("—");
  const navigate = useNavigate();

  // live service health in footer
  const tick = async () => {
    try {
      const r = await fetch("/api/health?deep=1");
      const data = await r.json();
      const arr = Object.values(data.services || {});
      const up = arr.filter((s) => s && s !== "down" && s !== "error").length;
      setHealth(arr.length ? up + "/" + arr.length + " up" : "—");
    } catch {
      setHealth("gateway down");
    }
  };
  if (typeof window !== "undefined" && !window.__healthStarted) {
    window.__healthStarted = true;
    tick();
    setInterval(tick, 8000);
  }

  const onSignOut = () => {
    if (window.confirm("Sign out, " + (user?.username || "there") + "?")) {
      logout();
      toast("Signed out");
      navigate("/");
    }
  };

  return (
    <div className="wrap">
      <header className="topbar">
        <Link className="brand" to="/" aria-label={BRAND.name + " home"}>
          <SpotlightHeading text={BRAND.name} className="brand-mark" as="span" font='"Fraunces", Georgia, serif' />
        </Link>
        <form
          className="search"
          onSubmit={(e) => {
            e.preventDefault();
            navigate("/?q=" + encodeURIComponent(e.target[0].value));
          }}
        >
          <input type="search" placeholder="Search the catalogue…" aria-label="Search" />
        </form>
        <nav className="nav">
          <Link to="/">Shop</Link>
          {user && <Link to="/orders">Orders</Link>}
          <Link className="cart-link" to="/cart">
            Cart <span className="cart-count">{count}</span>
          </Link>
          {user ? (
            <button className="ghost-btn" onClick={onSignOut}>
              {user.full_name ? user.full_name.split(" ")[0] : user.username}
            </button>
          ) : (
            <button className="ghost-btn" onClick={() => setAuthOpen(true)}>
              Sign in
            </button>
          )}
        </nav>
      </header>

      <main className="view">{children}</main>

      <footer className="footer">
        <div className="footer-grid">
          <div className="footer-brand">
            <div className="footer-logo">{BRAND.name}</div>
            <p className="footer-tag">{BRAND.tagline}</p>
            <p className="footer-blurb">{BRAND.blurb}</p>
          </div>
          <div className="footer-col">
            <div className="footer-h">Explore</div>
            <Link to="/">Shop</Link>
            {user && <Link to="/orders">Your orders</Link>}
            <Link to="/cart">Cart</Link>
          </div>
          <div className="footer-col">
            <div className="footer-h">Built with</div>
            <span>FastAPI microservices</span>
            <span>React + Vite</span>
            <span>Service discovery</span>
          </div>
          <div className="footer-col">
            <div className="footer-h">Made by</div>
            <a href={BRAND.github} target="_blank" rel="noreferrer noopener">
              github · trippusultan
            </a>
            <span className="footer-meta">services: {health}</span>
          </div>
        </div>
        <div className="footer-base">
          © {new Date().getFullYear()} {BRAND.name} — a clean matte demo.
        </div>
      </footer>

      {authOpen && <AuthModal onClose={() => setAuthOpen(false)} />}
    </div>
  );
}
