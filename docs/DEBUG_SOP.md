# 錯誤排查 SOP

## 1. 收集（5 分鐘內）
- 錯誤訊息 / 狀態碼 / **X-Request-ID**（每個回應都有）
- 用 request id 搜 log：`grep "id=<request_id>" app.log`
- 影響範圍：單一店家？全部？從何時開始？最近有無部署？

## 2. 依狀態碼分流
| 狀態碼 | 先查 |
|---|---|
| 401 | token 過期（預設 60 分）、JWT_SECRET 是否與簽發時相同 |
| 403 | 角色：店員操作店主功能？ |
| 404 | 是否跨店存取（store_id 不符一律 404）、slug 是否正確 |
| 409 | 商業規則：已售完、狀態不可轉換、店家未營業、重複註冊 |
| 422 | 請求格式：看回應 `detail[].loc` 指出哪個欄位 |
| 500 | log 內 `unhandled_error` 堆疊 |
| 502 | 外部服務（LINE Pay）失敗：看 returnCode |

## 3. 重現 → 隔離 → 修正
1. 用 `/docs` 或 curl 重現
2. **先寫一個會失敗的測試**重現 bug
3. 修正 → 測試轉綠 → 全部測試仍綠
4. PR 描述寫：原因、修法、如何避免再發生

## 4. 常見問題
| 症狀 | 原因 | 解法 |
|---|---|---|
| LINE 沒收到通知 | 未設 token / 店家未綁 `line_user_id` / 當月免費則數用完（log `line_push_quota_exceeded`） | 檢查設定、升級方案 |
| LINE Pay returnCode ≠ 0000 | 簽章錯（body 與簽章用的字串不一致）、orderId 重複（1172） | 確認簽章用「實際送出的 body 字串」 |
| 報表少訂單 | 日期以 UTC 切分 | 台灣時間 = UTC+8，查詢日期需換算 |
| `psycopg.OperationalError` | DB 未啟動 / 連線字串錯 | `pg_isready`、檢查 `DATABASE_URL` |
| 重複訂單 | 前端未帶 `Idempotency-Key` | 前端每次「新的下單動作」產生一組 UUID |

## 5. 事後
- 補測試防止回歸
- 必要時更新本文件與 Coding Guideline
