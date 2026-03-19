# Infra Brain — Coolify Deploy Checklist

Use this checklist for the current deployment shape: one Coolify `Docker Compose` application with two services defined in `docker-compose.yml`.

---

## Step 1 — Delete the Broken Install

1. In Coolify, delete the existing `infra-brain` application.
2. Delete the attached Postgres volume created by the old install if you do not need the data.
3. Confirm the old volume is gone before redeploying.

Current inline volume name in this repo: `postgres_data`.

Important:
- If you keep the old volume, Postgres keeps the old role password.
- Changing `POSTGRES_PASSWORD` in Coolify does not rewrite an already-initialized database.

---

## Step 2 — Create a New Docker Compose Application

1. In Coolify, create a new `Docker Compose` application from this repo.
2. Point Coolify at `docker-compose.yml`.
3. Use the repository root as the build context.

This app contains:
- `infrabrain-db`: PostgreSQL 16
- `api`: FastAPI + FastMCP application

---

## Step 3 — Set Environment Variables

Set these in the Coolify application environment:

```env
POSTGRES_PASSWORD=<strong password>
APP_ENV=production
LOG_LEVEL=INFO
```

Notes:
- Do not set `DATABASE_URL` in Coolify for the normal inline-compose install.
- The API service builds `DATABASE_URL` as `postgresql+asyncpg://infrabrain:${POSTGRES_PASSWORD}@infrabrain-db:5432/infrabrain`.
- `SERVICE_URL_API` and `SERVICE_FQDN_API` are not required by this app.

---

## Step 4 — Domain and Port

Configure the public service as:

- Service: `api`
- Port: `8000`
- Domain: `infra-brain.devonwatkins.com`
- Health check path: `/api/health`

The container also includes an internal healthcheck that probes `http://127.0.0.1:8000/api/health`.

---

## Step 5 — First Deploy

Deploy and watch for this startup sequence:

1. Postgres starts and becomes healthy.
2. API runs `alembic upgrade head`.
3. API runs `python scripts/seed.py --skip-existing`.
4. API starts `uvicorn` on port `8000`.

If `alembic` fails with `InvalidPasswordError`, either:
- the Postgres volume was reused from an older install, or
- the `POSTGRES_PASSWORD` value in Coolify does not match the password stored for role `infrabrain`.

---

## Step 6 — Verify

```bash
curl https://infra-brain.devonwatkins.com/api/health
curl https://infra-brain.devonwatkins.com/mcp
```

Expected health response:

```json
{"status":"ok","app":"infra-brain","db":"connected"}
```

---

## Step 7 — Ongoing Maintenance

- If you need to rotate the DB password later, rotate it in both places:
  - Coolify env `POSTGRES_PASSWORD`
  - Postgres role `infrabrain`
- If the database is disposable, the simpler path is to delete the Postgres volume and redeploy.
