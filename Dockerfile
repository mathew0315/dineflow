# ---- stage 1：建置前端（React + Vite） ----
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build -- --outDir /web/dist

# ---- stage 2：安裝 Python 依賴 ----
FROM python:3.13-slim AS build
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- stage 3：執行環境，只放需要的東西，映像更小、攻擊面更小 ----
FROM python:3.13-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY --from=build /install /usr/local
COPY app ./app
COPY scripts ./scripts
COPY --from=web /web/dist ./app/static

# 不以 root 執行（OWASP A02 Security Misconfiguration）
RUN useradd --create-home --uid 10001 appuser
USER appuser

# 雲端平台（Render 等）以 PORT 環境變數指定埠號
ENV PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import os,urllib.request;urllib.request.urlopen(f'http://localhost:{os.environ[\"PORT\"]}/health')"
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
