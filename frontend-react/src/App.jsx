import { Routes, Route, useNavigate, useLocation } from "react-router-dom";
import { useEffect } from "react";
import Layout from "./components/Layout.jsx";
import Shop from "./pages/Shop.jsx";
import ProductDetail from "./pages/ProductDetail.jsx";
import Cart from "./pages/Cart.jsx";
import Checkout from "./pages/Checkout.jsx";
import Orders from "./pages/Orders.jsx";

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();

  // Keep a tiny global handle for non-React triggers (e.g. "please sign in").
  useEffect(() => {
    window.__go = (hash) => navigate(hash);
  }, [navigate]);

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Shop />} />
        <Route path="/product/:id" element={<ProductDetail />} />
        <Route path="/cart" element={<Cart />} />
        <Route path="/checkout" element={<Checkout />} />
        <Route path="/orders" element={<Orders />} />
        <Route path="*" element={<Shop />} />
      </Routes>
      {/* location dependency keeps navigate fresh */}
      <span hidden>{location.pathname}</span>
    </Layout>
  );
}
