import { useCallback, useEffect, useState } from "react";
import { api, minutesAgo, Order, OrderStatus } from "../api";
import { useAdmin } from "./AdminLayout";

const RAILS: { status: OrderStatus; title: string; next?: OrderStatus; action?: string }[] = [
  { status: "pending", title: "新訂單", next: "preparing", action: "開始製作" },
  { status: "preparing", title: "製作中", next: "ready", action: "出餐" },
  { status: "ready", title: "可取餐", next: "completed", action: "已取餐" },
];

export default function Board() {
  const { toast } = useAdmin();
  const [orders, setOrders] = useState<Order[]>([]);
  const [busy, setBusy] = useState<number | null>(null);

  const load = useCallback(() => api<Order[]>("/api/orders?limit=100").then(setOrders).catch(() => {}), []);

  useEffect(() => {
    load();
    const t = setInterval(load, 5000); // 輪詢：顧客新下的單 5 秒內出現
    return () => clearInterval(t);
  }, [load]);

  async function move(o: Order, status: OrderStatus) {
    setBusy(o.id);
    try {
      await api(`/api/orders/${o.id}/status`, { method: "PATCH", json: { status } });
      await load();
      if (status === "cancelled") toast(`#${o.id} 已取消`);
    } catch (e) {
      toast((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="board">
      {RAILS.map((r) => {
        const list = orders.filter((o) => o.status === r.status).sort((a, b) => a.id - b.id);
        return (
          <section key={r.status} className={`rail rail-${r.status}`} aria-label={r.title}>
            <h3>{r.title}<span className="count">{list.length}</span></h3>
            {!list.length && <p className="empty">{r.status === "pending" ? "目前沒有新單" : "空的"}</p>}
            {list.map((o) => (
              <article key={o.id} className="ticket">
                <div className="ticket-head">
                  <span className="ticket-no">#{o.id}</span>
                  <span className={`tag tag-${o.channel}`}>{o.channel === "online" ? "線上" : `POS${o.table_no ? ` ${o.table_no}` : ""}`}</span>
                </div>
                <ul>
                  {o.items.map((i) => <li key={i.menu_item_id}><span>{i.name}</span><span className="q">×{i.quantity}</span></li>)}
                </ul>
                {o.note && <p style={{ margin: 0, fontSize: ".9rem" }}>備註：{o.note}</p>}
                <p className="muted" style={{ margin: 0, fontSize: ".85rem" }}>
                  {o.customer_name ?? "現場"}・{minutesAgo(o.created_at)}・NT${o.total}
                  {o.payment_status === "paid" ? "・已付" : "・未付"}
                </p>
                <div className="ticket-actions">
                  {(o.status === "pending" || o.status === "preparing") && o.payment_status !== "paid" && (
                    <button className="btn btn-ghost btn-sm" disabled={busy === o.id} onClick={() => move(o, "cancelled")}>取消</button>
                  )}
                  <button className={`btn btn-sm ${r.status === "preparing" ? "btn-jade" : "btn-red"}`}
                    disabled={busy === o.id} onClick={() => move(o, r.next!)}>{r.action}</button>
                </div>
              </article>
            ))}
          </section>
        );
      })}
    </div>
  );
}
