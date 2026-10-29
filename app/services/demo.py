"""公開 Demo 資料：啟動時重建示範店家，讓面試官打開就能操作。

- 只動 slug="demo" 這一家，其他使用者自行註冊的店家不受影響
- Render 免費方案閒置 15 分鐘會休眠，喚醒時重新啟動 → 資料自動回到初始狀態
- 帳密刻意公開在首頁（僅限 Demo 店家）
"""
import logging
from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import (
    AuditLog,
    Channel,
    MenuItem,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    Role,
    Store,
    User,
    utcnow,
)

log = logging.getLogger(__name__)

DEMO_SLUG = "demo"
DEMO_OWNER = ("owner@demo.dineflow.app", "demo-owner-2026")
DEMO_STAFF = ("staff@demo.dineflow.app", "demo-staff-2026")

MENU: list[tuple[str, str, int]] = [
    ("飯類", "滷肉飯", 35),
    ("飯類", "雞肉飯", 40),
    ("麵類", "擔仔麵", 55),
    ("麵類", "鍋燒意麵", 70),
    ("湯品", "貢丸湯", 30),
    ("湯品", "虱目魚丸湯", 40),
    ("小菜", "燙青菜", 35),
    ("小菜", "滷蛋", 15),
    ("飲料", "古早味紅茶", 25),
    ("飲料", "冬瓜茶", 25),
]

# (顧客, 品項與數量, 通路, 狀態, 幾分鐘前)
SAMPLE_ORDERS = [
    ("陳小姐", {"擔仔麵": 2, "滷蛋": 2}, Channel.ONLINE, OrderStatus.COMPLETED, 95),
    (None, {"滷肉飯": 3, "貢丸湯": 3}, Channel.POS, OrderStatus.COMPLETED, 70),
    ("林先生", {"鍋燒意麵": 1, "古早味紅茶": 1}, Channel.ONLINE, OrderStatus.READY, 12),
    (None, {"雞肉飯": 2, "燙青菜": 1}, Channel.POS, OrderStatus.PREPARING, 6),
    ("王同學", {"滷肉飯": 1, "虱目魚丸湯": 1, "冬瓜茶": 1}, Channel.ONLINE, OrderStatus.PENDING, 2),
]


def _wipe(db: Session, store_id: int) -> None:
    order_ids = select(Order.id).where(Order.store_id == store_id)
    db.execute(delete(OrderItem).where(OrderItem.order_id.in_(order_ids)))
    db.execute(delete(Order).where(Order.store_id == store_id))
    db.execute(delete(AuditLog).where(AuditLog.store_id == store_id))
    db.execute(delete(MenuItem).where(MenuItem.store_id == store_id))
    db.execute(delete(User).where(User.store_id == store_id))
    db.execute(delete(Store).where(Store.id == store_id))
    db.flush()


def seed_demo(db: Session) -> Store:
    existing = db.scalar(select(Store).where(Store.slug == DEMO_SLUG))
    if existing:
        _wipe(db, existing.id)

    store = Store(name="阿明麵食館（示範店）", slug=DEMO_SLUG, is_open=True)
    db.add(store)
    db.flush()

    db.add_all([
        User(store_id=store.id, email=DEMO_OWNER[0], password_hash=hash_password(DEMO_OWNER[1]), role=Role.OWNER),
        User(store_id=store.id, email=DEMO_STAFF[0], password_hash=hash_password(DEMO_STAFF[1]), role=Role.STAFF),
    ])
    items = {name: MenuItem(store_id=store.id, category=cat, name=name, price=price) for cat, name, price in MENU}
    db.add_all(items.values())
    db.flush()

    now = utcnow()
    for customer, lines, channel, status, minutes_ago in SAMPLE_ORDERS:
        order = Order(
            store_id=store.id, channel=channel, status=status,
            payment_method=PaymentMethod.CASH,
            payment_status=PaymentStatus.PAID if channel == Channel.POS or status == OrderStatus.COMPLETED
            else PaymentStatus.UNPAID,
            customer_name=customer, customer_phone="0912345678" if customer else None,
            table_no=None if customer else "A3",
            total=0, created_at=now - timedelta(minutes=minutes_ago),
        )
        for name, qty in lines.items():
            item = items[name]
            order.items.append(OrderItem(menu_item_id=item.id, name=name, unit_price=item.price,
                                         quantity=qty, subtotal=item.price * qty))
        order.total = sum(i.subtotal for i in order.items)
        db.add(order)

    db.commit()
    log.info("demo_seeded store=%s", store.id)
    return store
