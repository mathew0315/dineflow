# 開發路線圖（4 週）

| 週 | 目標 | 交付 |
|---|---|---|
| W1 ✅ | 後端核心：多租戶、菜單、訂單、POS、LINE、LINE Pay、報表、測試、CI | 本 repo v0.1 |
| W2 ✅ | 前端：React + Vite + TypeScript（顧客點餐、取餐進度、訂單看板、POS、菜單、報表、QR 桌貼）＋ Playwright 端對端測試 | `/frontend`，v0.2 |
| W3 | 上線：Render（Docker）＋ Neon PostgreSQL（設定已完成，見 DEPLOY.md）；Alembic migration；LINE Pay sandbox 實測 | 公開 Demo 網址 |
| W4 | 加分：登入 rate limit、Webhook 綁定 LINE userId、Excel 報表匯出、Sentry 監控 | v1.0 + Demo 影片 |

## 面試展示腳本（3 分鐘）
1. 打開 Demo：顧客掃碼點餐 → 手機收到 LINE 通知
2. POS 建單 → 後台改狀態 → 報表即時更新
3. GitHub：CI 綠燈、後端 52 個測試、覆蓋率 94%、瀏覽器端對端測試
4. 講 `docs/AI_WORKFLOW.md`：查證後修正的 5 個 AI 陷阱
5. 講一個跨租戶攻擊測試，說明 A01 防護
