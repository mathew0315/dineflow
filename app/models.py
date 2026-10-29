"""資料模型。

多租戶設計：Shared database, shared schema + store_id 欄位隔離。
所有業務資料表都有 store_id，查詢一律經由 deps.current_user 取得 store_id 過濾。
金額一律用整數（新台幣元），避免浮點誤差。
"""
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Role(StrEnum):
    OWNER = "owner"
    STAFF = "staff"


class Channel(StrEnum):
    ONLINE = "online"  # 顧客線上點餐
    POS = "pos"  # 店員櫃台點餐


class OrderStatus(StrEnum):
    PENDING = "pending"
    PREPARING = "preparing"
    READY = "ready"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentMethod(StrEnum):
    CASH = "cash"
    LINEPAY = "linepay"


class PaymentStatus(StrEnum):
    UNPAID = "unpaid"
    PAID = "paid"
    REFUNDED = "refunded"


class Store(Base):
    __tablename__ = "stores"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    line_user_id: Mapped[str | None] = mapped_column(String(64))  # 老闆 LINE userId，新訂單推播用
    is_open: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[Role] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MenuItem(Base):
    __tablename__ = "menu_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(50), default="未分類")
    price: Mapped[int]
    is_available: Mapped[bool] = mapped_column(default=True)
    is_archived: Mapped[bool] = mapped_column(default=False)  # 軟刪除：歷史訂單仍引用


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("store_id", "idempotency_key", name="uq_order_idem"),
        Index("ix_orders_store_created", "store_id", "created_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    channel: Mapped[Channel] = mapped_column(String(10))
    status: Mapped[OrderStatus] = mapped_column(String(12), default=OrderStatus.PENDING)
    payment_method: Mapped[PaymentMethod] = mapped_column(String(10))
    payment_status: Mapped[PaymentStatus] = mapped_column(String(10), default=PaymentStatus.UNPAID)
    payment_txn_id: Mapped[str | None] = mapped_column(String(64))
    customer_name: Mapped[str | None] = mapped_column(String(50))
    customer_phone: Mapped[str | None] = mapped_column(String(20))
    table_no: Mapped[str | None] = mapped_column(String(10))
    note: Mapped[str | None] = mapped_column(String(200))
    total: Mapped[int]
    idempotency_key: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"))
    name: Mapped[str] = mapped_column(String(100))  # 下單當下名稱快照
    unit_price: Mapped[int]  # 下單當下價格快照：菜單改價不影響歷史訂單
    quantity: Mapped[int]
    subtotal: Mapped[int]

    order: Mapped[Order] = relationship(back_populates="items")


class AuditLog(Base):
    """敏感操作稽核紀錄（OWASP A09 Logging & Alerting）。"""

    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(50))
    detail: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
