#!/bin/sh

set -eu

if [ -z "${DATABASE_URL:-}" ]; then
  : "${POSTGRES_PASSWORD:?DATABASE_URL or POSTGRES_PASSWORD must be set}"

  export DATABASE_URL="$(
    python - <<'PY'
import os
from urllib.parse import quote

user = os.environ.get("POSTGRES_USER", "infrabrain")
password = os.environ["POSTGRES_PASSWORD"]
host = os.environ.get("POSTGRES_HOST", "infrabrain-db")
port = os.environ.get("POSTGRES_PORT", "5432")
database = os.environ.get("POSTGRES_DB", "infrabrain")

print(
    f"postgresql+asyncpg://{quote(user, safe='')}:{quote(password, safe='')}@"
    f"{host}:{port}/{quote(database, safe='')}"
)
PY
  )"
fi

alembic upgrade head
python scripts/seed.py --skip-existing
exec uvicorn src.main:app --host 0.0.0.0 --port "${PORT:-8000}"
