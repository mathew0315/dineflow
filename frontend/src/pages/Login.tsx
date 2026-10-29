import { FormEvent, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, auth } from "../api";

const DEMO_PW: Record<string, string> = {
  "owner@demo.dineflow.app": "demo-owner-2026",
  "staff@demo.dineflow.app": "demo-staff-2026",
};

export default function Login() {
  const [params] = useSearchParams();
  const nav = useNavigate();
  const presetEmail = params.get("email") ?? "";
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState(presetEmail);
  const [password, setPassword] = useState(DEMO_PW[presetEmail] ?? "");
  const [storeName, setStoreName] = useState("");
  const [slug, setSlug] = useState("");
  const [error, setError] = useState(params.get("expired") ? "登入已過期，請重新登入" : "");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const res = mode === "login"
        ? await api<{ access_token: string }>("/api/auth/login", { method: "POST", json: { email, password } })
        : await api<{ access_token: string }>("/api/auth/register", {
            method: "POST", json: { email, password, store_name: storeName, slug },
          });
      auth.set(res.access_token);
      nav(mode === "login" ? "/admin" : "/admin/menu");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="sheet" onSubmit={submit} style={{ maxWidth: 420 }}>
      <header className="sheet-head">
        <h1>{mode === "login" ? "店家登入" : "開一間店"}</h1>
        <p><Link to="/">DineFlow</Link></p>
      </header>
      <div className="sheet-body">
        {mode === "register" && (
          <>
            <div className="field">
              <label htmlFor="store">店名</label>
              <input id="store" required maxLength={100} value={storeName} onChange={(e) => setStoreName(e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="slug">店家代號（點餐網址會是 /s/代號，限小寫英數與 -）</label>
              <input id="slug" required pattern="[a-z0-9\-]{3,50}" value={slug}
                onChange={(e) => setSlug(e.target.value.toLowerCase())} placeholder="a-ming-noodles" />
            </div>
          </>
        )}
        <div className="field">
          <label htmlFor="email">Email</label>
          <input id="email" type="email" required autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="pw">密碼{mode === "register" && "（至少 8 碼）"}</label>
          <input id="pw" type="password" required minLength={mode === "register" ? 8 : 1}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        {error && <p className="error" role="alert" style={{ margin: 0 }}>{error}</p>}
        <button className="btn btn-red" disabled={busy}>
          {busy ? "處理中…" : mode === "login" ? "登入" : "建立店家"}
        </button>
        <button type="button" className="btn btn-ghost" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}>
          {mode === "login" ? "還沒有店家？開一間" : "已經有帳號，回到登入"}
        </button>
      </div>
    </form>
  );
}
