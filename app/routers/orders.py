from datetime import UTC, date, datetime, time, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import CurrentUser, current_user
from app.models import Channel, Order, OrderStatus, PaymentMethod, PaymentStatus, Store
from app.schemas import OnlineOrderIn, OrderOut, OrderStatusIn, PaymentStartOut, PosOrderIn
from app.services import line_messaging, linepay
from app.services.orders import OrderError, change_status, create_order, format_new_order_message

router = APIRouter(tags=["orders"])

IdemKey = Header(default=None, alias="Idempotency-Key", max_length=64)


def _notify_owner(store: Store, order: Order, notifier: line_messaging.Notifier) -> None:
    if store.line_user_id:
        notifier.push_text(store.line_user_id, format_new_order_message(order))


def _get_own_order(db: Session, order_id: int, store_id: int) -> Order:
    order = db.scalar(select(Order).options(selectinload(Order.items)).where(Order.id == order_id))
    if order is None or order.store_id != store_id:
        raise HTTPException(404, "訂單不存在")
    return order


# ---------- 顧客線上點餐（公開） ----------
@router.post("/api/public/stores/{slug}/orders", response_model=OrderOut, status_code=201)
def place_online_order(
    slug: str, data: OnlineOrderIn, bg: BackgroundTasks,
    idempotency_key: str | None = IdemKey,
    db: Session = Depends(get_db),
    notifier: line_messaging.Notifier = Depends(line_messaging.get_notifier),
):
    store = db.scalar(select(Store).where(Store.slug == slug))
    if store is None:
        raise HTTPException(404, "店家不存在")
    if not store.is_open:
        raise HTTPException(409, "店家目前未營業")
    try:
        order = create_order(db, store.id, Channel.ONLINE, data,
                             customer_name=data.customer_name, customer_phone=data.customer_phone,
                             idempotency_key=idempotency_key)
    except OrderError as e:
        raise HTTPException(e.status_code, str(e)) from e
    bg.add_task(_notify_owner, store, order, notifier)  # 回應後才送，不拖慢顧客
    return order


# ---------- POS（店員） ----------
@router.post("/api/pos/orders", response_model=OrderOut, status_code=201)
def place_pos_order(
    data: PosOrderIn,
    idempotency_key: str | None = IdemKey,
    user: CurrentUser = Depends(current_user), db: Session = Depends(get_db),
):
    try:
        order = create_order(db, user.store_id, Channel.POS, data,
                             table_no=data.table_no, idempotency_key=idempotency_key)
    except OrderError as e:
        raise HTTPException(e.status_code, str(e)) from e
    # 現場現金結帳：建單即視為已收款
    if order.payment_method == PaymentMethod.CASH and order.payment_status != PaymentStatus.PAID:
        order.payment_status = PaymentStatus.PAID
        db.commit()
        db.refresh(order)
    return order


# ---------- 後台訂單管理 ----------
@router.get("/api/orders", response_model=list[OrderOut])
def list_orders(
    status: OrderStatus | None = None,
    day: date | None = Query(default=None, description="YYYY-MM-DD（UTC）"),
    limit: int = Query(default=50, ge=1, le=200),
    user: CurrentUser = Depends(current_user), db: Session = Depends(get_db),
):
    q = (select(Order).options(selectinload(Order.items))  # selectinload 避免 N+1 查詢
         .where(Order.store_id == user.store_id).order_by(Order.id.desc()).limit(limit))
    if status:
        q = q.where(Order.status == status)
    if day:
        start = datetime.combine(day, time.min, tzinfo=UTC)
        q = q.where(Order.created_at >= start, Order.created_at < start + timedelta(days=1))
    return db.scalars(q).all()


@router.get("/api/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, user: CurrentUser = Depends(current_user), db: Session = Depends(get_db)):
    return _get_own_order(db, order_id, user.store_id)


@router.patch("/api/orders/{order_id}/status", response_model=OrderOut)
def update_status(order_id: int, data: OrderStatusIn,
                  user: CurrentUser = Depends(current_user), db: Session = Depends(get_db)):
    order = _get_own_order(db, order_id, user.store_id)
    try:
        return change_status(db, order, data.status, user.id)
    except OrderError as e:
        raise HTTPException(e.status_code, str(e)) from e


# ---------- LINE Pay ----------
@router.post("/api/public/orders/{order_id}/linepay", response_model=PaymentStartOut)
def start_linepay(order_id: int, request: Request, phone: str = Query(pattern=r"^09\d{8}$"),
                  db: Session = Depends(get_db),
                  gateway_factory=Depends(linepay.gateway_provider)):
    order = db.get(Order, order_id)
    # 以「訂單 id + 下單手機」驗證是本人，避免他人枚舉 id 代付或窺探（OWASP A01）
    if order is None or order.customer_phone != phone:
        raise HTTPException(404, "訂單不存在")
    if order.payment_method != PaymentMethod.LINEPAY or order.payment_status != PaymentStatus.UNPAID:
        raise HTTPException(409, "此訂單不需 LINE Pay 付款")
    try:
        gw = gateway_factory()
        base = str(request.base_url).rstrip("/")
        res = gw.request(
            order_id=f"DF{order.id}", amount=order.total, product_name=f"DineFlow 訂單 #{order.id}",
            confirm_url=f"{base}/api/public/payments/linepay/confirm?order_id={order.id}",
            cancel_url=f"{base}/api/public/payments/linepay/cancel?order_id={order.id}",
        )
    except linepay.PaymentError as e:
        raise HTTPException(502, str(e)) from e
    order.payment_txn_id = res.transaction_id
    db.commit()
    return PaymentStartOut(order_id=order.id, payment_url=res.payment_url, transaction_id=res.transaction_id)


@router.get("/api/public/payments/linepay/confirm")
def confirm_linepay(order_id: int, transactionId: str = Query(pattern=r"^\d{1,25}$"),  # noqa: N803
                    db: Session = Depends(get_db),
                    gateway_factory=Depends(linepay.gateway_provider)):
    order = db.get(Order, order_id)
    if order is None or order.payment_txn_id != transactionId:
        raise HTTPException(404, "交易不存在")
    if order.payment_status == PaymentStatus.PAID:
        return {"order_id": order.id, "payment_status": order.payment_status}  # 冪等：重複 redirect
    try:
        # 金額用伺服器端 order.total，不採用任何外部傳入值
        gateway_factory().confirm(transactionId, order.total)
    except linepay.PaymentError as e:
        raise HTTPException(502, str(e)) from e
    order.payment_status = PaymentStatus.PAID
    db.commit()
    return {"order_id": order.id, "payment_status": order.payment_status}


@router.get("/api/public/payments/linepay/cancel")
def cancel_linepay(order_id: int, db: Session = Depends(get_db)):
    """使用者在 LINE Pay 頁面取消付款後的 redirect：訂單維持未付款，可重新發起付款。"""
    order = db.get(Order, order_id)
    if order is None or order.payment_method != PaymentMethod.LINEPAY:
        raise HTTPException(404, "訂單不存在")
    if order.payment_status == PaymentStatus.UNPAID:
        order.payment_txn_id = None  # 作廢本次交易，避免舊 transactionId 被拿去 confirm
        db.commit()
    return {"order_id": order.id, "payment_status": order.payment_status, "message": "已取消付款，可重新付款"}
