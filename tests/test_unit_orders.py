"""單元測試：純商業邏輯，不經 HTTP。"""
import pytest
from pydantic import ValidationError

from app.models import Channel, MenuItem, OrderStatus, PaymentMethod, Store
from app.schemas import OnlineOrderIn, OrderLineIn, PosOrderIn
from app.services.linepay import sign
from app.services.orders import OrderError, can_transition, create_order


@pytest.mark.parametrize(("src", "dst", "ok"), [
    (OrderStatus.PENDING, OrderStatus.PREPARING, True),
    (OrderStatus.PREPARING, OrderStatus.READY, True),
    (OrderStatus.READY, OrderStatus.COMPLETED, True),
    (OrderStatus.PENDING, OrderStatus.CANCELLED, True),
    (OrderStatus.PENDING, OrderStatus.COMPLETED, False),   # 不可跳步
    (OrderStatus.COMPLETED, OrderStatus.PENDING, False),   # 不可倒退
    (OrderStatus.CANCELLED, OrderStatus.PREPARING, False),
    (OrderStatus.READY, OrderStatus.CANCELLED, False),
])
def test_state_machine(src, dst, ok):
    assert can_transition(src, dst) is ok


def _seed(db):
    s = Store(name="A", slug="aaa")
    db.add(s)
    db.flush()
    rice = MenuItem(store_id=s.id, name="滷肉飯", price=50)
    tea = MenuItem(store_id=s.id, name="紅茶", price=30)
    sold_out = MenuItem(store_id=s.id, name="排骨", price=100, is_available=False)
    db.add_all([rice, tea, sold_out])
    db.commit()
    return s, rice, tea, sold_out


def test_total_computed_from_db_price(db):
    s, rice, tea, _ = _seed(db)
    data = PosOrderIn(items=[OrderLineIn(menu_item_id=rice.id, quantity=2),
                             OrderLineIn(menu_item_id=tea.id, quantity=1)])
    order = create_order(db, s.id, Channel.POS, data)
    assert order.total == 130
    assert [i.subtotal for i in order.items] == [100, 30]


def test_price_snapshot_not_affected_by_later_price_change(db):
    s, rice, _, _ = _seed(db)
    order = create_order(db, s.id, Channel.POS, PosOrderIn(items=[OrderLineIn(menu_item_id=rice.id, quantity=1)]))
    rice.price = 999
    db.commit()
    db.refresh(order)
    assert order.items[0].unit_price == 50 and order.total == 50


def test_sold_out_item_rejected(db):
    s, _, _, sold_out = _seed(db)
    with pytest.raises(OrderError) as e:
        create_order(db, s.id, Channel.POS, PosOrderIn(items=[OrderLineIn(menu_item_id=sold_out.id, quantity=1)]))
    assert e.value.status_code == 409


def test_idempotency_key_returns_same_order(db):
    s, rice, _, _ = _seed(db)
    data = PosOrderIn(items=[OrderLineIn(menu_item_id=rice.id, quantity=1)])
    o1 = create_order(db, s.id, Channel.POS, data, idempotency_key="k-1")
    o2 = create_order(db, s.id, Channel.POS, data, idempotency_key="k-1")
    assert o1.id == o2.id


@pytest.mark.parametrize("bad", [
    {"items": [], "customer_name": "王", "customer_phone": "0912345678"},                        # 空訂單
    {"items": [{"menu_item_id": 1, "quantity": 0}], "customer_name": "王", "customer_phone": "0912345678"},
    {"items": [{"menu_item_id": 1, "quantity": 100}], "customer_name": "王", "customer_phone": "0912345678"},
    {"items": [{"menu_item_id": 1, "quantity": 1}], "customer_name": "王", "customer_phone": "12345"},
    {"items": [{"menu_item_id": 1, "quantity": 1}] * 2, "customer_name": "王", "customer_phone": "0912345678"},
    {"items": [{"menu_item_id": 1, "quantity": 1}], "customer_name": "x" * 51, "customer_phone": "0912345678"},
])
def test_online_order_input_validation(bad):
    with pytest.raises(ValidationError):
        OnlineOrderIn(**bad)


def test_linepay_signature_matches_spec():
    # 依官方規格：Base64(HMAC-SHA256(secret, secret + uri + body + nonce))，以獨立計算比對
    import base64
    import hashlib
    import hmac
    secret, uri, body, nonce = "secret", "/v3/payments/request", '{"amount":100}', "n-1"
    expected = base64.b64encode(
        hmac.new(b"secret", (secret + uri + body + nonce).encode(), hashlib.sha256).digest()).decode()
    assert sign(secret, uri, body, nonce) == expected


def test_payment_method_default_is_cash():
    assert PosOrderIn(items=[{"menu_item_id": 1, "quantity": 1}]).payment_method == PaymentMethod.CASH
