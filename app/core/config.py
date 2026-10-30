"""集中管理設定：一律從環境變數讀取，程式碼內不放任何密鑰（OWASP A02/A04）。"""
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"  # dev / test / demo / prod
    database_url: str = "sqlite:///./dineflow.db"
    auto_create_tables: bool = True  # 正式環境應改用 migration 工具（如 Alembic）
    timezone: str = "Asia/Taipei"  # 報表「一天」的切分時區

    # 公開 Demo：啟動時重建示範店家（Render 免費方案閒置 15 分鐘會休眠，喚醒即重置）
    demo_mode: bool = False

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

    @field_validator("database_url")
    @classmethod
    def use_psycopg3_driver(cls, v: str) -> str:
        # 從 .env 範本複製時常見的貼錯：多了引號／空白、連「DATABASE_URL=」一起貼、一次貼了兩行
        v = v.strip().splitlines()[0] if v.strip() else v
        if "=" in v.split("://", 1)[0]:
            v = v.split("=", 1)[1]
        v = v.strip().strip('"').strip("'").strip()
        # 雲端資料庫（Neon、Render）給的是 postgres:// 或 postgresql://，統一指定 psycopg 3 驅動
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix):]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
