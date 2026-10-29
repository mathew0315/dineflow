import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, ApiError, MenuItem, nt, Order, Store } from "../api";

export default function OrderPage() {
  const { slug = "" } = useParams();
  const nav = useNavigate();
  const [store, setStore] = useState<Store | null>(null);
  const [menu, setMenu] = useState<MenuItem[]>([]);
  const [qty, setQty] = useState<Record<number, number>>({});
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  // 同一次下單動作共用一把冪等鍵：網路重試或連點不會重複建單
  const idemKey = useRef(crypto.randomUUID());

  useEffect(() => {
    Promise.all([api<Store>(`/api/public/stores/${slug}`), api<MenuItem[]>(`/api/public/stores/${slug}/menu`)])
      .then(([s, m]) => { setStore(s); setMenu(m); })
      .catch((e: ApiError) => setError(e.status === 404 ? "找不到這間店，請確認網址" : e.message))
      .finally(() => setLoading(false));
  }, [slug]);

  const groups = useMemo(() => {
    const g = new Map<string, MenuItem[]>();
    menu.forEach((m) => g.set(m.category, [...(g.get(m.category) ?? []), m]));
    return [...g.entries()];
  }, [menu]);

  const lines = menu.filter((m) => qty[m.id] > 0);
  const total = lines.reduce((s, m) => s + m.price * qty[m.id], 0);
  const change = (id: number, d: number) =>
    setQty((q) => ({ ...q, [id]: Math.min(99, Math.max(0, (q[id] ?? 0) + d)) }));

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (!lines.length) return setError("請先勾選至少一個品項");
    if (!/^09\d{8}$/.test(phone)) return setError("手機號碼請輸入 09 開頭的 10 碼數字");
    setSending(true);
    try {
      const order = await api<Order>(`/api/public/stores/${slug}/orders`, {
        method: "POST",
        headers: { "Idempotency-Key": idemKey.current },
        json: {
          items: lines.map((m) => ({ menu_item_id: m.id, quantity: qty[m.id] })),
          customer_name: name.trim(), customer_phone: phone, note: note.trim() || null,
        },
      });
      try { sessionStorage.setItem(`dineflow_phone_${order.id}`, phone); } catch { /* ignore */ }
      nav(`/s/${slug}/orders/${order.id}?phone=${phone}`);
    } catch (err) {
      setError((err as Error).message);
      setSending(false);
    }
  }

  if (loading) return <p className="sheet" style={{ padding: "2rem", textAlign: "center" }}>正在拿點菜單…</p>;
  if (!store) return <p className="sheet error" style={{ padding: "2rem", textAlign: "center" }}>{error}</p>;

  const now = new Date().toLocaleString("zh-TW", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false });

  return (
    <form className="sheet" onSubmit={submit}>
      <header className="sheet-head">
        <h1>點菜單</h1>
        <p>{store.name}</p>
      </header>
      <div className="sheet-meta">
        <div>日期<strong>{now}</strong></div>
        <div>品項<strong>{lines.length}</strong></div>
      </div>

      {!store.is_open && <p className="error" style={{ padding: "0 1.25rem" }}>店家目前休息中，暫停接單。</p>}

      <table className="menu">
        <thead><tr><th>品名</th><th className="col-price">單價</th><th className="col-qty">數量</th></tr></thead>
        <tbody>
          {groups.map(([cat, items]) => (
            <Rows key={cat} cat={cat} items={items} qty={qty} change={change} />
          ))}
        </tbody>
      </table>

      <div className="sheet-body">
        <div className="field">
          <label htmlFor="name">取餐稱呼</label>
          <input id="name" required maxLength={50} value={name} onChange={(e) => setName(e.target.value)} placeholder="例如：王先生" />
        </div>
        <div className="field">
          <label htmlFor="phone">手機（查詢取餐進度用）</label>
          <input id="phone" required inputMode="numeric" pattern="09\d{8}" maxLength={10} value={phone}
            onChange={(e) => setPhone(e.target.value.replace(/\D/g, ""))} placeholder="0912345678" />
        </div>
        <div className="field">
          <label htmlFor="note">備註</label>
          <input id="note" maxLength={200} value={note} onChange={(e) => setNote(e.target.value)} placeholder="不要香菜、內用、外帶…" />
        </div>
        <p className="muted" style={{ margin: 0, fontSize: ".9rem" }}>付款方式：取餐時現場付款</p>
        {error && <p className="error" role="alert" style={{ margin: 0 }}>{error}</p>}
      </div>

      <footer className="sheet-foot">
        <span className="total">合計<strong className="num">{nt(total)}</strong></span>
        <button className="btn btn-red" disabled={sending || !store.is_open || !lines.length}>
          {sending ? "送出中…" : "送出點單"}
        </button>
      </footer>
    </form>
  );
}

function Rows({ cat, items, qty, change }: {
  cat: string; items: MenuItem[]; qty: Record<number, number>; change: (id: number, d: number) => void;
}) {
  return (
    <>
      <tr className="cat"><td colSpan={3}>{cat}</td></tr>
      {items.map((m) => {
        const q = qty[m.id] ?? 0;
        return (
          <tr key={m.id} className={q ? "picked" : ""}>
            <td><span className="item-name">{m.name}</span></td>
            <td className="col-price num">{m.price}</td>
            <td className="col-qty">
              <span className="stepper">
                <button type="button" aria-label={`${m.name} 減一份`} disabled={!q} onClick={() => change(m.id, -1)}>−</button>
                <span className="qty" aria-live="polite">{q || ""}</span>
                <button type="button" aria-label={`${m.name} 加一份`} onClick={() => change(m.id, 1)}>+</button>
              </span>
            </td>
          </tr>
        );
      })}
    </>
  );
}
