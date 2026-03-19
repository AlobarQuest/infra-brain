# Infra Brain — Technical Architecture

---

## Project Structure

```
infra-brain/
├── src/
│   ├── main.py                  # FastAPI app + FastMCP server mount
│   ├── config.py                # Settings via pydantic-settings
│   ├── db/
│   │   ├── __init__.py
│   │   ├── engine.py            # Async SQLAlchemy engine + session factory
│   │   └── models.py            # ORM models: Version, Rule, Combo, Lesson
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── versions.py          # CRUD for versions table
│   │   ├── rules.py             # CRUD for rules table
│   │   ├── combos.py            # CRUD for combos table
│   │   └── lessons.py           # CRUD for lessons table
│   └── tools/
│       ├── __init__.py
│       ├── versions.py          # MCP tools: get_version, list_versions, update_version
│       ├── rules.py             # MCP tools: get_rules, add_rule
│       ├── combos.py            # MCP tools: get_combo, list_combos
│       └── lessons.py           # MCP tools: add_lesson, search_lessons
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial_schema.py
├── scripts/
│   ├── seed.py                  # Load initial data from seed/data.json
│   └── start.sh                 # Build runtime DATABASE_URL, run migrations/seed, start uvicorn
├── seed/
│   └── data.json                # Initial version pins, rules, combos, lessons
├── tests/
│   ├── test_versions.py
│   ├── test_rules.py
│   └── test_lessons.py
├── alembic.ini
├── docker-compose.yml           # Production-shape: app + postgres
├── docker-compose.local.yml     # Adds port exposure for local dev
├── Dockerfile
├── requirements.txt
├── .env.example
├── .github/
│   └── workflows/
│       └── deploy.yml          # Optional legacy GHCR/webhook workflow
└── README.md
```

---

## Database Schema

### Table: `versions`

Stores the canonical pinned version for every package used in the portfolio.

```sql
CREATE TABLE versions (
    id          SERIAL PRIMARY KEY,
    package     TEXT NOT NULL UNIQUE,       -- e.g. "sqlalchemy", "python", "postgres"
    canonical   TEXT NOT NULL,              -- e.g. "2.0.36" — pin exactly this
    min_allowed TEXT,                       -- e.g. "2.0.0" — anything below is blocked
    blocked_above TEXT,                     -- e.g. "2.1.0" — anything >= this is blocked
    reason      TEXT NOT NULL,              -- why this version was chosen / why others blocked
    confirmed_in TEXT[],                    -- app slugs where this version is validated
    ecosystem   TEXT NOT NULL DEFAULT 'python', -- "python" | "node" | "docker" | "system"
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by  TEXT NOT NULL DEFAULT 'ai-capture'
);
```

**Example rows:**

| package | canonical | min_allowed | blocked_above | reason | confirmed_in | ecosystem |
|---|---|---|---|---|---|---|
| python | 3.12 | 3.12.0 | 3.13.0 | 3.13 ecosystem not validated | {contacts,booking-assistant,inbox-assistant} | system |
| sqlalchemy | 2.0.36 | 2.0.0 | 2.1.0 | async session breaking change in 2.1 | {contacts,inbox-assistant,real-estate-analyzer} | python |
| fastapi | 0.115.6 | 0.115.0 | null | latest 0.115.x; requires pydantic v2 | {contacts,booking-assistant} | python |
| uvicorn | 0.32.1 | 0.30.0 | null | use uvicorn[standard] extras | {contacts,booking-assistant} | python |
| pydantic | 2.10.3 | 2.0.0 | null | v2 only; v1 syntax breaks fastapi 0.115.x | {contacts,inbox-assistant} | python |
| alembic | 1.13.3 | 1.13.0 | null | pairs with sqlalchemy 2.0.x | {contacts,inbox-assistant} | python |
| asyncpg | 0.29.0 | 0.29.0 | null | async postgres driver for fastapi apps | {contacts,inbox-assistant} | python |
| psycopg2-binary | 2.9.10 | 2.9.0 | null | sync driver; use only when async not needed | {} | python |
| postgres | 16-alpine | null | null | docker image; never use :latest tag | {contacts,lifeops-portal,inbox-assistant} | docker |
| redis | 7-alpine | null | null | docker image; always appendonly yes | {contacts} | docker |
| python-base-image | 3.12-slim | null | null | not alpine — glibc issues with compiled deps | {contacts,booking-assistant} | docker |
| node | 20-alpine | null | null | docker base for nextjs apps | {lifeops-portal} | docker |
| nextjs | 14.x | 14.0.0 | null | app router; never source-build on VPS | {lifeops-portal} | node |
| prisma | 5.x | 5.0.0 | null | pairs with nextjs 14 and node 20 | {lifeops-portal} | node |
| typescript | 5.x | 5.0.0 | null | all node projects | {lifeops-portal} | node |
| react | 18.x | 18.0.0 | null | pairs with vite 5 | {real-estate-analyzer} | node |
| vite | 5.x | 5.0.0 | null | no create-react-app | {real-estate-analyzer} | node |
| rq | 1.16.x | 1.16.0 | null | redis queue; pairs with redis-py 5.x | {contacts} | python |
| redis-py | 5.x | 5.0.0 | null | python redis client | {contacts} | python |
| pytest | 7.x | 7.0.0 | null | test runner | {contacts,booking-assistant} | python |
| pytest-asyncio | 0.23.x | 0.23.0 | null | async test support | {contacts,inbox-assistant} | python |
| httpx | 0.28.x | 0.27.0 | null | async http client; test client for fastapi | {contacts} | python |
| pydantic-settings | 2.7.x | 2.0.0 | null | settings management from env vars | {contacts} | python |

---

### Table: `rules`

Hard constraints and anti-patterns. Agents must check BLOCK rules before proceeding.

```sql
CREATE TABLE rules (
    id          SERIAL PRIMARY KEY,
    severity    TEXT NOT NULL CHECK (severity IN ('BLOCK', 'WARN', 'INFO')),
    category    TEXT NOT NULL,   -- "deployment" | "secrets" | "database" | "docker" | "ci" | "general"
    rule        TEXT NOT NULL,   -- the rule statement, actionable and specific
    reason      TEXT NOT NULL,   -- why this rule exists
    source_app  TEXT,            -- app slug where this was learned (if from incident)
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Example rows:**

| severity | category | rule | reason | source_app |
|---|---|---|---|---|
| BLOCK | deployment | Never source-build Next.js or TypeScript apps on the VPS | Host CPU cannot handle npm build; causes stalled Coolify deploys | lifeops-portal |
| BLOCK | secrets | Never commit secrets or .env files to git | Security; use BWS + Coolify env vars | null |
| BLOCK | docker | Never use :latest tag for any Docker image | Unpredictable upgrades break reproducibility | null |
| BLOCK | deployment | Disable Coolify scheduled jobs for Flavor C apps | Duplicates the in-stack scheduler sidecar; causes double backups and probes | contacts |
| BLOCK | ci | Coolify webhook must be triggered after GHCR push, not before | Early trigger causes Coolify to pull stale image | null |
| WARN | deployment | Flavor A apps (SQLite) need manual backup setup — Coolify auto-backup only works for Postgres | SQLite backup requires Coolify scheduled job calling backup.sh | booking-assistant |
| WARN | database | Do not use Redis as a primary datastore | Redis is cache/queue only; data must survive Redis restart via Postgres | contacts |
| WARN | docker | python:3.12-alpine causes issues with compiled dependencies | glibc missing in alpine; use python:3.12-slim | null |
| WARN | deployment | Google OAuth redirect URIs must match exactly — preview and production need separate URIs | Mismatched URI causes silent OAuth failure with no useful error | booking-assistant |
| WARN | ci | Always pin SHA for third-party GitHub Actions (actions/checkout@v4 etc.) | Floating tags can be hijacked | null |
| INFO | database | Run alembic upgrade head at container startup, not in Dockerfile build | Build-time migration has no DB connection; runtime migration is correct | null |
| INFO | deployment | Health check in Coolify must use 127.0.0.1 not the public domain | Coolify checks internal container network; external domain adds unnecessary DNS round-trip | null |
| INFO | general | Infra Brain itself is the source of truth — update it when standards change | Do not let agents infer standards from existing app code; query Infra Brain first | null |

---

### Table: `combos`

Validated dependency sets for common stack patterns. Agents use these to get an entire
stack's worth of pins in a single call instead of looking up packages one by one.

```sql
CREATE TABLE combos (
    id           SERIAL PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,   -- e.g. "python-fastapi-stack"
    description  TEXT NOT NULL,
    packages     JSONB NOT NULL,         -- {"fastapi": "0.115.6", "sqlalchemy": "2.0.36", ...}
    ecosystem    TEXT NOT NULL,          -- "python" | "node"
    flavor       TEXT,                  -- "A" | "B" | "C" | null (applies to all)
    confirmed_in TEXT[],                 -- app slugs
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Example rows:**

**`python-fastapi-stack`** (Flavor B/C Python apps)
```json
{
  "python": "3.12",
  "fastapi": "0.115.6",
  "uvicorn[standard]": "0.32.1",
  "sqlalchemy": "2.0.36",
  "alembic": "1.13.3",
  "asyncpg": "0.29.0",
  "pydantic": "2.10.3",
  "pydantic-settings": "2.7.0",
  "python-dotenv": "1.0.1",
  "httpx": "0.28.1",
  "pytest": "7.4.4",
  "pytest-asyncio": "0.23.8"
}
```

**`python-fastapi-rq-stack`** (Flavor C additions on top of fastapi-stack)
```json
{
  "rq": "1.16.2",
  "redis": "5.2.1"
}
```

**`nextjs-prisma-stack`** (Flavor B Node apps)
```json
{
  "node": "20",
  "next": "14.2.18",
  "react": "18.3.1",
  "react-dom": "18.3.1",
  "typescript": "5.7.2",
  "prisma": "5.22.0",
  "@prisma/client": "5.22.0"
}
```

**`react-vite-stack`** (standalone React frontends)
```json
{
  "react": "18.3.1",
  "react-dom": "18.3.1",
  "vite": "5.4.11",
  "typescript": "5.7.2",
  "tailwindcss": "3.4.16",
  "@tanstack/react-query": "5.62.7",
  "recharts": "2.14.1"
}
```

---

### Table: `lessons`

Freeform production discoveries, incident post-mortems, and hard-won knowledge.
Unlike the other tables, lessons are narrative — the schema is loose by design.

```sql
CREATE TABLE lessons (
    id          SERIAL PRIMARY KEY,
    app         TEXT,               -- app slug this lesson came from (null = portfolio-wide)
    title       TEXT NOT NULL,      -- short summary for search/display
    content     TEXT NOT NULL,      -- full lesson detail
    tags        TEXT[],             -- searchable tags e.g. {"oauth", "google", "coolify"}
    severity    TEXT NOT NULL DEFAULT 'INFO' CHECK (severity IN ('CRITICAL', 'WARN', 'INFO')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    source      TEXT NOT NULL DEFAULT 'ai-capture'
);
```

**Example rows (from portfolio history):**

| app | title | severity | tags |
|---|---|---|---|
| lifeops-portal | Next.js source builds stall VPS deploys | CRITICAL | {nextjs, coolify, deployment, cpu} |
| booking-assistant | Google OAuth PKCE verifier must persist across redirect | WARN | {google, oauth, pkce, fastapi} |
| booking-assistant | Google OAuth redirect URI must match exactly per environment | WARN | {google, oauth, coolify, preview} |
| contacts | Coolify scheduled jobs duplicate in-stack scheduler sidecar | WARN | {coolify, scheduler, flavor-c} |
| contacts | Scheduler sidecar must be in-stack, not external cron | INFO | {scheduler, docker, flavor-c} |
| contacts | Health check exempt paths must include /api/health for Coolify probes | INFO | {coolify, health-check, basic-auth} |

---

## MCP Tool Inventory

All tools are exposed via FastMCP mounted on the FastAPI app.
MCP endpoint: `https://infra-brain.devonwatkins.com/mcp`

### Version Tools

**`get_version(package: str)`**
Returns the full version record for one package.
Returns: `{package, canonical, min_allowed, blocked_above, reason, confirmed_in, ecosystem}`
Error if not found: `{"error": "not_found", "package": "..."}`

**`list_versions(ecosystem?: str)`**
Returns all version records, optionally filtered by ecosystem.
Ecosystems: `"python"` | `"node"` | `"docker"` | `"system"`

**`update_version(package: str, canonical: str, reason?: str, confirmed_in?: list[str])`**
Updates the canonical version for a package. Used when an agent validates a new version.
Requires: package must already exist. Use `add_version` for new packages.

**`add_version(package, canonical, ecosystem, reason, min_allowed?, blocked_above?, confirmed_in?)`**
Adds a new package to the registry.

### Rule Tools

**`get_rules(category?: str, severity?: str)`**
Returns rules, optionally filtered by category and/or severity.
Always check `severity="BLOCK"` rules before starting any deployment task.

**`add_rule(severity, category, rule, reason, source_app?)`**
Adds a new rule. Used when a new constraint is discovered.

### Combo Tools

**`get_combo(name: str)`**
Returns the full package set for a named stack combo.

**`list_combos(ecosystem?: str, flavor?: str)`**
Returns all combos, optionally filtered.

### Lesson Tools

**`search_lessons(query: str, app?: str, tags?: list[str])`**
Full-text search across lesson titles and content.
Returns ranked results. Always call this before working on a known-problematic area.

**`add_lesson(title, content, app?, tags?, severity?)`**
Adds a new lesson. Called by agents after discovering something worth recording.

### Health Tool

**`health()`**
Returns `{"status": "ok", "app": "infra-brain", "db": "connected"}`.
Used by Coolify health checks and MCP client connectivity tests.

---

## HTTP Surface

The FastAPI app exposes one health endpoint and mounts FastMCP at `/mcp`.

```
GET  /api/health   → health check (Coolify probe target)
ANY  /mcp          → FastMCP SSE endpoint
```

Notes:
- `/api/health` is the only dedicated REST endpoint today.
- `/mcp` expects MCP/SSE semantics. Plain browser or `curl` requests without
  `Accept: text/event-stream` return a `Not Acceptable` error from FastMCP.
- There are no separate `/api/versions`, `/api/rules`, or `/api/lessons` REST endpoints in the current app.

---

## Configuration (Environment Variables)

Two layers of configuration exist in the current project:

```
# App settings consumed by src/config.py
DATABASE_URL=postgresql+asyncpg://infrabrain:PASSWORD@localhost:5432/infrabrain
APP_NAME=infra-brain
APP_ENV=development
LOG_LEVEL=INFO
PORT=8000
ALLOWED_HOSTS=localhost

# Inline compose deployment inputs consumed by scripts/start.sh
POSTGRES_HOST=infrabrain-db
POSTGRES_PORT=5432
POSTGRES_DB=infrabrain
POSTGRES_USER=infrabrain
POSTGRES_PASSWORD=changeme
```

Notes:
- `.env.example` ships with the repo for local development.
- In the live Coolify deployment, only `POSTGRES_PASSWORD`, `APP_ENV`, and `LOG_LEVEL`
  need to be set in the UI. The compose file supplies the other `POSTGRES_*` values.
- `scripts/start.sh` URL-encodes the password before building `DATABASE_URL`.

---

## Alembic Migration: Initial Schema

`alembic/versions/0001_initial_schema.py` creates all four tables in one migration.
Seed data is loaded separately via `scripts/seed.py` which reads `seed/data.json`.

Runtime startup sequence (implemented in `scripts/start.sh`):
```bash
alembic upgrade head
python scripts/seed.py --skip-existing
uvicorn src.main:app --host 0.0.0.0 --port "${PORT:-80}"
```

---

## Dockerfile (Flavor B pattern)

```dockerfile
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
EXPOSE 80
CMD ["sh", "/app/scripts/start.sh"]
```

Notes:
- The deployed container listens on port `80`.
- Local development maps host `8000` to container `80`.
- `seed.py --skip-existing` means seeding is idempotent — safe to run on every startup
  without overwriting manual edits.

---

## docker-compose.yml (production shape for local dev parity)

```yaml
services:
  infrabrain-db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: infrabrain
      POSTGRES_USER: infrabrain
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U infrabrain"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    build: .
    restart: unless-stopped
    depends_on:
      infrabrain-db:
        condition: service_healthy
    environment:
      POSTGRES_HOST: infrabrain-db
      POSTGRES_PORT: 5432
      POSTGRES_DB: infrabrain
      POSTGRES_USER: infrabrain
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      PORT: 80
      APP_NAME: infra-brain
      APP_ENV: ${APP_ENV:-development}
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:80/api/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - default
      - coolify

networks:
  default:
  coolify:
    external: true

volumes:
  postgres_data:
```

## docker-compose.local.yml (local dev port exposure)

```yaml
services:
  api:
    ports:
      - "8000:80"
```

Local start: `docker compose -f docker-compose.yml -f docker-compose.local.yml up --build`

---

## GitHub Actions Workflow (legacy / optional)

The repo currently contains `.github/workflows/deploy.yml` which builds and pushes a GHCR
image and then triggers a Coolify webhook. That workflow is no longer the primary production
path. The live deployment uses:

- Coolify `Private Repository (GitHub App)`
- `Docker Compose` build pack
- Compose location `docker-compose.yml`

Keep the workflow only if you want an alternate image-based deploy path for future use.
