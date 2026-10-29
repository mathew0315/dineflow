import { useEffect, useState } from "react";
import { api, DailyReport, nt } from "../api";

export default function Report() {
  const [rep, setRep] = useState<DailyReport | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<DailyReport>("/api/reports/daily").then(setRep).catch((e: Error) => setError(e.message));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!rep) return <p>計算中…</p>;

  const max = Math.max(1, ...rep.top_items.map((t) => t.quantity));
  const avg = rep.order_count ? Math.round(rep.revenue / rep.order_count) : 0;

  return (
    <>
      <h2>今日報表 <span className="muted" style={{ fontSize: ".95rem", fontWeight: 400 }}>{rep.date}（台灣時間，不含取消單）</span></h2>
      <div className="kpis">
        <div className="kpi"><div className="v num">{nt(rep.revenue)}</div><div className="l">營收</div></div>
        <div className="kpi"><div className="v num">{rep.order_count}</div><div className="l">訂單數</div></div>
        <div className="kpi"><div className="v num">{nt(avg)}</div><div className="l">平均客單價</div></div>
      </div>
      <div className="kpis" style={{ gridTemplateColumns: "1fr 2fr" }}>
        <section className="panel">
          <h3 style={{ marginTop: 0, fontSize: "1rem" }}>通路</h3>
          <p style={{ margin: ".3rem 0" }}>線上點餐 <strong className="num">{nt(rep.by_channel.online ?? 0)}</strong></p>
          <p style={{ margin: ".3rem 0" }}>櫃台 POS <strong className="num">{nt(rep.by_channel.pos ?? 0)}</strong></p>
        </section>
        <section className="panel">
          <h3 style={{ marginTop: 0, fontSize: "1rem" }}>熱銷品項</h3>
          {!rep.top_items.length && <p className="muted">今天還沒有訂單</p>}
          {rep.top_items.map((t) => (
            <div key={t.name} className="bar-row">
              <span>{t.name}</span>
              <span className="bar" style={{ width: `${(t.quantity / max) * 100}%` }} />
              <span className="hand num" style={{ fontSize: "1.2rem" }}>{t.quantity}</span>
            </div>
          ))}
        </section>
      </div>
    </>
  );
}
