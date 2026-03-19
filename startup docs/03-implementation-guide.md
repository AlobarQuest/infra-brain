# Infra Brain — Implementation Guide

This document tells a coding AI (Claude Code, ADAS, CoWork) exactly what to build
in each phase. Each phase is independently deployable and delivers immediate value.

**Before starting any phase:** Read `01-PRD.md` and `02-technical-architecture.md` first.
Read the `infra-standards` skill at `/mnt/skills/user/infra-standards/SKILL.md`.

---

## Phase 1 — Core Registry (Build this first)

**Deliverable:** A running FastAPI + FastMCP server backed by Postgres with all four
tables, seeded with initial data, and the full MCP tool set working.

**Test:** `get_version("sqlalchemy")` returns `{"canonical": "2.0.36", ...}` and
`get_rules(severity="BLOCK")` returns the list of blocking rules.

### Step 1.1 — Project scaffold

Create the directory structure exactly as shown in `02-technical-architecture.md`.
Initialize git. Create `.gitignore` (exclude `.env`, `__pycache__`, `.venv`).

### Step 1.2 — Dependencies

Write `requirements.txt` with these exact versions (canonical per Infra Brain seed data):
```
fastapi==0.115.6
uvicorn[standard]==0.32.1
fastmcp==2.3.4
sqlalchemy==2.0.36
alembic==1.13.3
asyncpg==0.29.0
pydantic==2.10.3
pydantic-settings==2.7.0
python-dotenv==1.0.1
httpx==0.28.1
pytest==7.4.4
pytest-asyncio==0.23.8
```

### Step 1.3 — Configuration

`src/config.py` — use `pydantic-settings` BaseSettings:
```python
class Settings(BaseSettings):
    database_url: str
    app_name: str = "infra-brain"
    app_env: str = "development"
    log_level: str = "INFO"
    port: int = 8000

    model_config = ConfigDict(env_file=".env")
```

Local development uses `localhost:8000`. The deployed container overrides `PORT=80`
through `docker-compose.yml`.

### Step 1.4 — Database engine

`src/db/engine.py` — async SQLAlchemy engine:
- Use `create_async_engine` with `asyncpg` driver
- `DATABASE_URL` format: `postgresql+asyncpg://user:pass@host:5432/dbname`
- Session factory: `async_sessionmaker` with `expire_on_commit=False`
- Expose `get_session` as an async context manager for dependency injection

### Step 1.5 — ORM Models

`src/db/models.py` — implement all four models exactly matching the schema in
`02-technical-architecture.md`:
- `Version` — with `ARRAY(Text)` for `confirmed_in`
- `Rule` — with `CheckConstraint` on severity values
- `Combo` — with `JSON` type for `packages`
- `Lesson` — with `ARRAY(Text)` for `tags`

Use `mapped_column` and `Mapped` (SQLAlchemy 2.0 style, not legacy Column).
All timestamps use `func.now()` server defaults.

### Step 1.6 — Alembic setup

Run `alembic init alembic` then configure `alembic/env.py`:
- Import models and set `target_metadata = Base.metadata`
- Use async engine pattern for autogenerate
- Set `sqlalchemy.url` to read from environment

Generate initial migration: `alembic revision --autogenerate -m "initial_schema"`
Review the generated file — ensure all four tables, constraints, and defaults are present.

### Step 1.7 — Repositories

One file per table in `src/repositories/`. Each repository:
- Takes an `AsyncSession` as constructor argument
- Implements the operations needed by the MCP tools
- Never contains business logic — pure data access

`versions.py`:
- `get_by_package(package: str) -> Version | None`
- `list_all(ecosystem: str | None) -> list[Version]`
- `upsert(data: dict) -> Version`

`rules.py`:
- `list_all(category: str | None, severity: str | None) -> list[Rule]`
- `add(data: dict) -> Rule`

`combos.py`:
- `get_by_name(name: str) -> Combo | None`
- `list_all(ecosystem: str | None, flavor: str | None) -> list[Combo]`

`lessons.py`:
- `search(query: str, app: str | None, tags: list[str] | None) -> list[Lesson]`
  Use PostgreSQL `ILIKE` for content search across title and content fields.
- `add(data: dict) -> Lesson`

### Step 1.8 — MCP Tools

`src/tools/versions.py` — implement:
- `get_version(package: str)` → calls `versions_repo.get_by_package`
- `list_versions(ecosystem: str | None = None)` → calls `versions_repo.list_all`
- `update_version(package, canonical, reason, confirmed_in)` → calls `versions_repo.upsert`
- `add_version(package, canonical, ecosystem, reason, min_allowed, blocked_above, confirmed_in)` → calls `versions_repo.upsert`

`src/tools/rules.py` — implement:
- `get_rules(category: str | None = None, severity: str | None = None)`
- `add_rule(severity, category, rule, reason, source_app)`

`src/tools/combos.py` — implement:
- `get_combo(name: str)`
- `list_combos(ecosystem: str | None = None, flavor: str | None = None)`

`src/tools/lessons.py` — implement:
- `search_lessons(query: str, app: str | None = None, tags: list[str] | None = None)`
- `add_lesson(title, content, app, tags, severity)`

All tools must return clean Python dicts (not ORM objects). FastMCP serializes
dicts to JSON automatically. Include an `error` key in the return dict when something
goes wrong — never raise unhandled exceptions in tool handlers.

### Step 1.9 — Main app

`src/main.py`:
```python
from fastapi import FastAPI
from fastmcp import FastMCP

app = FastAPI(title="Infra Brain")
mcp = FastMCP("infra-brain")

# Register all tools from tools/ modules
# Mount MCP on FastAPI: app.mount("/mcp", mcp.get_asgi_app())

@app.get("/api/health")
async def health():
    # Check DB connectivity here too
    return {"status": "ok", "app": "infra-brain"}
```

Mount pattern: FastMCP's ASGI app mounts at `/mcp`. The FastAPI app serves `/api/*`.
Local development is exposed at `localhost:8000` via compose port mapping, while the
deployed container listens on port `80`.

### Step 1.10 — Seed script

`scripts/seed.py`:
- Reads `seed/data.json`
- For each record, calls `upsert` (versions) or `add if not exists` (rules, combos, lessons)
- `--skip-existing` flag: if record already exists, skip it (do not overwrite)
- `--force` flag: overwrite everything (for resetting to baseline)
- Idempotent by default — safe to run on every container startup

`seed/data.json` — see `04-seed-data.json` for the full initial dataset.

### Step 1.11 — Tests

`tests/test_versions.py`:
- Test `get_version` returns correct data for a seeded package
- Test `get_version` returns `{"error": "not_found"}` for unknown package
- Test `update_version` changes the canonical field

`tests/test_rules.py`:
- Test `get_rules(severity="BLOCK")` returns only BLOCK rules
- Test `add_rule` persists correctly

`tests/test_lessons.py`:
- Test `search_lessons("oauth")` returns the Google OAuth lesson
- Test `add_lesson` persists and is searchable

Use pytest-asyncio. Tests use a separate test database (set via `DATABASE_URL` env var).

### Step 1.12 — Dockerfile and compose

Write `Dockerfile`, `docker-compose.yml`, `docker-compose.local.yml`, and `.env.example`
exactly as shown in `02-technical-architecture.md`.

**Local dev test:**
```bash
cp .env.example .env
# edit .env: set POSTGRES_PASSWORD
docker compose -f docker-compose.yml -f docker-compose.local.yml up --build
curl http://localhost:8000/api/health
# Should return {"status": "ok", "app": "infra-brain"}
```

**MCP connectivity test:**
```bash
# Local inspector
npx @modelcontextprotocol/inspector http://localhost:8000/mcp

# Remote SSE probe
curl -i -N -H 'Accept: text/event-stream' \
  https://infra-brain.devonwatkins.com/mcp
```

Do not expect a plain `curl https://.../mcp` request to return JSON. FastMCP requires
`Accept: text/event-stream`.

**Phase 1 complete when:**
- [ ] `docker compose up` starts cleanly
- [ ] `/api/health` returns 200
- [ ] All seed data loaded
- [ ] All MCP tools respond correctly in MCP inspector
- [ ] All tests pass

---

## Phase 2 — CI/CD and Deployment

**Deliverable:** The app is deployed on the VPS, reachable at
`https://infra-brain.devonwatkins.com/mcp`, and connected to Claude.ai as an MCP server.

### Step 2.1 — GitHub repo

Create `github.com/alobarquest/infra-brain`. Push Phase 1 code.

### Step 2.2 — Coolify source path

Current production deployment uses Coolify directly from GitHub:

- Source type: `Private Repository (GitHub App)`
- Build pack: `Docker Compose`
- Compose location: `docker-compose.yml`

The checked-in `.github/workflows/deploy.yml` is now optional/legacy. It is not required
for the live deployment path.

### Step 2.3 — Coolify setup

In Coolify UI:

1. **Create application resource**
   - Type: `Private Repository (GitHub App)`
   - Repository: `github.com/alobarquest/infra-brain`
   - Build pack: `Docker Compose`
   - Compose location: `docker-compose.yml`

2. **Set environment variables**:
   ```
   POSTGRES_PASSWORD=<strong password>
   APP_ENV=production
   LOG_LEVEL=INFO
   ```

3. **Configure the public service**
   - Service: `api`
   - Container port: `80`
   - Domain: `https://infra-brain.devonwatkins.com`
   - Health check path: `/api/health`

4. **Deploy and verify**
   - Trigger manual deploy
   - Check logs — look for `alembic upgrade head`, seed completion, and `Uvicorn running on http://0.0.0.0:80`
   - Hit `https://infra-brain.devonwatkins.com/api/health`
   - Validate MCP with an SSE-capable client or `Accept: text/event-stream`

### Step 2.4 — Connect to Claude.ai

In Claude.ai Settings → Connected Apps → Add MCP Server:
- Name: `Infra Brain`
- URL: `https://infra-brain.devonwatkins.com/mcp`

Verify in a new conversation: ask "what version of sqlalchemy should I use?" —
Claude should call `get_version("sqlalchemy")` and return the registered answer.

### Step 2.5 — Connect to Claude Code

Add to `~/.mcp.json` (global) or project-level `.mcp.json`:
```json
{
  "mcpServers": {
    "infra-brain": {
      "url": "https://infra-brain.devonwatkins.com/mcp"
    }
  }
}
```

### Step 2.6 — Backup

The current live deployment uses inline Postgres inside the compose stack, so there is
no separate Coolify database resource to attach scheduled DB backups to.

Current recommendation:
- use server-level backups for the Docker volume, or
- add a future `pg_dump` automation once backup requirements are finalized

**Phase 2 complete when:**
- [ ] Coolify deploys from the GitHub App source cleanly
- [ ] `https://infra-brain.devonwatkins.com/api/health` returns 200
- [ ] Claude.ai can call `get_version("sqlalchemy")` via MCP
- [ ] MCP endpoint responds to an SSE-capable client

---

## Phase 3 — Register in App Brain

**Deliverable:** Infra Brain is registered in App Brain so any AI arriving in a
conversation can know Infra Brain exists and how to use it.

```python
# Call App Brain MCP:
onboard_app(
    slug="infra-brain",
    name="Infra Brain",
    description="...",  # from PRD
    deployment_url="https://infra-brain.devonwatkins.com",
    repo_path="github.com/alobarquest/infra-brain",
    tags=["mcp", "infrastructure", "versions", "rules", "knowledge-management"],
    tech_stack={"backend": "FastAPI", "db": "PostgreSQL 16", "mcp": "FastMCP"},
    deployment_notes="MCP endpoint: https://infra-brain.devonwatkins.com/mcp. Add to .mcp.json or Claude.ai connected apps.",
    replace_existing=True
)
```

Also update the `infra-standards` SKILL.md to add:

```markdown
## Version Lookups

Before pinning ANY dependency version, query Infra Brain first:
- MCP tool: `get_version("package-name")`
- MCP tool: `get_combo("python-fastapi-stack")` for the full validated Python stack
- MCP tool: `get_rules(severity="BLOCK")` before any deployment work

Infra Brain MCP: https://infra-brain.devonwatkins.com/mcp
```

---

## Future Phases (not in scope for initial build)

**Phase 4 — Audit tools**
Add tools that query the Coolify API and GitHub API to check live compliance.
`audit_app(slug)` → checks actual deployment against Infra Brain standards.

**Phase 5 — Generate tools**
Add tools that produce deployment artifacts (Dockerfiles, GitHub Actions workflows,
Coolify checklists) pre-filled with Infra Brain's canonical values.

**Phase 6 — Admin UI**
Minimal web interface for browsing and editing the registry without psql.
Low priority — MCP tools and direct DB access cover all current needs.
