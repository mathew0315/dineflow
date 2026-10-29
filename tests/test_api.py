"""整合測試：走完整 HTTP → 依賴注入 → DB。"""
from tests.conftest import add_item, register

PHONE = "0912345678"


def _online_order(client, slug="shop-a", items=None, method="cash", **headers):
    return client.post(f"/api/public/stores/{slug}/orders", headers=headers, json={
        "items": items, "customer_name": "王小明", "customer_phone": PHONE, "payment_method": method})


# ---------- Auth ----------
def test_health(client):
    r = client.get("/health")
    assert r.json() == {"status": "ok"}
    assert r.headers["X-Content-Type-Options"] == "nosniff"


def test_register_login_me(client):
    register(client)
    r = client.post("/api/auth/login", json={"email": "a@example.com", "password": "Passw0rd!"})
    assert r.status_code == 200
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"})
    assert me.json()["role"] == "owner"
    assert "password_hash" not in me.json()


def test_login_error_message_does_not_leak_account_existence(client):
    register(client)
    wrong_pw = client.post("/api/auth/login", json={"email": "a@example.com", "password": "nope"})
    no_user = client.post("/api/auth/login", json={"email": "x@example.com", "password": "nope"})
    assert wrong_pw.status_code == no_user.status_code == 401
    assert wrong_pw.json() == no_user.json()


def test_duplicate_slug_rejected(client):
    register(client)
    r = client.post("/api/auth/register", json={
        "store_name": "x", "slug": "shop-a", "email": "c@example.com", "password": "Passw0rd!"})
    assert r.status_code == 409


def test_requires_token_and_rejects_tampered_token(client, owner_a):
    assert client.get("/api/menu").status_code == 401
    bad = {"Authorization": owner_a["Authorization"][:-3] + "abc"}
    assert client.get("/api/menu", headers=bad).status_code == 401


# ---------- 權限 / 多租戶隔離（OWASP A01） ----------
def test_tenant_isolation_menu(client, owner_a, owner_b):
    item = add_item(client, owner_a)
    assert client.get("/api/menu", headers=owner_b).json() == []
    assert client.patch(f"/api/menu/{item['id']}", headers=owner_b, json={"price": 1}).status_code == 404
    assert client.delete(f"/api/menu/{item['id']}", headers=owner_b).status_code == 404


def test_tenant_isolation_orders(client, owner_a, owner_b):
    item = add_item(client, owner_a)
    order = _online_order(client, items=[{"menu_item_id": item["id"], "quantity": 1}]).json()
    assert client.get(f"/api/orders/{order['id']}", headers=owner_b).status_code == 404
    assert client.patch(f"/api/orders/{order['id']}/status", headers=owner_b,
                        json={"status": "preparing"}).status_code == 404
    assert client.get("/api/orders", headers=owner_b).json() == []


def test_cannot_order_other_stores_item(client, owner_a, owner_b):
    item_b = add_item(client, owner_b, name="B 店限定")
    r = _online_order(client, slug="shop-a", items=[{"menu_item_id": item_b["id"], "quantity": 1}])
    assert r.status_code == 422


def test_staff_permissions(client, owner_a):
    item = add_item(client, owner_a)
    assert client.post("/api/auth/staff", headers=owner_a,
                       json={"email": "s@example.com", "password": "Passw0rd!"}).status_code == 201
    tok = client.post("/api/auth/login", json={"email": "s@example.com", "password": "Passw0rd!"}).json()
    staff = {"Authorization": f"Bearer {tok['access_token']}"}
    assert client.post("/api/menu", headers=staff, json={"name": "x", "price": 1}).status_code == 403
    assert client.patch(f"/api/menu/{item['id']}", headers=staff, json={"price": 1}).status_code == 403
    assert client.patch(f"/api/menu/{item['id']}", headers=staff, json={"is_available": False}).status_code == 200
    assert client.get("/api/reports/daily", headers=staff).status_code == 403


# ---------- 點餐流程 ----------
def test_online_order_flow_and_line_notification(client, owner_a, notifier):
    client.patch("/api/store", headers=owner_a, json={"line_user_id": "U" + "a" * 32})
    rice = add_item(client, owner_a, price=50)
    tea = add_item(client, owner_a, name="紅茶", price=30)

    menu = client.get("/api/public/stores/shop-a/menu").json()
    assert {m["name"] for m in menu} == {"滷肉飯", "紅茶"}

    r = _online_order(client, items=[{"menu_item_id": rice["id"], "quantity": 2},
                                     {"menu_item_id": tea["id"], "quantity": 1}])
    assert r.status_code == 201
    order = r.json()
    assert order["total"] == 130 and order["status"] == "pending"
    assert len(notifier.sent) == 1 and "NT$130" in notifier.sent[0][1]

    for s in ("preparing", "ready", "completed"):
        assert client.patch(f"/api/orders/{order['id']}/status", headers=owner_a,
                            json={"status": s}).json()["status"] == s


def test_client_cannot_override_price(client, owner_a):
    rice = add_item(client, owner_a, price=50)
    r = client.post("/api/public/stores/shop-a/orders", json={
        "items": [{"menu_item_id": rice["id"], "quantity": 1, "price": 1}],
        "customer_name": "x", "customer_phone": PHONE, "total": 1})
    assert r.json()["total"] == 50  # 多餘欄位被忽略，價格以 DB 為準


def test_invalid_status_jump_rejected(client, owner_a):
    rice = add_item(client, owner_a)
    oid = _online_order(client, items=[{"menu_item_id": rice["id"], "quantity": 1}]).json()["id"]
    assert client.patch(f"/api/orders/{oid}/status", headers=owner_a,
                        json={"status": "completed"}).status_code == 409


def test_closed_store_rejects_orders(client, owner_a):
    rice = add_item(client, owner_a)
    client.patch("/api/store", headers=owner_a, json={"is_open": False})
    assert _online_order(client, items=[{"menu_item_id": rice["id"], "quantity": 1}]).status_code == 409


def test_pos_cash_order_is_paid_and_idempotent(client, owner_a):
    rice = add_item(client, owner_a)
    body = {"items": [{"menu_item_id": rice["id"], "quantity": 3}], "table_no": "A1"}
    h = {**owner_a, "Idempotency-Key": "pos-abc"}
    r1 = client.post("/api/pos/orders", headers=h, json=body)
    r2 = client.post("/api/pos/orders", headers=h, json=body)
    assert r1.json()["id"] == r2.json()["id"]
    assert r1.json()["payment_status"] == "paid" and r1.json()["channel"] == "pos"


def test_sql_injection_attempt_is_harmless(client, owner_a):
    add_item(client, owner_a)
    r = client.get("/api/public/stores/shop-a' OR '1'='1/menu")
    assert r.status_code == 404


# ---------- LINE Pay ----------
def test_linepay_flow_uses_server_side_amount(client, owner_a, gateway):
    rice = add_item(client, owner_a, price=80)
    order = _online_order(client, items=[{"menu_item_id": rice["id"], "quantity": 2}], method="linepay").json()
    assert order["payment_status"] == "unpaid"

    # 手機不符 → 視為不存在
    assert client.post(f"/api/public/orders/{order['id']}/linepay?phone=0900000000").status_code == 404

    r = client.post(f"/api/public/orders/{order['id']}/linepay?phone={PHONE}")
    assert r.status_code == 200 and gateway.requests[0]["amount"] == 160
    txn = r.json()["transaction_id"]

    # 偽造 transactionId → 拒絕
    assert client.get(f"/api/public/payments/linepay/confirm?order_id={order['id']}&transactionId=1").status_code == 404

    c = client.get(f"/api/public/payments/linepay/confirm?order_id={order['id']}&transactionId={txn}")
    assert c.json()["payment_status"] == "paid"
    assert gateway.confirms == [(txn, 160)]

    # 重複 redirect：冪等，不會重複 confirm
    client.get(f"/api/public/payments/linepay/confirm?order_id={order['id']}&transactionId={txn}")
    assert len(gateway.confirms) == 1

    # 已付款不可直接取消
    assert client.patch(f"/api/orders/{order['id']}/status", headers=owner_a,
                        json={"status": "cancelled"}).status_code == 409


# ---------- 報表 ----------
def test_daily_report_excludes_cancelled(client, owner_a):
    rice = add_item(client, owner_a, price=50)
    tea = add_item(client, owner_a, name="紅茶", price=30)
    _online_order(client, items=[{"menu_item_id": rice["id"], "quantity": 2}])
    client.post("/api/pos/orders", headers=owner_a, json={"items": [{"menu_item_id": tea["id"], "quantity": 1}]})
    cancel = _online_order(client, items=[{"menu_item_id": rice["id"], "quantity": 10}]).json()
    client.patch(f"/api/orders/{cancel['id']}/status", headers=owner_a, json={"status": "cancelled"})

    rep = client.get("/api/reports/daily", headers=owner_a).json()
    assert rep["order_count"] == 2
    assert rep["revenue"] == 130
    assert rep["by_channel"] == {"online": 100, "pos": 30}
    assert rep["top_items"][0] == {"name": "滷肉飯", "quantity": 2}
