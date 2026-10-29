from datetime import UTC, date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import CurrentUser, require_owner
from app.models import Order, OrderItem, OrderStatus
from app.schemas import DailyReportOut

router = APIRouter(prefix="/api/reports", tags=["reports"])


def build_daily_report(db: Session, store_id: int, day: date) -> DailyReportOut:
    """當日營收報表：已取消訂單不計。全部用 SQL 聚合，不把資料撈進 Python 再加總。"""
    start = datetime.combine(day, time.min, tzinfo=UTC)
    end = start + timedelta(days=1)
    valid = (Order.store_id == store_id, Order.created_at >= start, Order.created_at < end,
             Order.status != OrderStatus.CANCELLED)

    count, revenue = db.execute(select(func.count(Order.id), func.coalesce(func.sum(Order.total), 0))
                                .where(*valid)).one()
    by_channel = dict(db.execute(select(Order.channel, func.sum(Order.total))
                                 .where(*valid).group_by(Order.channel)).all())
    top = db.execute(
        select(OrderItem.name, func.sum(OrderItem.quantity).label("qty"))
        .join(Order).where(*valid).group_by(OrderItem.name)
        .order_by(func.sum(OrderItem.quantity).desc()).limit(5)
    ).all()
    return DailyReportOut(
        date=day.isoformat(), order_count=count, revenue=int(revenue),
        by_channel={str(k): int(v) for k, v in by_channel.items()},
        top_items=[{"name": n, "quantity": int(q)} for n, q in top],
    )


@router.get("/daily", response_model=DailyReportOut)
def daily_report(day: date | None = Query(default=None),
                 owner: CurrentUser = Depends(require_owner), db: Session = Depends(get_db)):
    return build_daily_report(db, owner.store_id, day or datetime.now(UTC).date())
