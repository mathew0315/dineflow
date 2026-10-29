"""集中管理設定：一律從環境變數讀取，程式碼內不放任何密鑰（OWASP A02/A04）。"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    database_url: str = "sqlite:///./dineflow.db"

    # JWT：正式環境必須以環境變數覆寫，長度至少 32 字元
    jwt_secret: str = Field(default="dev-only-change-me-dev-only-change-me", min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # LINE Messaging API（LINE Notify 已於 2025-03-31 停止服務，改用 Messaging API push）
    line_channel_access_token: str | None = None
    line_api_base: str = "https://api.line.me"

    # LINE Pay v3（預設指向 sandbox）
    linepay_channel_id: str | None = None
    linepay_channel_secret: str | None = None
    linepay_api_base: str = "https://sandbox-api-pay.line.me"

    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
