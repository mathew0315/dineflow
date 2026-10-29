"""DineFlow — 多租戶餐飲 SaaS（線上點餐 + POS + 後台）API 入口。"""
import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.db import Base, engine
from app.routers import auth, menu, orders, reports, stores

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("dineflow")
settings = get_settings()

app = FastAPI(
    title="DineFlow API",
    version="0.1.0",
    description="多租戶餐飲 SaaS：線上開店、POS、訂餐、LINE 通知、LINE Pay",
    # 正式環境關閉互動文件，減少攻擊面（OWASP A02 Security Misconfiguration）
    docs_url=None if settings.app_env == "prod" else "/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # 白名單，不用 "*"
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    """每個請求帶 request_id + 耗時 log，方便除錯與監控；並加上基本安全標頭。"""
    rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    start = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - start) * 1000
    response.headers["X-Request-ID"] = rid
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    log.info("req id=%s %s %s -> %s %.1fms", rid, request.method, request.url.path, response.status_code, ms)
    return response


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    # 未預期錯誤：完整堆疊只進 log，不回傳給使用者（OWASP A10）
    log.exception("unhandled_error path=%s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "伺服器發生錯誤，請稍後再試"})


@app.get("/health", tags=["ops"])
def health():
    return {"status": "ok"}


for r in (auth.router, stores.router, menu.router, orders.router, reports.router):
    app.include_router(r)


if settings.app_env == "dev":
    # 開發環境自動建表；正式環境應使用 migration 工具（如 Alembic）
    Base.metadata.create_all(engine)
