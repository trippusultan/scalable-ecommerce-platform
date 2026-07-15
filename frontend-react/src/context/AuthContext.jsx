import { createContext, useContext, useState, useCallback, useEffect } from "react";
import { api } from "../api.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);

  const load = useCallback(() => {
    const u = localStorage.getItem("user");
    const t = localStorage.getItem("token");
    if (u && t) {
      try {
        setUser(JSON.parse(u));
      } catch {
        setUser(null);
      }
    } else {
      setUser(null);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const clear = useCallback(() => {
    localStorage.removeItem("user");
    localStorage.removeItem("token");
    setUser(null);
  }, []);

  const login = useCallback(
    async (username, password) => {
      const r = await api.post("/users/login", { username, password });
      localStorage.setItem("token", r.access_token);
      const u = await api.get("/users/me");
      localStorage.setItem("user", JSON.stringify(u));
      setUser(u);
      return u;
    },
    []
  );

  const register = useCallback(
    async (username, email, fullName, password) => {
      const r = await api.post("/users/register", { username, email, full_name: fullName, password });
      localStorage.setItem("token", r.access_token);
      const u = await api.get("/users/me");
      localStorage.setItem("user", JSON.stringify(u));
      setUser(u);
      return u;
    },
    []
  );

  return (
    <AuthContext.Provider value={{ user, login, register, logout: clear, refresh: load }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
