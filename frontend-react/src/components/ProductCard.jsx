import { useState } from "react";
import { Link } from "react-router-dom";
import { useCart } from "../context/CartContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import { productImage, productImageUrl } from "../images.js";
import SheenButton from "./SheenButton.jsx";
import ElectricBorder from "./ElectricBorder.jsx";

export default function ProductCard({ product }) {
  const { cart, add, setQty, remove } = useCart();
  const { toast } = useToast();
  const qty = cart[product.id] || 0;
  const [hovered, setHovered] = useState(false);
  const [imgFailed, setImgFailed] = useState(false);
  const photo = productImageUrl(product);

  const thumb = (
    <Link className="thumb" to={"/product/" + product.id} aria-label={product.name}>
      {photo && !imgFailed ? (
        <img
          className="thumb-photo"
          src={photo}
          alt={product.name}
          loading="lazy"
          onError={() => setImgFailed(true)}
        />
      ) : (
        <span className="thumb-art" dangerouslySetInnerHTML={{ __html: productImage(product) }} />
      )}
    </Link>
  );

  return (
    <ElectricBorder
      active={hovered}
      radius={18}
      glowIntensity={5}
      className="card-border"
      style={{ borderRadius: 18 }}
    >
      <div
        className="card"
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        {thumb}
        <div className="cat-tag">{product.category_name || "Item"}</div>
        <h3>
          <Link to={"/product/" + product.id}>{product.name}</Link>
        </h3>
        <p className="desc">{product.description || ""}</p>
        <div className="row">
          <div className="price">
            ${Number(product.price).toFixed(2)} <small>/ ea</small>
          </div>
          {qty > 0 ? (
            <div className="stepper" role="group" aria-label={"Quantity for " + product.name}>
              <button
                className="step-btn"
                aria-label="Decrease"
                onClick={() => (qty <= 1 ? remove(product.id) : setQty(product.id, qty - 1))}
              >
                −
              </button>
              <span className="step-qty">{qty}</span>
              <button className="step-btn" aria-label="Increase" onClick={() => setQty(product.id, qty + 1)}>
                +
              </button>
            </div>
          ) : (
            <SheenButton
              className="add-btn"
              ariaLabel={"Add " + product.name + " to cart"}
              onClick={() => {
                add(product.id, 1);
                toast("Added to cart");
              }}
            >
              Add
            </SheenButton>
          )}
        </div>
      </div>
    </ElectricBorder>
  );
}
