# DineFlow — 多租戶餐飲 SaaS（線上點餐 + POS + 後台）

> 個人作品集專案｜Python · FastAPI · PostgreSQL · Docker · GitHub Actions · LINE Messaging API · LINE Pay v3
> 以 AI 輔助開發（Claude）完成，流程與規範見 [`docs/AI_WORKFLOW.md`](docs/AI_WORKFLOW.md)

![CI](https://github.com/<your-account>/dineflow/actions/workflows/ci.yml/badge.svg)

## 一句話
一套讓小吃店「開店 → 上架菜單 → 顧客線上點餐 / 櫃台 POS 點餐 → LINE 通知老闆 → LINE Pay 付款 → 每日營收報表」的 SaaS 後端，多家店共用同一系統、資料彼此隔離。

## 功能
| 模組 | 內容 |
|---|---|
| 開店 / 帳號 | 註冊店家（租戶）＋店主帳號、JWT 登入、新增店員、角色權限（owner / staff） |
| 菜單 | CRUD、分類、售完切換、軟刪除、價格異動稽核 |
| 線上點餐 | 公開菜單、顧客下單（手機格式驗證）、營業中檢查、Idempotency-Key 防重複下單 |
| POS | 店員建單、桌號、現金即結 |
| 訂單 | 狀態機（pending→preparing→ready→completed / cancelled），不可跳步、不可倒退 |
| LINE 通知 | 新訂單即時推播（Messaging API push，背景執行，失敗不影響下單） |
| LINE Pay | v3 Request / Confirm、HMAC 簽章、伺服器端金額比對、19 位 transactionId 精度保留 |
| 報表 | 每日營收、通路分布、熱銷 Top 5（SQL 聚合）＋ 批次腳本每日推播日結 |

## 架構
```
Client (顧客/POS/後台)
   │ HTTPS + JWT
FastAPI ── routers/   HTTP 層：驗證輸入、權限、轉換錯誤碼
   │       services/  商業邏輯：訂單、狀態機、LINE、LINE Pay（可單元測試）
   │       deps.py    身分驗證 + 角色權限（所有查詢強制帶 store_id）
SQLAlchemy 2.x
   │
PostgreSQL 16
```
多租戶策略：**Shared DB + shared schema + `store_id` 欄位隔離**。跨店存取一律回 404（不回 403，避免洩漏資源存在）。

## 品質
- **45 個測試**：單元（狀態機、計價、驗證、簽章）＋ 整合（HTTP→DB 全流程、跨租戶攻擊、權限）＋ 第三方 Mock（LINE / LINE Pay）
- **覆蓋率 94%**（PostgreSQL 實測）
- CI：ruff（含 bandit 資安規則）→ pip-audit 依賴弱點掃描 → pytest（PostgreSQL service）→ Docker build
- 資安對照 OWASP Top 10:2025：[`docs/SECURITY_CHECKLIST.md`](docs/SECURITY_CHECKLIST.md)

## 快速開始
```bash
cp .env.example .env          # 填入 JWT_SECRET
docker compose up --build     # API: http://localhost:8000/docs
```
不用 Docker：
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload            # 預設 SQLite
pytest --cov=app                         # 測試
TEST_DATABASE_URL=postgresql+psycopg://user:pw@localhost/dineflow_test pytest   # PostgreSQL 整合測試
```

## API 一覽（完整互動文件：`/docs`）
| Method | Path | 權限 |
|---|---|---|
| POST | `/api/auth/register` `/api/auth/login` | 公開 |
| POST | `/api/auth/staff` | owner |
| GET/PATCH | `/api/store` | 登入 / owner |
| GET/POST/PATCH/DELETE | `/api/menu[/{id}]` | 登入（改價 owner） |
| GET | `/api/public/stores/{slug}/menu` | 公開 |
| POST | `/api/public/stores/{slug}/orders` | 公開 |
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
