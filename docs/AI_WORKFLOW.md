# AI 輔助開發工作流

> 原則：**AI 產初稿，人負責正確性**。每一段 AI 產出都必須「看懂 → 驗證 → 補測試」才能合併。

## 流程
```
1 需求拆解 → 2 產生初稿 → 3 人工審查 → 4 測試驗證 → 5 Code Review(PR) → 6 上線
```

| 階段 | 我做什麼 | AI 做什麼 | 產出 / 關卡 |
|---|---|---|---|
| 1 需求拆解 | 寫 User Story、驗收條件 | 補漏掉的邊界情況、提出資料模型 | Issue（含驗收條件） |
| 2 產生初稿 | 指定檔案、介面、限制 | 依範本產程式碼 | feature branch |
| 3 人工審查 | 逐行讀懂、對照 Checklist | 解釋看不懂的段落 | 審查清單全勾 |
| 4 測試驗證 | 先想「怎麼壞掉」 | 產測試草稿；我補攻擊情境 | `pytest` 全綠、覆蓋率 ≥85% |
| 5 Code Review | 開 PR、自我 review | 第二意見 review | CI 全綠才可 merge |
| 6 上線 | 部署、看 log | 協助判讀錯誤 | `/health` 正常、smoke test |

## AI 產出審查 Checklist（每次必做）
- [ ] 每一行我都看得懂、能解釋給別人聽
- [ ] 查詢有帶 `store_id`？（租戶隔離）
- [ ] 權限檢查在？owner / staff 分清楚？
- [ ] 輸入有長度、範圍限制？
- [ ] 金額是否由後端計算，不信任前端？
- [ ] 外部 API 失敗會怎樣？有 timeout 嗎？
- [ ] 有沒有用到 AI 幻想出來的套件 / API？（到 PyPI / 官方文件查證）
- [ ] 套件版本是否為現行版本？（`pip index versions <pkg>`）
- [ ] 有沒有寫死的密鑰？

## 本專案開發中「查證後修正 / 避開」的 AI 常見陷阱
| 初稿 / 常見寫法 | 問題（經查證） | 本專案做法 |
|---|---|---|
| 用 LINE Notify 發通知 | 該服務 2025-03-31 已終止 | 改 Messaging API push |
| 用 passlib 雜湊密碼 | 套件長期未維護 | 直接用 bcrypt |
| `json.loads` 解析 LINE Pay 回應 | 19 位 transactionId 可能失去精度（JS 端尤其明顯） | `parse_int=str` 保留字串 |
| `DateTime` 無時區 | PostgreSQL 時區比較錯誤風險 | `DateTime(timezone=True)` |
| CI 使用舊版 action | 版本落後 | 以 `git ls-remote` 查證最新 major 版 |

## Prompt 範本

### P1 需求拆解
```
角色：資深後端工程師
背景：FastAPI + SQLAlchemy 2 + PostgreSQL 的多租戶餐飲 SaaS，所有業務表有 store_id。
需求：<一句話需求>
請輸出：
1. User Story 與驗收條件（Given/When/Then）
2. 需要的資料表 / 欄位變更
3. API 設計（method、path、權限、request/response）
4. 邊界情況與可能的攻擊方式（至少 5 個）
不要寫程式碼。
```

### P2 產生初稿
```
依下列規格實作，只修改指定檔案：
- 檔案：app/routers/xxx.py、app/services/xxx.py
- 規則：商業邏輯放 services，router 只做驗證與錯誤轉換
- 所有查詢必須以 CurrentUser.store_id 過濾；跨店資源回 404
- 輸入用 Pydantic，字串需 max_length
- 不得新增未列在 requirements.txt 的套件；若必要請先說明
規格：<貼上 P1 結果>
```

### P3 補測試
```
為以下程式碼寫 pytest：
- 單元測試：純邏輯（不經 HTTP）
- 整合測試：使用 tests/conftest.py 的 client、owner_a、owner_b fixture
必須包含：正常流程、輸入驗證失敗、權限不足、跨租戶存取、重複請求
外部 API 用 httpx.MockTransport，不可打真實網路。
<貼上程式碼>
```

### P4 Code Review
```
以資安與正確性角度 review 以下 diff，依嚴重度排序列出問題：
重點：OWASP Top 10:2025、多租戶隔離、交易一致性、N+1 查詢、例外處理
每個問題附：位置、原因、修正建議。沒問題就說沒問題，不要湊數。
<貼上 diff>
```

### P5 除錯
```
錯誤訊息：<完整 traceback>
重現步驟：<步驟>
預期 vs 實際：<...>
我已排除：<...>
請列出最可能的 3 個原因（附判斷依據），以及各自的驗證方式。先不要改程式碼。
```

## Git 分支流程
- `main`：永遠可部署，受保護，只能透過 PR 合併
- `feat/<功能>`、`fix/<問題>`：從 main 開，完成後開 PR
- Commit 訊息：`feat: 新增 POS 建單`、`fix: 修正報表時區`、`test:`、`docs:`
- PR 必須：CI 綠燈 ＋ 自我 review ＋ 描述「改了什麼、怎麼測」
