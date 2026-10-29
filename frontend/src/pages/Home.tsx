import { Link } from "react-router-dom";

const DEMO = {
  owner: ["owner@demo.dineflow.app", "demo-owner-2026"],
  staff: ["staff@demo.dineflow.app", "demo-staff-2026"],
};

export default function Home() {
  return (
    <main className="home">
      <section className="home-hero">
        <div>
          <h1>小吃店的點菜單，搬到手機上。</h1>
          <p>
            顧客掃桌上的 QR Code 勾選點餐，廚房看板即時出現新單，櫃台也能直接 POS 建單。
            多家店共用一套系統，資料彼此隔離。
          </p>
          <p className="muted">
            這是一個可操作的作品集 Demo。示範店的資料每次伺服器喚醒時會重置，可以放心亂按。
          </p>
        </div>
        <div className="sheet mini-sheet" aria-hidden="true">
          <div className="sheet-head"><h1>點菜單</h1></div>
          <table className="menu">
            <tbody>
              <tr className="cat"><td colSpan={3}>麵類</td></tr>
              <tr className="picked"><td><span className="item-name">擔仔麵</span></td><td className="col-price">55</td><td className="col-qty hand" style={{ fontSize: "1.4rem" }}>2</td></tr>
              <tr><td><span className="item-name">鍋燒意麵</span></td><td className="col-price">70</td><td className="col-qty" /></tr>
              <tr className="cat"><td colSpan={3}>小菜</td></tr>
              <tr className="picked"><td><span className="item-name">滷蛋</span></td><td className="col-price">15</td><td className="col-qty hand" style={{ fontSize: "1.4rem" }}>2</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="home-paths">
        <div className="path">
          <h2>我是顧客</h2>
          <p>用手機打開示範店的點菜單，送出後可以即時看取餐進度。</p>
          <Link className="btn btn-red" to="/s/demo">開始點餐</Link>
        </div>
        <div className="path">
          <h2>我是老闆</h2>
          <p>看訂單看板、管理菜單與價格、查看今日營收、印出桌貼 QR Code。</p>
          <div className="cred">帳號 <code>{DEMO.owner[0]}</code><br />密碼 <code>{DEMO.owner[1]}</code></div>
          <Link className="btn" to={`/login?email=${encodeURIComponent(DEMO.owner[0])}`}>以老闆身分登入</Link>
        </div>
        <div className="path">
          <h2>我是店員</h2>
          <p>櫃台 POS 點餐、推進出餐狀態、切換售完。改價與報表需要老闆權限。</p>
          <div className="cred">帳號 <code>{DEMO.staff[0]}</code><br />密碼 <code>{DEMO.staff[1]}</code></div>
          <Link className="btn" to={`/login?email=${encodeURIComponent(DEMO.staff[0])}`}>以店員身分登入</Link>
        </div>
      </section>

      <section className="home-tech">
        <h2>技術與原始碼</h2>
        <ul>
          <li>後端 Python FastAPI + PostgreSQL，前端 React + TypeScript，一個 Docker 映像部署</li>
          <li>50+ 個自動化測試、GitHub Actions CI、對照 OWASP Top 10:2025 的資安設計</li>
          <li>
            <a href="https://github.com/mathew0315/dineflow">GitHub 原始碼</a>
            {"　"}
            <a href="/docs">API 互動文件</a>
          </li>
        </ul>
      </section>
    </main>
  );
}
