import { FormEvent, useEffect, useState } from "react";
import { api, MenuItem } from "../api";
import { useAdmin } from "./AdminLayout";

export default function MenuAdmin() {
  const { me, toast } = useAdmin();
  const owner = me.role === "owner";
  const [items, setItems] = useState<MenuItem[]>([]);
  const [prices, setPrices] = useState<Record<number, string>>({});
  const [form, setForm] = useState({ name: "", category: "", price: "" });

  const load = () => api<MenuItem[]>("/api/menu").then((m) => {
    setItems(m);
    setPrices(Object.fromEntries(m.map((i) => [i.id, String(i.price)])));
  });
  useEffect(() => { load().catch(() => {}); }, []);

  async function patch(item: MenuItem, body: Partial<MenuItem>, done: string) {
    try {
      await api(`/api/menu/${item.id}`, { method: "PATCH", json: body });
      await load();
      toast(done);
    } catch (e) { toast((e as Error).message); }
  }

  async function savePrice(item: MenuItem) {
    const p = Number(prices[item.id]);
    if (!Number.isInteger(p) || p < 0) return toast("價格請輸入 0 以上的整數");
    if (p !== item.price) await patch(item, { price: p }, `「${item.name}」改為 NT$${p}`);
  }

  async function remove(item: MenuItem) {
    if (!confirm(`下架「${item.name}」？歷史訂單仍會保留這個品項。`)) return;
    try { await api(`/api/menu/${item.id}`, { method: "DELETE" }); await load(); toast("已下架"); }
    catch (e) { toast((e as Error).message); }
  }

  async function create(e: FormEvent) {
    e.preventDefault();
    try {
      await api("/api/menu", { method: "POST", json: {
        name: form.name.trim(), category: form.category.trim() || "未分類", price: Number(form.price),
      } });
      setForm({ name: "", category: form.category, price: "" });
      await load();
      toast("已新增品項");
    } catch (err) { toast((err as Error).message); }
  }

  return (
    <>
      <h2>菜單</h2>
      {!owner && <p className="muted">店員可以切換售完；改價、新增與下架需要老闆帳號。</p>}
      <div style={{ overflowX: "auto" }}>
        <table className="grid">
          <thead><tr><th>分類</th><th>品名</th><th>價格</th><th>狀態</th>{owner && <th />}</tr></thead>
          <tbody>
            {items.map((i) => (
              <tr key={i.id}>
                <td className="muted">{i.category}</td>
                <td className={i.is_available ? "" : "soldout"}>{i.name}</td>
                <td>
                  {owner ? (
                    <input aria-label={`${i.name} 價格`} inputMode="numeric" value={prices[i.id] ?? ""}
                      onChange={(e) => setPrices({ ...prices, [i.id]: e.target.value.replace(/\D/g, "") })}
                      onBlur={() => savePrice(i)} onKeyDown={(e) => e.key === "Enter" && savePrice(i)} />
                  ) : <span className="num">{i.price}</span>}
                </td>
                <td>
                  <button className={`btn btn-sm ${i.is_available ? "" : "btn-red"}`}
                    onClick={() => patch(i, { is_available: !i.is_available }, i.is_available ? `「${i.name}」標為售完` : `「${i.name}」恢復供應`)}>
                    {i.is_available ? "供應中" : "售完"}
                  </button>
                </td>
                {owner && <td><button className="btn btn-ghost btn-sm" onClick={() => remove(i)}>下架</button></td>}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {owner && (
        <form className="panel" onSubmit={create} style={{ marginTop: "1rem", display: "grid", gap: ".8rem", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", alignItems: "end" }}>
          <div className="field"><label htmlFor="n">品名</label>
            <input id="n" required maxLength={100} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
          <div className="field"><label htmlFor="c">分類</label>
            <input id="c" maxLength={50} value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} placeholder="麵類" /></div>
          <div className="field"><label htmlFor="p">價格</label>
            <input id="p" required inputMode="numeric" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value.replace(/\D/g, "") })} /></div>
          <button className="btn btn-red">新增品項</button>
        </form>
      )}
    </>
  );
}
