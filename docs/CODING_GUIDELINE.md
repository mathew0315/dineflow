# Coding Guideline

## 分層
| 層 | 位置 | 職責 | 禁止 |
|---|---|---|---|
| Router | `app/routers/` | 解析輸入、權限、呼叫 service、轉錯誤碼 | 寫商業邏輯 |
| Service | `app/services/` | 商業規則、外部 API | 依賴 FastAPI Request |
| Schema | `app/schemas.py` | 輸入驗證、輸出格式 | 回傳內部欄位（password_hash） |
| Model | `app/models.py` | 資料表 | 商業邏輯 |

## 規則
1. **多租戶**：任何業務查詢必有 `store_id == user.store_id`；跨店一律 404
2. **金額**：整數（元）；由後端以 DB 價格計算
3. **時間**：一律 UTC、`DateTime(timezone=True)`；顯示時才轉台灣時間
4. **輸入**：所有字串有 `max_length`；數字有上下限
5. **錯誤**：預期錯誤 → `HTTPException` 明確訊息；非預期 → 全域 handler 回通用訊息，細節只進 log
6. **外部服務**：設 timeout；失敗不可拖垮主流程；以依賴注入方便測試
7. **設定 / 密鑰**：只從環境變數讀取（`app/core/config.py`）
8. **查詢**：列表用 `selectinload` 避免 N+1；統計用 SQL 聚合
9. **命名**：snake_case 函式、PascalCase 類別、API path 用複數名詞
10. **測試**：新功能至少附「正常 + 失敗 + 權限」三種測試

## 共用元件
| 元件 | 用途 |
|---|---|
| `deps.current_user` / `require_owner` | 身分與角色 |
| `services.orders.create_order` | 建單（計價、快照、冪等） |
| `services.orders.change_status` | 狀態機 + 稽核 |
| `services.line_messaging.get_notifier` | LINE 推播（無 token 自動降級） |
| `services.linepay.gateway_provider` | 金流（測試可替換） |
| `tests/conftest.py` fixtures | `client`、`owner_a`、`owner_b`、`notifier`、`gateway` |

## 工具
```bash
ruff check . --fix     # lint + 排序 + 資安規則
pytest --cov=app       # 測試
pip-audit -r requirements.txt   # 依賴弱點
```
