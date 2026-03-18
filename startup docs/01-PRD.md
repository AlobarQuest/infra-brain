# Infra Brain — Product Requirements Document

**Project:** `infra-brain`
**Owner:** Devon Watkins
**Status:** Pre-build
**Flavor:** B (Standard — FastAPI + Postgres + GHCR + Coolify)
**Domain:** `infra-brain.devonwatkins.com`

---

## Problem Statement

Devon operates a growing portfolio of applications on a Hetzner VPS managed by Coolify.
Each time a new app is built or an existing app is modified, AI coding agents (Claude Code,
ADAS, CoWork) must rediscover the same infrastructure facts from scratch:

- Which Python version is canonical?
- What SQLAlchemy version is validated and safe?
- What Dockerfile pattern applies to this type of app?
- What rules must never be violated?
- What lessons were learned from past production incidents?

This rediscovery is slow, error-prone, and causes inconsistency across the portfolio. Agents
pin wrong versions, make deployment mistakes that have already been solved, and produce
artifacts that don't match the established patterns.

---

## Solution

Infra Brain is a **purpose-built infrastructure knowledge registry** exposed as an MCP server.
It stores structured, queryable facts about Devon's infrastructure standards and serves them
to any AI agent or human that needs them.

It is not a general document store. It is a typed registry with four specific tables:
versions, rules, combos, and lessons. Each table has a schema that enforces the right
structure for that type of knowledge.

---

## Users

| User | How they interact | What they need |
|---|---|---|
| AI coding agent (Claude Code, ADAS, CoWork) | MCP tool calls | Exact version pins, applicable rules, relevant lessons before starting work |
| Claude.ai chat (this interface) | MCP tool calls | Same as above, plus ability to add new lessons and update versions |
| Devon (human) | MCP tool calls via chat, or direct psql | Browse and update the registry as standards evolve |

---

## Core Use Cases

### UC-1: Version lookup
An agent is about to write a `requirements.txt`. Before pinning any version, it calls
`get_version("sqlalchemy")` and receives the canonical version, the minimum allowed,
the blocked-above boundary, and the reason. It pins exactly what Infra Brain says.

### UC-2: Rule check
An agent is about to write a Coolify config for a Next.js app. It calls
`get_rules(category="deployment")` and receives all deployment rules including
"Never source-build Next.js on VPS — BLOCK severity." It knows not to configure
a source build.

### UC-3: Combo lookup
An agent is scaffolding a new Python/FastAPI app. It calls
`get_combo("python-fastapi-stack")` and receives the full validated dependency set
with exact version pins for the entire stack at once.

### UC-4: Lesson retrieval
An agent is working on Booking Assistant's Google OAuth flow. It calls
`search_lessons("google oauth")` and receives the lesson about PKCE code verifier
persistence and the requirement for exact redirect URI matching. It avoids
re-discovering a bug that already hit production.

### UC-5: Write-back
An agent finishes validating that `sqlalchemy==2.0.37` works correctly and is safe.
It calls `update_version("sqlalchemy", canonical="2.0.37")`. The registry is updated.
Every subsequent agent gets the new pin without any human intervention.

### UC-6: New lesson capture
Devon or an agent discovers that a certain Coolify health check configuration causes
false failures. It calls `add_lesson(app="contacts", content="...")`. The lesson is
permanently stored and retrievable by future agents working on any app.

---

## Non-Goals

- **Not a general document store.** Long-form architecture docs belong in App Brain.
- **Not a deployment executor.** Infra Brain tells agents what to do; it does not do it for them.
  Execution belongs in a future Infra MCP audit/generate layer.
- **Not a human-facing web UI.** A table editor UI is a low-priority future enhancement.
  The primary interface is MCP tools.
- **Not a secrets manager.** Secrets stay in BWS. Infra Brain stores patterns, not values.

---

## Success Criteria

1. An agent asked "what SQLAlchemy version should I use?" gets the correct answer in
   one tool call without searching, guessing, or asking Devon.
2. An agent scaffolding a new app never picks a version that violates a BLOCK rule.
3. A lesson learned in one project is automatically available to agents in all other projects.
4. Adding a new app to the portfolio does not require updating any code — only adding
   knowledge to Infra Brain.
5. The registry can be updated (new version, new rule, new lesson) in a single MCP tool
   call with no deployment required.

---

## Constraints

- Must follow Flavor B infrastructure standards (the same standards it documents).
- Zero incremental hosting cost — runs on existing Hetzner VPS.
- All secrets via BWS. No secrets in git.
- Must be reachable as a connected MCP from Claude.ai and from Claude Code `.mcp.json`.
