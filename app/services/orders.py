"""訂單核心商業邏輯（與 HTTP 層分離，方便單元測試）。"""
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    AuditLog,
    Channel,
    MenuItem,
    Order,
    OrderItem,
    OrderStatus,
    PaymentStatus,
)
from app.schemas import OrderCreateBase


class OrderError(Exception):
    """商業規則錯誤，router 轉成 4xx。"""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


# 狀態機：只允許合法轉換（OWASP A06 Insecure Design：商業邏輯不可被跳步）
ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.PREPARING, OrderStatus.CANCELLED},
    OrderStatus.PREPARING: {OrderStatus.READY, OrderStatus.CANCELLED},
    OrderStatus.READY: {OrderStatus.COMPLETED},
    OrderStatus.COMPLETED: set(),
    OrderStatus.CANCELLED: set(),
}


def can_transition(current: OrderStatus, target: OrderStatus) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def create_order(
    db: Session,
    store_id: int,
    channel: Channel,
    data: OrderCreateBase,
    *,
    customer_name: str | None = None,
    customer_phone: str | None = None,
    table_no: str | None = None,
    idempotency_key: str | None = None,
) -> Order:
    # 冪等：同一個 key 重送（網路重試、重複點擊）只會建立一張單
    if idempotency_key:
        existing = db.scalar(
            select(Order).options(selectinload(Order.items))
            .where(Order.store_id == store_id, Order.idempotency_key == idempotency_key)
        )
        if existing:
            return existing

    ids = [line.menu_item_id for line in data.items]
    # 只查「本店」的品項：別家店的 menu_item_id 會被視為不存在（租戶隔離）
    menu = {
        m.id: m
        for m in db.scalars(select(MenuItem).where(MenuItem.store_id == store_id, MenuItem.id.in_(ids)))
    }

    order = Order(
        store_id=store_id,
        channel=channel,
        payment_method=data.payment_method,
        customer_name=customer_name,
        customer_phone=customer_phone,
        table_no=table_no,
        note=data.note,
        idempotency_key=idempotency_key,
        total=0,
    )
    total = 0
    for line in data.items:
        item = menu.get(line.menu_item_id)
        if item is None:
            raise OrderError(f"品項 {line.menu_item_id} 不存在", 422)
        if not item.is_available:
            raise OrderError(f"「{item.name}」已售完", 409)
        subtotal = item.price * line.quantity  # 價格一律以後端資料庫為準，不信任前端
        total += subtotal
        order.items.append(OrderItem(
            menu_item_id=item.id, name=item.name, unit_price=item.price,
            quantity=line.quantity, subtotal=subtotal,
        ))
    order.total = total
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def change_status(db: Session, order: Order, target: OrderStatus, user_id: int) -> Order:
    current = OrderStatus(order.status)
    if not can_transition(current, target):
        raise OrderError(f"不可從 {current} 變更為 {target}", 409)
    if target == OrderStatus.CANCELLED and order.payment_status == PaymentStatus.PAID:
        raise OrderError("已付款訂單需先退款才能取消", 409)
    order.status = target
    db.add(AuditLog(store_id=order.store_id, user_id=user_id, action="order.status",
                    detail=f"order={order.id} {current}->{target}"))
    db.commit()
    db.refresh(order)
    return order


def format_new_order_message(order: Order) -> str:
    lines = [f"🔔 新訂單 #{order.id}（{'線上' if order.channel == Channel.ONLINE else 'POS'}）"]
    lines += [f"・{i.name} x{i.quantity}" for i in order.items]
    lines.append(f"合計 NT${order.total}")
    if order.customer_name:
        lines.append(f"顧客：{order.customer_name}")
    return "\n".join(lines)
