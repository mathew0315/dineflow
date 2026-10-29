# DineFlow — 多租戶餐飲 SaaS（線上點餐 + POS + 後台）

> 個人作品集專案｜Python · FastAPI · PostgreSQL · React · TypeScript · Docker · GitHub Actions · LINE Messaging API · LINE Pay v3
> 以 AI 輔助開發（Claude）完成，流程與規範見 [`docs/AI_WORKFLOW.md`](docs/AI_WORKFLOW.md)

![CI](https://github.com/mathew0315/dineflow/actions/workflows/ci.yml/badge.svg)

## 一句話
一套讓小吃店「開店 → 上架菜單 → 顧客掃碼點餐 / 櫃台 POS 點餐 → 廚房看板出餐 → LINE 通知老闆 → 每日營收報表」的 SaaS，多家店共用同一系統、資料彼此隔離。

## 線上 Demo
**網址：`（部署後填入）`**　｜　免費主機閒置 15 分鐘會休眠，第一次開啟約需 1 分鐘

| 身分 | 帳號 | 密碼 | 可以做什麼 |
|---|---|---|---|
| 顧客 | 不用登入 | — | 開 `/s/demo` 點餐，送出後即時看取餐進度 |
| 老闆 | `owner@demo.dineflow.app` | `demo-owner-2026` | 訂單看板、POS、改價、報表、QR 桌貼 |
| 店員 | `staff@demo.dineflow.app` | `demo-staff-2026` | 訂單看板、POS、切換售完 |

示範店資料在每次伺服器喚醒時重置；也可以在登入頁自己「開一間店」，體驗多租戶。

## 畫面
| 顧客點菜單（手機） | 取餐進度 | 廚房訂單看板 |
|---|---|---|
| 紙本點菜單風格，螢光筆標記已選品項 | 每 5 秒自動更新，可取餐時蓋章 | 新訂單 / 製作中 / 可取餐，一鍵推進 |

## 功能
| 模組 | 內容 |
|---|---|
| 開店 / 帳號 | 註冊店家（租戶）＋店主帳號、JWT 登入、新增店員、角色權限（owner / staff） |
| 菜單 | CRUD、分類、售完切換、軟刪除（下架）、價格異動稽核 |
| 顧客點餐 | 掃碼開點菜單、手機格式驗證、營業中檢查、Idempotency-Key 防重複下單、以「單號＋手機」查取餐進度 |
| POS | 店員建單、桌號、現金即結 |
| 訂單看板 | 狀態機（pending→preparing→ready→completed / cancelled），不可跳步、不可倒退；5 秒輪詢 |
| 店家設定 | 營業 / 暫停接單、產生並列印點餐 QR Code 桌貼 |
| LINE 通知 | 新訂單即時推播（Messaging API push，背景執行，失敗不影響下單） |
| LINE Pay | v3 Request / Confirm / Cancel、HMAC 簽章、伺服器端金額比對、19 位 transactionId 精度保留 |
| 報表 | 每日營收（台灣時間切日）、通路分布、熱銷 Top 5（SQL 聚合）＋ 批次腳本每日推播日結 |

## 架構
```
瀏覽器（顧客手機 / 櫃台平板 / 老闆電腦）
   │ HTTPS + JWT
FastAPI ── /            React 單頁應用（Vite build，同一個服務提供）
   │       /api/*       routers/  HTTP 層：驗證輸入、權限、轉換錯誤碼
   │                    services/ 商業邏輯：訂單、狀態機、LINE、LINE Pay、Demo 資料
   │                    deps.py   身分驗證 + 角色權限（所有查詢強制帶 store_id）
SQLAlchemy 2.x
   │
PostgreSQL 16（正式：Neon；測試：CI service）
```
- 多租戶策略：**Shared DB + shared schema + `store_id` 欄位隔離**。跨店存取一律回 404（不回 403，避免洩漏資源存在）。
- 前後端打包成**一個 Docker 映像**：部署只需一個免費 web service，也沒有跨網域 CORS 問題。

## 品質
- **52 個後端測試**：單元（狀態機、計價、驗證、簽章）＋ 整合（HTTP→DB 全流程、跨租戶攻擊、權限、時區切日）＋ 第三方 Mock（LINE / LINE Pay）
- **覆蓋率 94%**（PostgreSQL 實測）
- **瀏覽器端對端測試**（Playwright）：顧客點餐 → 看板推進 → 顧客頁自動變「可取餐」→ POS → 改價 → 報表 → 店員權限 → 錯誤處理
- CI：ruff（含 bandit 資安規則）→ pip-audit → pytest（PostgreSQL）＋ 前端 TypeScript 型別檢查與 build ＋ npm audit → Docker build
- 資安對照 OWASP Top 10:2025：[`docs/SECURITY_CHECKLIST.md`](docs/SECURITY_CHECKLIST.md)

## 快速開始
```bash
cp .env.example .env          # 填入 JWT_SECRET
docker compose up --build     # 開 http://localhost:8000 ，示範店自動建立
```
不用 Docker：
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
(cd frontend && npm ci && npm run build)   # 前端輸出到 app/static
DEMO_MODE=true uvicorn app.main:app --reload
pytest --cov=app
```
前端開發模式：`cd frontend && npm run dev`（Vite 會把 `/api` 轉給 8000 埠的後端）

## 部署
免費方案（Render + Neon），步驟見 [`docs/DEPLOY.md`](docs/DEPLOY.md)。

## API 一覽（完整互動文件：`/docs`）
| Method | Path | 權限 |
|---|---|---|
| POST | `/api/auth/register` `/api/auth/login` | 公開 |
| POST | `/api/auth/staff` | owner |
| GET/PATCH | `/api/store` | 登入 / owner |
| GET/POST/PATCH/DELETE | `/api/menu[/{id}]` | 登入（改價 owner） |
| GET | `/api/public/stores/{slug}`、`/api/public/stores/{slug}/menu` | 公開 |
| POST | `/api/public/stores/{slug}/orders` | 公開 |
| GET | `/api/public/orders/{id}?phone=` | 公開（手機驗證） |
| POST | `/api/pos/orders` | 登入 |
| GET/PATCH | `/api/orders[/{id}/status]` | 登入 |
| POST | `/api/public/orders/{id}/linepay?phone=` | 公開（手機驗證） |
| GET | `/api/public/payments/linepay/confirm`、`/cancel` | LINE Pay redirect |
| GET | `/api/reports/daily` | owner |

## 文件
- [AI 輔助開發工作流 + Prompt 範本](docs/AI_WORKFLOW.md)
- [學習筆記 / 面試準備](docs/LEARNING_GUIDE.md)
- [Coding Guideline](docs/CODING_GUIDELINE.md)
- [錯誤排查 SOP](docs/DEBUG_SOP.md)
- [資安檢查表（OWASP 2025）](docs/SECURITY_CHECKLIST.md)
- [部署指南](docs/DEPLOY.md)
- [開發路線圖](docs/ROADMAP.md)

## 技術決策紀錄
| 決策 | 原因 |
|---|---|
| LINE Messaging API 而非 LINE Notify | LINE Notify 已於 2025-03-31 停止服務 |
| 金額用整數（元） | 避免浮點誤差 |
| 訂單品項存名稱/價格快照 | 菜單改價不影響歷史訂單與報表 |
| bcrypt 直接使用（不用 passlib） | passlib 長期未維護 |
| 通知走 BackgroundTasks | 不拖慢顧客下單回應；失敗只記 log |
| 外部服務以依賴注入 | 測試可替換成假物件，不打真實 API |
| 報表切日先換算成 UTC 再查詢 | SQLite 綁定參數會丟失時區，測試抓到此差異 |
| 前端由 FastAPI 一起提供 | 單一服務部署、同源不需 CORS、免費方案只需一個 web service |
| 資料庫用 Neon 而非 Render 免費 PostgreSQL | Render 免費資料庫 30 天後過期；Neon 免費方案不刪資料 |
| 訂單看板用 5 秒輪詢而非 WebSocket | 免費主機會休眠、連線易中斷；輪詢簡單可靠，對小店流量足夠 |
