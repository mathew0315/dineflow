"""Request / Response schema。輸入驗證集中在這裡（OWASP A05 Injection / A06 Insecure Design）。

原則：
- 所有字串有長度上限
- 金額、數量有上下限
- Response schema 不回傳 password_hash 等內部欄位
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import Channel, OrderStatus, PaymentMethod, PaymentStatus, Role

SLUG_PATTERN = r"^[a-z0-9-]{3,50}$"
PHONE_PATTERN = r"^09\d{8}$"  # 台灣手機格式


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Auth ----------
class RegisterStoreIn(BaseModel):
    store_name: str = Field(min_length=1, max_length=100)
    slug: str = Field(pattern=SLUG_PATTERN)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)  # bcrypt 上限 72 bytes


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class StaffIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class UserOut(ORM):
    id: int
    email: str
    role: Role


# ---------- Store ----------
class StoreOut(ORM):
    id: int
    name: str
    slug: str
    is_open: bool


class StoreUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    is_open: bool | None = None
    line_user_id: str | None = Field(default=None, pattern=r"^U[0-9a-f]{32}$")


# ---------- Menu ----------
class MenuItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    category: str = Field(default="未分類", min_length=1, max_length=50)
    price: int = Field(ge=0, le=100_000)
    is_available: bool = True


class MenuItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    category: str | None = Field(default=None, min_length=1, max_length=50)
    price: int | None = Field(default=None, ge=0, le=100_000)
    is_available: bool | None = None


class MenuItemOut(ORM):
    id: int
    name: str
    category: str
    price: int
    is_available: bool


# ---------- Order ----------
class OrderLineIn(BaseModel):
    menu_item_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=99)


class OrderCreateBase(BaseModel):
    items: list[OrderLineIn] = Field(min_length=1, max_length=50)
    payment_method: PaymentMethod = PaymentMethod.CASH
    note: str | None = Field(default=None, max_length=200)

    @field_validator("items")
    @classmethod
    def no_duplicate_items(cls, v: list[OrderLineIn]) -> list[OrderLineIn]:
        ids = [i.menu_item_id for i in v]
        if len(ids) != len(set(ids)):
            raise ValueError("同一品項請合併數量，不可重複")
        return v


class OnlineOrderIn(OrderCreateBase):
    customer_name: str = Field(min_length=1, max_length=50)
    customer_phone: str = Field(pattern=PHONE_PATTERN)


class PosOrderIn(OrderCreateBase):
    table_no: str | None = Field(default=None, max_length=10)


class OrderItemOut(ORM):
    menu_item_id: int
    name: str
    unit_price: int
    quantity: int
    subtotal: int


class OrderOut(ORM):
    id: int
    channel: Channel
    status: OrderStatus
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    customer_name: str | None
    table_no: str | None
    note: str | None
    total: int
    created_at: datetime
    items: list[OrderItemOut]


class OrderStatusIn(BaseModel):
    status: OrderStatus


class PaymentStartOut(BaseModel):
    order_id: int
    payment_url: str
    transaction_id: str


# ---------- Report ----------
class DailyReportOut(BaseModel):
    date: str
    order_count: int
    revenue: int
    by_channel: dict[str, int]
    top_items: list[dict]
