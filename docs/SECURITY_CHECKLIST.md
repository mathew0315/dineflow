# 資安檢查表（OWASP Top 10:2025 對照）

| OWASP 2025 | 本專案做法 | 位置 | 測試 |
|---|---|---|---|
| A01 Broken Access Control | 所有查詢強制 `store_id`；跨店回 404；owner/staff 角色；付款與查單以「訂單 + 手機」驗證本人；已下架品項不可再啟用 | `deps.py`、各 router | `test_tenant_isolation_*`、`test_staff_permissions`、`test_linepay_flow_*` |
| A02 Security Misconfiguration | 正式環境關閉 `/docs`；CORS 白名單；安全標頭；容器非 root；前端靜態檔限制在 static 目錄內（防路徑穿越） | `main.py`、`Dockerfile` | `test_health` |
| A03 Software Supply Chain Failures | 版本鎖定（含 package-lock.json）；CI 執行 `pip-audit`、`npm audit` | `requirements.txt`、`ci.yml` | CI |
| A04 Cryptographic Failures | bcrypt 雜湊；JWT 密鑰從環境變數、長度 ≥32；HMAC-SHA256 金流簽章 | `core/security.py`、`services/linepay.py` | `test_linepay_signature_*` |
| A05 Injection | SQLAlchemy 參數化查詢；Pydantic 驗證格式與長度 | `schemas.py` | `test_sql_injection_attempt_*`、`test_online_order_input_validation` |
| A06 Insecure Design | 價格由後端計算；訂單狀態機；冪等鍵；付款金額以伺服器為準 | `services/orders.py` | `test_client_cannot_override_price`、`test_state_machine` |
| A07 Authentication Failures | 統一登入錯誤訊息；不存在帳號也執行 bcrypt（防時間差探測）；JWT 指定演算法 | `routers/auth.py` | `test_login_error_message_*`、`test_requires_token_*` |
| A08 Software or Data Integrity Failures | LINE Pay confirm 比對 transactionId 與伺服器金額；重複 confirm 冪等 | `routers/orders.py` | `test_linepay_flow_*` |
| A09 Logging & Alerting Failures | Request ID + 耗時 log；敏感操作寫入 `audit_logs`；批次任務失敗以 exit code 告警 | `main.py`、`models.AuditLog`、`scripts/` | — |
| A10 Mishandling of Exceptional Conditions | 全域例外處理不洩漏堆疊；外部服務 timeout 與失敗降級 | `main.py`、`services/` | `test_line_push_*_does_not_raise` |

## 已知限制 / 待辦
- [ ] 登入與公開下單 rate limit（防暴力破解、灌單）— 建議 Redis + slowapi 或 API Gateway
- [ ] JWT 存在 localStorage：若有 XSS 可被竊取；正式環境可改 HttpOnly Cookie + CSRF token
- [ ] Refresh token / token 撤銷清單
- [ ] LINE Pay 退款 API
- [ ] 正式環境 HTTPS（由反向代理 / 雲端 LB 終結）
- [ ] 顧客手機號碼為個資：保存期限與遮罩顯示
