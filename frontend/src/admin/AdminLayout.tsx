import { createContext, useContext, useEffect, useState } from "react";
import { Navigate, NavLink, Outlet, useNavigate } from "react-router-dom";
import { api, auth, Me, Store } from "../api";

interface Ctx { me: Me; store: Store; setStore: (s: Store) => void; toast: (msg: string) => void }
const AdminCtx = createContext<Ctx | null>(null);
export const useAdmin = () => useContext(AdminCtx)!;

export default function AdminLayout() {
  const nav = useNavigate();
  const [me, setMe] = useState<Me | null>(null);
  const [store, setStore] = useState<Store | null>(null);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    if (!auth.get()) return;
    Promise.all([api<Me>("/api/auth/me"), api<Store>("/api/store")])
      .then(([m, s]) => { setMe(m); setStore(s); })
      .catch(() => { /* 401 會由 api() 導回登入頁 */ });
  }, []);

  useEffect(() => {
    if (!msg) return;
    const t = setTimeout(() => setMsg(""), 2500);
    return () => clearTimeout(t);
  }, [msg]);

  if (!auth.get()) return <Navigate to="/login" replace />;
  if (!me || !store) return <p className="page">載入中…</p>;

  const owner = me.role === "owner";
  const logout = () => { auth.clear(); nav("/login"); };

  return (
    <AdminCtx.Provider value={{ me, store, setStore, toast: setMsg }}>
      <header className="topbar">
        <span className="brand">{store.name}</span>
        <span className="tag" style={{ color: "#fff" }}>{store.is_open ? "營業中" : "休息中"}</span>
        <span className="who">{me.email}（{owner ? "老闆" : "店員"}）</span>
        <button className="btn btn-ghost btn-sm" onClick={logout}>登出</button>
      </header>
      <nav className="tabs" aria-label="後台功能">
        <NavLink end to="/admin">訂單看板</NavLink>
        <NavLink to="/admin/pos">POS 點餐</NavLink>
        <NavLink to="/admin/menu">菜單</NavLink>
        {owner && <NavLink to="/admin/report">今日報表</NavLink>}
        {owner && <NavLink to="/admin/settings">店家設定</NavLink>}
      </nav>
      <main className="page"><Outlet /></main>
      {msg && <div className="toast" role="status">{msg}</div>}
    </AdminCtx.Provider>
  );
}
