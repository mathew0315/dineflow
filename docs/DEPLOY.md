# 部署指南（免費方案：Render + Neon）

| 元件 | 平台 | 免費額度（2026-10 查證） |
|---|---|---|
| 網站 + API（Docker） | Render Free Web Service | 每月 750 小時；閒置 15 分鐘休眠，喚醒約 1 分鐘 |
| PostgreSQL | Neon Free | 每專案 1 GB；閒置 5 分鐘暫停；資料不會因免費方案被刪除 |

> 不用 Render 免費資料庫：建立 30 天後會過期（再給 14 天寬限期後刪除）。

## 1. 建立 Neon 資料庫（約 3 分鐘）
1. 到 https://neon.com 用 GitHub 帳號登入
2. Create project：名稱 `dineflow`，Region 選 **AWS Asia Pacific (Singapore)**（離台灣與 Render 新加坡最近）
3. 在 Dashboard 按 **Connect**，複製連線字串，長得像：
   `postgresql://neondb_owner:xxxx@ep-xxxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require`
   - 程式會自動把 `postgresql://` 轉成 psycopg 3 驅動格式，直接貼即可

## 2. 用 Blueprint 部署到 Render（約 5 分鐘 + 首次 build 約 5 分鐘）
1. 到 https://render.com 用 GitHub 帳號登入
2. **New → Blueprint**，選 repo `mathew0315/dineflow`
3. Render 讀到 `render.yaml`，會要求填 `DATABASE_URL` → 貼上 Neon 連線字串
4. 按 **Apply**，等待 build 完成
5. 打開 `https://dineflow-xxxx.onrender.com`，看到首頁即完成
   - `/health` 回 `{"status":"ok"}`
   - `/s/demo` 可以點餐

## 3. 部署後
- 把網址填進 README 的「線上 Demo」
- 之後每次 push 到 `main`，Render 會自動重新部署
- 要接 LINE 推播：在 Render 的 Environment 加 `LINE_CHANNEL_ACCESS_TOKEN`，並在店家資料設定老闆的 LINE userId

## 環境變數
| 變數 | 說明 | Demo 值 |
|---|---|---|
| `DATABASE_URL` | PostgreSQL 連線字串 | Neon 提供 |
| `JWT_SECRET` | JWT 簽章密鑰（≥32 字元） | Render 自動產生 |
| `APP_ENV` | `demo` 保留 `/docs`；`prod` 會關閉 | `demo` |
| `DEMO_MODE` | 啟動時重建示範店 | `true` |
| `AUTO_CREATE_TABLES` | 啟動時建表（正式環境建議改用 Alembic migration） | `true` |
| `TIMEZONE` | 報表切日時區 | 預設 `Asia/Taipei` |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Messaging API（選填） | — |
| `LINEPAY_CHANNEL_ID` / `LINEPAY_CHANNEL_SECRET` | LINE Pay Sandbox（選填） | — |

## 常見問題
| 症狀 | 原因 / 解法 |
|---|---|
| 開網頁要等很久 | 免費主機休眠中，喚醒約 1 分鐘，屬正常 |
| Render build 失敗在 `npm ci` | 確認 `frontend/package-lock.json` 有 commit |
| 啟動後 500、log 有 `OperationalError` | `DATABASE_URL` 貼錯，或 Neon 專案被刪；到 Render → Environment 修正後 Manual Deploy |
| 啟動失敗、log 有 `invalid channel_binding value` | 連線字串夾帶引號；新版程式已自動清除，重新部署即可 |
| 啟動失敗、log 有 `password authentication failed` | 複製到被遮住的 `****` 密碼；到 Neon → Connect → Postgres database 分頁，打開 Show password 後用複製按鈕 |
| log 有 IPv6 位址 `Network is unreachable` | Render 不支援 IPv6，屬正常；看同一段 log 裡 IPv4 位址那幾行的錯誤才是真正原因 |
| 示範店改過的資料不見了 | 設計如此：`DEMO_MODE=true` 每次喚醒重置 |
