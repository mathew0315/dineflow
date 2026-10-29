import { QRCodeSVG } from "qrcode.react";
import { api, Store } from "../api";
import { useAdmin } from "./AdminLayout";

export default function Settings() {
  const { store, setStore, toast } = useAdmin();
  const orderUrl = `${location.origin}/s/${store.slug}`;

  async function toggleOpen() {
    try {
      const s = await api<Store>("/api/store", { method: "PATCH", json: { is_open: !store.is_open } });
      setStore(s);
      toast(s.is_open ? "已開始營業，顧客可以下單" : "已暫停接單");
    } catch (e) { toast((e as Error).message); }
  }

  return (
    <>
      <h2 className="no-print">店家設定</h2>
      <section className="panel no-print" style={{ marginBottom: "1rem", display: "flex", gap: "1rem", alignItems: "center", flexWrap: "wrap" }}>
        <span>目前狀態：<strong>{store.is_open ? "營業中" : "休息中"}</strong></span>
        <button className={`btn ${store.is_open ? "" : "btn-jade"}`} onClick={toggleOpen}>
          {store.is_open ? "暫停接單" : "開始營業"}
        </button>
      </section>

      <section className="sheet" style={{ maxWidth: 360, margin: "0 auto" }}>
        <header className="sheet-head"><h1>掃碼點餐</h1><p>{store.name}</p></header>
        <div style={{ display: "grid", placeItems: "center", padding: "1.5rem" }}>
          <QRCodeSVG value={orderUrl} size={220} fgColor="#1f2b38" level="M" />
          <p className="muted" style={{ wordBreak: "break-all", textAlign: "center", fontSize: ".85rem" }}>{orderUrl}</p>
        </div>
      </section>
      <p className="no-print" style={{ textAlign: "center" }}>
        <button className="btn" onClick={() => print()}>列印桌貼</button>{"　"}
        <a className="btn" href={orderUrl} target="_blank" rel="noreferrer">開啟點餐頁</a>
      </p>
    </>
  );
}
