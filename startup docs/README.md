# Infra Brain — Project Specification

**Status:** Ready to build
**Flavor:** B (FastAPI + PostgreSQL 16 + GHCR + Coolify)
**Repo:** `github.com/alobarquest/infra-brain`
**Domain:** `infra-brain.devonwatkins.com`
**MCP endpoint:** `https://infra-brain.devonwatkins.com/mcp`

---

## What Is This?

Infra Brain is Devon's infrastructure knowledge registry. It is a Postgres-backed
MCP server that stores and serves:

- **Canonical software versions** — the exact pinned versions validated across the portfolio
- **Rules** — hard constraints (BLOCK) and warnings (WARN) that AI agents must follow
- **Combos** — validated full-stack dependency sets (e.g. the entire Python FastAPI stack at once)
- **Lessons** — production discoveries and incident post-mortems

Any AI agent (Claude Code, ADAS, CoWork, Claude.ai) queries Infra Brain before making
infrastructure decisions. It is the single source of truth that prevents version drift,
repeated mistakes, and inconsistent deployments.

---

## Documents In This Package

Read in order when handing to a coding AI:

| File | Contents |
|---|---|
| `01-PRD.md` | What it is, why it exists, use cases, success criteria |
| `02-technical-architecture.md` | Database schema, MCP tools, project structure, Dockerfile, CI |
| `03-implementation-guide.md` | Phase-by-phase build instructions for a coding AI |
| `04-seed-data.json` | Initial version pins, rules, combos, and lessons to load at first boot |
| `05-coolify-deploy-checklist.md` | Step-by-step Coolify configuration and verification |

---

## Build Instructions for Coding AI

1. Read all five documents in this package before writing any code
2. Also read `/mnt/skills/user/infra-standards/SKILL.md` — Infra Brain itself must follow
   the same infrastructure standards it documents
3. Build Phase 1 (core registry) first and verify locally before touching CI/CD
4. Follow the exact version pins in `04-seed-data.json` — those are the canonical versions
5. The seed script must be idempotent (`--skip-existing` by default)
6. All MCP tools return dicts with an `error` key on failure — never unhandled exceptions

---

## Key Design Decisions

**Why Postgres instead of a document store?**
Version records need structured fields (min_allowed, blocked_above) that a document store
can't enforce. Rules need severity-level filtering. Combos need JSON package maps.
Postgres gives us typed schemas with real constraints.

**Why FastMCP instead of raw MCP SDK?**
FastMCP mounts cleanly as an ASGI app on FastAPI. The health endpoint, REST API, and MCP
tools all run on the same port. Simpler operations, consistent with the portfolio direction.

**Why is seed data separate from migrations?**
Alembic manages schema (structure). Seed data is content — it changes independently and
must be updatable without a schema migration. The seed script loads `04-seed-data.json`
and is idempotent so it's safe to run on every container startup.

**Why not Supabase?**
Cost discipline (VPS already paid), data sovereignty, and dogfooding — Infra Brain
should follow the same Flavor B pattern it recommends for other apps.

---

## After Build

Once deployed, update these:
- `infra-standards` SKILL.md → add Infra Brain MCP URL and "query before pinning" instruction
- App Brain → register `infra-brain` app entry
- Claude.ai → add MCP server connection
- `~/.mcp.json` → add to Claude Code global config
