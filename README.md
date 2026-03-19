# Infra Brain

Infrastructure knowledge registry for Devon's app portfolio. Exposed as an MCP server.

**MCP endpoint:** `https://infra-brain.devonwatkins.com/mcp`
**Health:** `https://infra-brain.devonwatkins.com/api/health`

## What it stores

| Table | Contents |
|---|---|
| `versions` | Canonical pinned versions for every package in the portfolio |
| `rules` | Hard constraints (BLOCK) and warnings (WARN/INFO) AI agents must follow |
| `combos` | Validated full-stack dependency sets |
| `lessons` | Production discoveries and incident post-mortems |

## MCP Tools

| Tool | Purpose |
|---|---|
| `get_version(package)` | Get canonical version for a package |
| `list_versions(ecosystem?)` | List all versions, filtered by ecosystem |
| `update_version(package, canonical, ...)` | Update an existing package version |
| `add_version(package, canonical, ...)` | Add a new package |
| `get_rules(category?, severity?)` | Get rules — always check `severity="BLOCK"` first |
| `add_rule(severity, category, rule, reason)` | Add a new rule |
| `get_combo(name)` | Get a validated full-stack dependency set |
| `list_combos(ecosystem?, flavor?)` | List all combos |
| `search_lessons(query, app?, tags?)` | Full-text search lessons |
| `add_lesson(title, content, ...)` | Record a new lesson |

## Local development

```bash
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD

docker compose -f docker-compose.yml -f docker-compose.local.yml up --build

curl http://localhost:8000/api/health
# → {"status": "ok", "app": "infra-brain", "db": "connected"}
```

## Coolify deployment

Deploy this repo in Coolify as a `Docker Compose` application using `docker-compose.yml`.

Required Coolify environment variables:

```env
POSTGRES_PASSWORD=<strong password for the inline postgres service>
APP_ENV=production
LOG_LEVEL=INFO
```

The API service derives `DATABASE_URL` internally from `POSTGRES_PASSWORD`. If you change the Postgres password after first boot, you must either update the role password inside Postgres or recreate the Postgres volume.

## MCP connectivity test

```bash
npx @modelcontextprotocol/inspector http://localhost:8000/mcp
```

## Connect to Claude Code

Add to `~/.mcp.json`:

```json
{
  "mcpServers": {
    "infra-brain": {
      "url": "https://infra-brain.devonwatkins.com/mcp"
    }
  }
}
```

## Stack

- **FastAPI** 0.115.6 + **FastMCP** 2.3.4
- **PostgreSQL** 16 + **SQLAlchemy** 2.0.36 (async) + **Alembic** 1.13.3
- **Docker Compose** → **Coolify**
