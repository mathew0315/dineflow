"""LINE Messaging API push 通知。

背景：LINE Notify 已於 2025-03-31 終止，官方建議改用 Messaging API。
- Push message 計入官方帳號每月免費則數，超量會回 429
- 通知失敗「不可」讓訂單失敗：只記 log（OWASP A10 例外處理）
"""
import logging
from typing import Protocol

import httpx

from app.core.config import get_settings

log = logging.getLogger(__name__)


class Notifier(Protocol):
    def push_text(self, to: str, text: str) -> bool: ...


class LineMessagingNotifier:
    def __init__(self, token: str, base_url: str, client: httpx.Client | None = None):
        self._token = token
        self._base = base_url
        self._client = client or httpx.Client(timeout=5.0)

    def push_text(self, to: str, text: str) -> bool:
        try:
            r = self._client.post(
                f"{self._base}/v2/bot/message/push",
                headers={"Authorization": f"Bearer {self._token}"},
                json={"to": to, "messages": [{"type": "text", "text": text[:5000]}]},
            )
        except httpx.HTTPError as e:
            log.warning("line_push_network_error", extra={"error": str(e)})
            return False
        if r.status_code == 429:
            log.warning("line_push_quota_exceeded")
            return False
        if r.status_code >= 400:
            log.warning("line_push_failed", extra={"status": r.status_code})
            return False
        return True


class NullNotifier:
    """未設定 token 時使用（開發環境 / 測試）。"""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def push_text(self, to: str, text: str) -> bool:
        self.sent.append((to, text))
        log.info("line_push_skipped_no_token")
        return True


def get_notifier() -> Notifier:
    s = get_settings()
    if s.line_channel_access_token:
        return LineMessagingNotifier(s.line_channel_access_token, s.line_api_base)
    return NullNotifier()
