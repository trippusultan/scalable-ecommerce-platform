import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";

export default function AuthModal({ onClose }) {
  const { login, register } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [tab, setTab] = useState("login");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setMsg("");
    const f = new FormData(e.target);
    try {
      if (tab === "login") {
        await login(f.get("username"), f.get("password"));
        toast("Signed in");
      } else {
        await register(f.get("username"), f.get("email"), f.get("fullname"), f.get("password"));
        toast("Account created");
      }
      onClose();
      navigate("/");
    } catch (err) {
      setMsg(err.message || "Auth failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true">
        <button className="modal-close" aria-label="Close" onClick={onClose}>
          ×
        </button>
        <div className="modal-tabs">
          <button className={"tab" + (tab === "login" ? " active" : "")} onClick={() => setTab("login")}>
            Sign in
          </button>
          <button className={"tab" + (tab === "register" ? " active" : "")} onClick={() => setTab("register")}>
            Create account
          </button>
        </div>
        <form className="auth-form" onSubmit={submit}>
          <input name="username" placeholder="Username" autoComplete="username" required />
          {tab === "register" && (
            <>
              <input name="email" placeholder="Email" type="email" autoComplete="email" required />
              <input name="fullname" placeholder="Full name" autoComplete="name" required />
            </>
          )}
          <input name="password" placeholder="Password" type="password" autoComplete="current-password" required />
          <button className="accent-btn" type="submit" disabled={busy}>
            {tab === "login" ? "Sign in" : "Create account"}
          </button>
          <div className={"form-msg" + (msg ? " err" : "")}>{msg}</div>
        </form>
      </div>
    </div>
  );
}
