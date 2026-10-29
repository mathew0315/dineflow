# 讀懂這個專案（給自己的學習筆記）

> 目標：面試時每一行都講得出「為什麼這樣寫」。

## 閱讀順序（約 6–8 小時）
| 順序 | 檔案 | 看懂什麼 |
|---|---|---|
| 1 | `app/main.py` | FastAPI 怎麼啟動、middleware、全域錯誤處理 |
| 2 | `app/models.py` | 資料表、關聯、為何每張表有 `store_id` |
| 3 | `app/schemas.py` | Pydantic 驗證：輸入格式不對 → 自動 422 |
| 4 | `app/core/security.py` + `app/deps.py` | 密碼雜湊、JWT、`Depends` 依賴注入 |
| 5 | `app/routers/menu.py` | 最簡單的 CRUD 範例 |
| 6 | `app/services/orders.py` | 核心商業邏輯：計價、快照、冪等、狀態機 |
| 7 | `app/routers/orders.py` | 線上點餐 / POS / LINE Pay 流程 |
| 8 | `tests/` | 每個測試在驗證什麼風險 |
| 9 | `frontend/src/api.ts` | 前端怎麼帶 token、處理錯誤與 401 |
| 10 | `frontend/src/pages/OrderPage.tsx` | 顧客點餐：狀態管理、冪等鍵、表單驗證 |
| 11 | `frontend/src/admin/Board.tsx` | 訂單看板：輪詢、狀態推進 |

## 必懂關鍵字
| 關鍵字 | 一句話 |
|---|---|
| HTTP method | GET 查、POST 新增、PATCH 部分修改、DELETE 刪 |
| 狀態碼 | 2xx 成功、401 沒登入、403 沒權限、404 找不到、409 衝突、422 格式錯、5xx 伺服器錯 |
| REST | 用「名詞路徑 + HTTP method」表達操作 |
| ORM | 用 Python 物件操作資料表（SQLAlchemy） |
| JWT | 登入後拿到的簽章字串，之後每次請求帶在 `Authorization: Bearer` |
| 依賴注入 `Depends` | FastAPI 自動幫你準備 db session、目前使用者；測試時可替換 |
| 多租戶 | 多家店共用系統，用 `store_id` 隔離資料 |
| 冪等 | 同一請求送多次，結果只發生一次 |
| N+1 | 列表每筆再查一次關聯 → 改 `selectinload` 一次查完 |
| Mock | 測試時用假物件代替外部 API |

## 自己動手練（每題都改程式 + 補測試）
1. 菜單新增「描述」欄位（models → schemas → 測試）
2. 訂單列表加 `channel` 篩選
3. 報表改成「台灣時間」切日
4. 新增「店員停用」功能（只有 owner 可用）
5. 登入加失敗次數限制

## 面試常見問題（準備答案）
1. 怎麼確保 A 店看不到 B 店資料？→ `deps.current_user` 取 store_id、所有查詢過濾、跨店回 404、有測試
2. 為何價格不能相信前端？→ 可被竄改；後端以 DB 價格重算（`test_client_cannot_override_price`）
3. LINE 通知失敗會怎樣？→ 背景執行、只記 log、不影響訂單
4. LINE Pay 怎麼防偽造？→ HMAC 簽章、比對 transactionId、金額用伺服器端
5. 你怎麼用 AI 開發？怎麼確保 AI 寫的是對的？→ 講 `AI_WORKFLOW.md` 流程與 Checklist
6. 單元測試和整合測試差在哪？→ 純邏輯 vs 走 HTTP + DB
7. 為什麼用 Docker？CI 做了什麼？→ 環境一致；lint → 弱點掃描 → 測試 → build
8. 為什麼看板用輪詢不用 WebSocket？→ 免費主機會休眠、連線易斷；小店流量下輪詢簡單可靠，取捨寫在 README
9. JWT 放 localStorage 的風險？→ XSS 可竊取；改 HttpOnly Cookie + CSRF 防護（列在資安待辦）
