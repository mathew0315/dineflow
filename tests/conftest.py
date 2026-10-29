"""測試共用設定。

- 預設用 SQLite in-memory（快）；CI 設 TEST_DATABASE_URL 指向 PostgreSQL 跑整合測試
- 外部服務（LINE、LINE Pay）以 dependency_overrides 換成假物件，測試不打真實 API
"""
import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("AUTO_CREATE_TABLES", "false")  # 測試自行建表，不碰預設資料庫
os.environ.setdefault("DEMO_MODE", "false")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services import line_messaging, linepay  # noqa: E402

TEST_DB = os.getenv("TEST_DATABASE_URL", "sqlite://")


@pytest.fixture
def engine():
    if TEST_DB.startswith("sqlite"):
        eng = create_engine(TEST_DB, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    else:
        eng = create_engine(TEST_DB)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def db(engine):
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    s = Session()
    yield s
    s.close()


class FakeGateway:
    def __init__(self):
        self.requests: list[dict] = []
        self.confirms: list[tuple[str, int]] = []

    def request(self, order_id, amount, product_name, confirm_url, cancel_url):
        self.requests.append({"order_id": order_id, "amount": amount, "confirm_url": confirm_url})
        return linepay.PaymentRequestResult("2026102900000000001", "https://sandbox-web-pay.line.me/x")

    def confirm(self, transaction_id, amount):
        self.confirms.append((transaction_id, amount))


@pytest.fixture
def notifier():
    return line_messaging.NullNotifier()


@pytest.fixture
def gateway():
    return FakeGateway()


@pytest.fixture
def client(engine, notifier, gateway):
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def _get_db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[line_messaging.get_notifier] = lambda: notifier
    app.dependency_overrides[linepay.gateway_provider] = lambda: (lambda: gateway)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def register(client, slug="shop-a", email="a@example.com", password="Passw0rd!"):
    r = client.post("/api/auth/register", json={
        "store_name": f"店家 {slug}", "slug": slug, "email": email, "password": password})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def add_item(client, headers, name="滷肉飯", price=50, **kw):
    r = client.post("/api/menu", headers=headers, json={"name": name, "price": price, **kw})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def owner_a(client):
    return register(client)


@pytest.fixture
def owner_b(client):
    return register(client, slug="shop-b", email="b@example.com")
