import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api, nt, Order, OrderStatus, STATUS_LABEL, timeOf } from "../api";

const STEPS: OrderStatus[] = ["pending", "preparing", "ready", "completed"];

export default function TrackPage() {
  const { slug = "", id = "" } = useParams();
  const [params] = useSearchParams();
  const phone = params.get("phone") ?? (() => { try { return sessionStorage.getItem(`dineflow_phone_${id}`); } catch { return null; } })() ?? "";
  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let stop = false;
    let finished = false;
    const load = () =>
      api<Order>(`/api/public/orders/${id}?phone=${phone}`)
        .then((o) => {
          if (stop) return;
          setOrder(o);
          setError("");
          finished = o.status === "completed" || o.status === "cancelled";
        })
        .catch((e: Error) => !stop && setError(e.message));
    load();
    // 每 5 秒更新一次；完成或取消後停止
    const t = setInterval(() => { if (!finished) load(); }, 5000);
    return () => { stop = true; clearInterval(t); };
  }, [id, phone]);

  if (error && !order) return <p className="sheet error" style={{ padding: "2rem", textAlign: "center" }}>{error}</p>;
  if (!order) return <p className="sheet" style={{ padding: "2rem", textAlign: "center" }}>查詢中…</p>;

  const reached = STEPS.indexOf(order.status);

  return (
    <section className="sheet">
      <header className="sheet-head">
        <h1>取餐單</h1>
        <p>單號 <span className="hand" style={{ fontSize: "1.6rem" }}>#{order.id}</span></p>
      </header>

      <div style={{ textAlign: "center", padding: "1.6rem 1rem 1.2rem" }}>
        <span className={`stamp stamp-${order.status}`} role="status">{STATUS_LABEL[order.status]}</span>
        <p className="muted" style={{ marginTop: "1rem" }}>
          {order.status === "ready" ? "餐點好了，請到櫃台取餐並付款" :
            order.status === "cancelled" ? "這張單已取消，有疑問請洽櫃台" :
            order.status === "completed" ? "謝謝光臨" : "這個頁面會自動更新，不用重新整理"}
        </p>
      </div>

      {order.status !== "cancelled" && (
        <ol className="progress" style={{ padding: "0 1.25rem 1rem" }}>
          {STEPS.map((s, i) => <li key={s} className={i <= reached ? "done" : ""}>{STATUS_LABEL[s]}</li>)}
        </ol>
      )}

      <table className="menu">
        <thead><tr><th>品名</th><th className="col-price">小計</th><th className="col-qty">數量</th></tr></thead>
        <tbody>
          {order.items.map((i) => (
            <tr key={i.menu_item_id}>
              <td>{i.name}</td>
              <td className="col-price num">{i.subtotal}</td>
              <td className="col-qty hand" style={{ fontSize: "1.3rem" }}>{i.quantity}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <footer className="sheet-foot" style={{ position: "static" }}>
        <span className="muted">下單 {timeOf(order.created_at)}</span>
        <span className="total">合計<strong className="num">{nt(order.total)}</strong></span>
      </footer>
      <p style={{ textAlign: "center", padding: "0 1rem 1.2rem", margin: 0 }}>
        <Link to={`/s/${slug}`}>再點一張</Link>
      </p>
    </section>
  );
}
