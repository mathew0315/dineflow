"""第三方串接測試：用 httpx.MockTransport 攔截 HTTP，驗證「送出的請求」與「錯誤處理」。"""
import json

import httpx
import pytest

from app.services.line_messaging import LineMessagingNotifier
from app.services.linepay import LinePayGateway, PaymentError, sign


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


# ---------- LINE Messaging API ----------
def test_line_push_sends_correct_request():
    seen = {}

    def handler(req: httpx.Request):
        seen["url"] = str(req.url)
        seen["auth"] = req.headers["Authorization"]
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json={})

    n = LineMessagingNotifier("tok", "https://api.line.me", _client(handler))
    assert n.push_text("U123", "hi") is True
    assert seen["url"] == "https://api.line.me/v2/bot/message/push"
    assert seen["auth"] == "Bearer tok"
    assert seen["body"] == {"to": "U123", "messages": [{"type": "text", "text": "hi"}]}


@pytest.mark.parametrize("resp", [
    httpx.Response(429, json={"message": "You have reached your monthly limit."}),
    httpx.Response(500),
])
def test_line_push_failure_does_not_raise(resp):
    n = LineMessagingNotifier("tok", "https://api.line.me", _client(lambda r: resp))
    assert n.push_text("U123", "hi") is False


def test_line_push_network_error_does_not_raise():
    def boom(req):
        raise httpx.ConnectError("down")
    assert LineMessagingNotifier("t", "https://x", _client(boom)).push_text("U1", "hi") is False


# ---------- LINE Pay v3 ----------
def test_linepay_request_signs_and_keeps_19_digit_txn_id():
    seen = {}

    def handler(req: httpx.Request):
        body = req.content.decode()
        nonce = req.headers["X-LINE-Authorization-Nonce"]
        seen["sig_ok"] = req.headers["X-LINE-Authorization"] == sign("sec", req.url.path, body, nonce)
        seen["channel"] = req.headers["X-LINE-ChannelId"]
        seen["body"] = json.loads(body)
        # 19 位數 transactionId（直接寫入原始 JSON，避免被當 float）
        return httpx.Response(200, content=b'{"returnCode":"0000","returnMessage":"Success.",'
                              b'"info":{"transactionId":2026102912345678901,'
                              b'"paymentUrl":{"web":"https://pay/web","app":"line://pay"}}}')

    gw = LinePayGateway("cid", "sec", "https://sandbox-api-pay.line.me", _client(handler))
    res = gw.request("DF1", 160, "訂單", "https://c", "https://x")
    assert seen["sig_ok"] and seen["channel"] == "cid"
    assert seen["body"]["amount"] == 160 and seen["body"]["currency"] == "TWD"
    assert seen["body"]["packages"][0]["amount"] == 160
    assert res.transaction_id == "2026102912345678901"  # 精度未流失
    assert res.payment_url == "https://pay/web"


def test_linepay_error_return_code_raises():
    resp = httpx.Response(200, json={"returnCode": "1172", "returnMessage": "Existing same orderId."})
    gw = LinePayGateway("cid", "sec", "https://x", _client(lambda r: resp))
    with pytest.raises(PaymentError, match="1172"):
        gw.confirm("123", 100)


def test_linepay_confirm_path():
    seen = {}

    def handler(req):
        seen["path"] = req.url.path
        return httpx.Response(200, json={"returnCode": "0000", "returnMessage": "Success."})

    LinePayGateway("cid", "sec", "https://x", _client(handler)).confirm("999", 100)
    assert seen["path"] == "/v3/payments/999/confirm"
