"""v0.2：公開 Demo 所需功能（顧客查單、店家資訊、台灣時區報表、Demo 資料、設定正規化）。"""
from datetime import UTC, datetime

from app.core.config import Settings
from app.models import Order
from app.services.demo import DEMO_OWNER, DEMO_SLUG, seed_demo
from tests.conftest import add_item

PHONE = "0912345678"


def _order(client, item_id, slug="shop-a"):
    return client.post(f"/api/public/stores/{slug}/orders", json={
        "items": [{"menu_item_id": item_id, "quantity": 1}], "customer_name": "王", "customer_phone": PHONE}).json()


def test_public_store_info(client, owner_a):
    r = client.get("/api/public/stores/shop-a")
    assert r.status_code == 200 and r.json()["is_open"] is True
    assert client.get("/api/public/stores/nope").status_code == 404


def test_customer_can_track_own_order_only_with_phone(client, owner_a):
    item = add_item(client, owner_a)
    order = _order(client, item["id"])
    ok = client.get(f"/api/public/orders/{order['id']}?phone={PHONE}")
    assert ok.status_code == 200 and ok.json()["status"] == "pending"
    assert "customer_phone" not in ok.json()  # 回應不回傳手機
    assert client.get(f"/api/public/orders/{order['id']}?phone=0900000000").status_code == 404
    assert client.get(f"/api/public/orders/{order['id']}").status_code == 422


def test_report_uses_taipei_day(client, owner_a, db):
    """UTC 10/28 17:00 = 台灣 10/29 01:00 → 應算在台灣的 10/29。"""
    item = add_item(client, owner_a, price=50)
    oid = _order(client, item["id"])["id"]
    o = db.get(Order, oid)
    o.created_at = datetime(2026, 10, 28, 17, 0, tzinfo=UTC)
    db.commit()
    assert client.get("/api/reports/daily?day=2026-10-29", headers=owner_a).json()["revenue"] == 50
    assert client.get("/api/reports/daily?day=2026-10-28", headers=owner_a).json()["revenue"] == 0


def test_seed_demo_is_idempotent_and_loginable(client, db):
    seed_demo(db)
    client.post("/api/public/stores/demo/orders", json={
        "items": [{"menu_item_id": client.get("/api/public/stores/demo/menu").json()[0]["id"], "quantity": 1}],
        "customer_name": "訪客", "customer_phone": PHONE})
    seed_demo(db)  # 第二次執行 = 重置
    menu = client.get(f"/api/public/stores/{DEMO_SLUG}/menu").json()
    assert len(menu) == 10
    tok = client.post("/api/auth/login", json={"email": DEMO_OWNER[0], "password": DEMO_OWNER[1]}).json()
    orders = client.get("/api/orders", headers={"Authorization": f"Bearer {tok['access_token']}"}).json()
    assert len(orders) == 5  # 訪客下的單已被重置掉
    assert {o["status"] for o in orders} == {"completed", "ready", "preparing", "pending"}


def test_seed_demo_does_not_touch_other_stores(client, owner_a, db):
    add_item(client, owner_a)
    seed_demo(db)
    seed_demo(db)
    assert len(client.get("/api/menu", headers=owner_a).json()) == 1


def test_database_url_normalized_for_cloud_providers():
    assert Settings(database_url="postgres://u:p@h/db").database_url == "postgresql+psycopg://u:p@h/db"
    assert Settings(database_url="postgresql://u:p@h/db?sslmode=require").database_url \
        == "postgresql+psycopg://u:p@h/db?sslmode=require"
    assert Settings(database_url="sqlite://").database_url == "sqlite://"


def test_archived_item_hidden_and_cannot_be_reenabled(client, owner_a):
    item = add_item(client, owner_a)
    assert client.delete(f"/api/menu/{item['id']}", headers=owner_a).status_code == 204
    assert client.get("/api/menu", headers=owner_a).json() == []
    assert client.get("/api/public/stores/shop-a/menu").json() == []
    assert client.patch(f"/api/menu/{item['id']}", headers=owner_a, json={"is_available": True}).status_code == 404
    r = client.post("/api/public/stores/shop-a/orders", json={
        "items": [{"menu_item_id": item["id"], "quantity": 1}], "customer_name": "王", "customer_phone": PHONE})
    assert r.status_code == 409  # 已下架 = 不可點（is_available=False）


def test_database_url_tolerates_pasted_quotes():
    url = "postgresql://u:p@ep-x.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    expected = "postgresql+psycopg://" + url.removeprefix("postgresql://")
    assert Settings(database_url=f'"{url}"').database_url == expected
    assert Settings(database_url=f"  {url}\n").database_url == expected


def test_database_url_tolerates_whole_env_paste():
    url = "postgresql://u:p@ep-x.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    expected = "postgresql+psycopg://" + url.removeprefix("postgresql://")
    # 實際發生過：結尾多一個引號 → libpq 報 invalid channel_binding value: "require""
    assert Settings(database_url=url + '"').database_url == expected
    # 連 KEY= 一起貼、或按「Copy .env」一次貼兩行
    assert Settings(database_url=f'DATABASE_URL="{url}"').database_url == expected
    two_lines = f'DATABASE_URL="{url}"\nDATABASE_URL_POOLED="postgresql://u:p@pooler/neondb"'
    assert Settings(database_url=two_lines).database_url == expected
