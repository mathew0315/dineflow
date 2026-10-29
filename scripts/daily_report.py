"""批次任務：每日營收結算，推播給所有已綁定 LINE 的店主。

用法（cron / 排程器每天 23:55 執行）：
    python -m scripts.daily_report            # 今天
    python -m scripts.daily_report 2026-10-29 # 指定日期

設計：
- 單一店家失敗不影響其他店家（逐店 try/except，最後回報失敗數）
- 回傳 exit code：全部成功 0、有失敗 1 → 排程系統可據此告警
"""
import logging
import sys
from datetime import UTC, date, datetime

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Store
from app.routers.reports import build_daily_report
from app.services.line_messaging import get_notifier

log = logging.getLogger("daily_report")


def run(day: date) -> int:
    notifier = get_notifier()
    failed = 0
    with SessionLocal() as db:
        stores = db.scalars(select(Store).where(Store.line_user_id.is_not(None))).all()
        for store in stores:
            try:
                rep = build_daily_report(db, store.id, day)
                top = "、".join(f"{t['name']}x{t['quantity']}" for t in rep.top_items[:3]) or "無"
                text = (f"📊 {store.name} {rep.date} 日結\n訂單 {rep.order_count} 筆\n"
                        f"營收 NT${rep.revenue}\n熱銷：{top}")
                if not notifier.push_text(store.line_user_id, text):
                    failed += 1
            except Exception:
                log.exception("daily_report_failed store=%s", store.id)
                failed += 1
    log.info("daily_report_done day=%s stores=%d failed=%d", day, len(stores), failed)
    return failed


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    target = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else datetime.now(UTC).date()
    sys.exit(1 if run(target) else 0)
