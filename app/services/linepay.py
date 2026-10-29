"""LINE Pay Online API v3 串接（Request → 使用者付款 → Confirm）。

簽章：Base64( HMAC-SHA256( key=ChannelSecret, msg=ChannelSecret + URI + Body + Nonce ) )
Header：X-LINE-ChannelId / X-LINE-Authorization-Nonce / X-LINE-Authorization
成功判斷：returnCode == "0000"
Sandbox：https://sandbox-api-pay.line.me

安全重點：Confirm 金額一律用「伺服器端訂單金額」，不信任前端/redirect 參數。
"""
import base64
import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.config import get_settings


class PaymentError(Exception):
    pass


@dataclass
class PaymentRequestResult:
    transaction_id: str
    payment_url: str


class PaymentGateway(Protocol):
    def request(self, order_id: str, amount: int, product_name: str,
                confirm_url: str, cancel_url: str) -> PaymentRequestResult: ...

    def confirm(self, transaction_id: str, amount: int) -> None: ...


def sign(channel_secret: str, uri: str, body: str, nonce: str) -> str:
    msg = (channel_secret + uri + body + nonce).encode()
    digest = hmac.new(channel_secret.encode(), msg, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


class LinePayGateway:
    def __init__(self, channel_id: str, channel_secret: str, base_url: str,
                 client: httpx.Client | None = None):
        self._id = channel_id
        self._secret = channel_secret
        self._base = base_url
        self._client = client or httpx.Client(timeout=10.0)

    def _post(self, uri: str, payload: dict) -> dict:
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        nonce = str(uuid.uuid4())
        headers = {
            "Content-Type": "application/json",
            "X-LINE-ChannelId": self._id,
            "X-LINE-Authorization-Nonce": nonce,
            "X-LINE-Authorization": sign(self._secret, uri, body, nonce),
        }
        try:
            r = self._client.post(self._base + uri, content=body.encode(), headers=headers)
            # transactionId 為 19 位數，用 parse_int=str 保留精度
            data = json.loads(r.text, parse_int=str)
        except (httpx.HTTPError, ValueError) as e:
            raise PaymentError(f"LINE Pay 連線失敗: {e}") from e
        if data.get("returnCode") != "0000":
            raise PaymentError(f"LINE Pay 錯誤 {data.get('returnCode')}: {data.get('returnMessage')}")
        return data

    def request(self, order_id, amount, product_name, confirm_url, cancel_url):
        data = self._post("/v3/payments/request", {
            "amount": amount,
            "currency": "TWD",
            "orderId": order_id,
            "packages": [{
                "id": f"pkg-{order_id}",
                "amount": amount,
                "products": [{"name": product_name[:100], "quantity": 1, "price": amount}],
            }],
            "redirectUrls": {"confirmUrl": confirm_url, "cancelUrl": cancel_url},
        })
        info = data["info"]
        return PaymentRequestResult(str(info["transactionId"]), info["paymentUrl"]["web"])

    def confirm(self, transaction_id, amount):
        self._post(f"/v3/payments/{transaction_id}/confirm", {"amount": amount, "currency": "TWD"})


def get_payment_gateway() -> PaymentGateway:
    s = get_settings()
    if not (s.linepay_channel_id and s.linepay_channel_secret):
        raise PaymentError("LINE Pay 尚未設定（LINEPAY_CHANNEL_ID / LINEPAY_CHANNEL_SECRET）")
    return LinePayGateway(s.linepay_channel_id, s.linepay_channel_secret, s.linepay_api_base)


def gateway_provider():
    """FastAPI 依賴：回傳 gateway 工廠。測試時以 app.dependency_overrides 換成假金流。"""
    return get_payment_gateway
