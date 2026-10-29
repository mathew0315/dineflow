import { useEffect, useMemo, useRef, useState } from "react";
import { api, MenuItem, nt, Order } from "../api";
import { useAdmin } from "./AdminLayout";

export default function Pos() {
  const { toast } = useAdmin();
  const [menu, setMenu] = useState<MenuItem[]>([]);
  const [qty, setQty] = useState<Record<number, number>>({});
  const [table, setTable] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const idemKey = useRef(crypto.randomUUID());

  useEffect(() => { api<MenuItem[]>("/api/menu").then(setMenu).catch(() => {}); }, []);

  const groups = useMemo(() => {
    const g = new Map<string, MenuItem[]>();
    menu.forEach((m) => g.set(m.category, [...(g.get(m.category) ?? []), m]));
    return [...g.entries()];
  }, [menu]);

  const lines = menu.filter((m) => qty[m.id] > 0);
  const total = lines.reduce((s, m) => s + m.price * qty[m.id], 0);
  const add = (id: number, d: number) => setQty((q) => ({ ...q, [id]: Math.min(99, Math.max(0, (q[id] ?? 0) + d)) }));

  async function submit() {
    setBusy(true);
    try {
      const o = await api<Order>("/api/pos/orders", {
        method: "POST",
        headers: { "Idempotency-Key": idemKey.current },
        json: {
          items: lines.map((m) => ({ menu_item_id: m.id, quantity: qty[m.id] })),
          table_no: table.trim() || null, note: note.trim() || null, payment_method: "cash",
        },
      });
      toast(`#${o.id} 已送進廚房，收款 ${nt(o.total)}`);
      setQty({}); setTable(""); setNote("");
      idemKey.current = crypto.randomUUID(); // 下一張單換新的冪等鍵
    } catch (e) {
      toast((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="pos">
      <div>
        {groups.map(([cat, items]) => (
          <div key={cat} className="pos-cat">
            <h3>{cat}</h3>
            <div className="pos-grid">
              {items.map((m) => (
                <button key={m.id} className="pos-item" disabled={!m.is_available} onClick={() => add(m.id, 1)}>
                  <strong>{m.name}</strong>
                  <span className="p">{m.is_available ? nt(m.price) : "售完"}</span>
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      <aside className="sheet pos-ticket" style={{ margin: 0 }}>
        <header className="sheet-head" style={{ padding: ".6rem" }}><h1 style={{ fontSize: "1.3rem" }}>櫃台單</h1></header>
        {!lines.length ? <p className="empty">點左邊的品項加入</p> : (
          <table className="menu">
            <tbody>
              {lines.map((m) => (
                <tr key={m.id} className="picked">
                  <td><span className="item-name">{m.name}</span></td>
                  <td className="col-qty">
                    <span className="stepper">
                      <button type="button" aria-label={`${m.name} 減一份`} onClick={() => add(m.id, -1)}>−</button>
                      <span className="qty">{qty[m.id]}</span>
                      <button type="button" aria-label={`${m.name} 加一份`} onClick={() => add(m.id, 1)}>+</button>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="sheet-body">
          <div className="field">
            <label htmlFor="table">桌號</label>
            <input id="table" maxLength={10} value={table} onChange={(e) => setTable(e.target.value)} placeholder="A3、外帶…" />
          </div>
          <div className="field">
            <label htmlFor="pos-note">備註</label>
            <input id="pos-note" maxLength={200} value={note} onChange={(e) => setNote(e.target.value)} />
          </div>
        </div>
        <footer className="sheet-foot">
          <span className="total">現金<strong className="num">{nt(total)}</strong></span>
          <button className="btn btn-red" disabled={busy || !lines.length} onClick={submit}>{busy ? "送出中…" : "收款並送單"}</button>
        </footer>
      </aside>
    </div>
  );
}
