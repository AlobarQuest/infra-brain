FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .
EXPOSE 8000
CMD ["sh", "-c", "export DATABASE_URL=\"${DATABASE_URL:-postgresql+asyncpg://infrabrain:${POSTGRES_PASSWORD}@postgres:5432/infrabrain}\" && : \"${DATABASE_URL:?DATABASE_URL or POSTGRES_PASSWORD must be set}\" && alembic upgrade head && python scripts/seed.py --skip-existing && uvicorn src.main:app --host 0.0.0.0 --port \"${PORT:-8000}\""]
