# Infra Brain — Coolify Deploy Checklist

Work through this after Phase 1 local dev is verified and the GitHub repo is pushed.

---

## Pre-requisites

- [ ] Phase 1 complete: `docker compose up` works locally, all MCP tools respond, seed loaded
- [ ] GitHub repo `github.com/alobarquest/infra-brain` created and code pushed to `main`
- [ ] GitHub Actions ran and pushed image to `ghcr.io/alobarquest/infra-brain:latest`
- [ ] GHCR package is visible at `https://github.com/alobarquest?tab=packages`

---

## Step 1 — Create the Postgres Database Resource in Coolify

1. In Coolify → New Resource → Database → PostgreSQL
2. Set:
   - **Name:** `infra-brain-db`
   - **Version:** 16
   - **Database name:** `infrabrain`
   - **Username:** `infrabrain`
   - **Password:** generate strong password (save it — goes into BWS next)
3. Deploy the database resource
4. Note the **internal host** Coolify assigns (format: `postgresql-XXXX` or similar)
5. Verify connectivity from the Coolify UI database panel

---

## Step 2 — Add Secrets to BWS

In Bitwarden Secrets Manager, add to the `infra-brain` project/collection:

```
INFRA_BRAIN_DATABASE_URL = postgresql+asyncpg://infrabrain:PASSWORD@INTERNAL_HOST:5432/infrabrain
INFRA_BRAIN_APP_NAME     = infra-brain
INFRA_BRAIN_APP_ENV      = production
INFRA_BRAIN_LOG_LEVEL    = INFO
```

Replace `PASSWORD` with the password from Step 1.
Replace `INTERNAL_HOST` with the Coolify internal host from Step 1.

---

## Step 3 — Configure GHCR Registry in Coolify

If not already done:
1. Coolify → Settings → Registries → Add Registry
2. Type: GitHub Container Registry (GHCR)
3. Username: `alobarquest`
4. Token: GitHub PAT with `read:packages` scope
5. Save and verify

---

## Step 4 — Create the Application Resource in Coolify

1. Coolify → New Resource → Application → Docker Image
2. Set:
   - **Name:** `infra-brain`
   - **Image:** `ghcr.io/alobarquest/infra-brain:latest`
   - **Registry:** select the GHCR registry configured in Step 3
   - **Port:** `8000`
   - **Domain:** `infra-brain.devonwatkins.com`
   - **Health check path:** `/api/health`
   - **Health check host:** `127.0.0.1`
   - **Health check port:** `8000`

3. Set environment variables (pull from BWS):
   ```
   DATABASE_URL   = <value of INFRA_BRAIN_DATABASE_URL from BWS>
   APP_NAME       = infra-brain
   APP_ENV        = production
   LOG_LEVEL      = INFO
   ```

4. Save configuration (do not deploy yet)

---

## Step 5 — Add GitHub Actions Secrets

In the GitHub repo (`github.com/alobarquest/infra-brain`) → Settings → Secrets → Actions:

```
COOLIFY_WEBHOOK_URL  = <webhook URL from Coolify app resource → Webhooks tab>
COOLIFY_API_TOKEN    = <Coolify API token from Coolify → Settings → API>
```

---

## Step 6 — First Deploy

1. In Coolify, trigger a manual deploy of `infra-brain`
2. Watch the deploy logs:
   - Container starts
   - `alembic upgrade head` runs and creates tables
   - `python scripts/seed.py --skip-existing` runs and loads data
   - `uvicorn` starts and binds to port 8000
3. Coolify health check should turn green

---

## Step 7 — Verify

```bash
# Health check
curl https://infra-brain.devonwatkins.com/api/health
# Expected: {"status": "ok", "app": "infra-brain"}

# Test MCP endpoint (list tools)
curl https://infra-brain.devonwatkins.com/mcp
# Expected: MCP tool manifest JSON

# Test version lookup via HTTP
curl https://infra-brain.devonwatkins.com/api/versions/sqlalchemy
# Expected: {"package": "sqlalchemy", "canonical": "2.0.36", ...}
```

---

## Step 8 — Configure Backup

1. In Coolify, select the `infra-brain-db` Postgres resource
2. Enable scheduled backup:
   - **Target:** S3 Compatible
   - **Endpoint:** `https://fsn1.your-objectstorage.com` (update to actual Hetzner endpoint)
   - **Bucket:** `devon-backups`
   - **Path prefix:** `postgres/infra-brain/`
   - **Access Key:** `HETZNER_S3_KEY` (from BWS shared secrets)
   - **Secret Key:** `HETZNER_S3_SECRET` (from BWS shared secrets)
   - **Schedule:** `0 2 * * *` (2 AM nightly)
3. Trigger a manual backup and verify the file appears in Hetzner Object Storage

---

## Step 9 — Connect to Claude.ai

1. Claude.ai → Settings → Connected Apps → Add MCP Server
2. Name: `Infra Brain`
3. URL: `https://infra-brain.devonwatkins.com/mcp`
4. Save

**Verify:** Open a new Claude.ai conversation and ask:
> "What version of SQLAlchemy should I use in my Python projects?"

Claude should call `get_version("sqlalchemy")` and return `2.0.36` with the reason.

---

## Step 10 — Connect to Claude Code

Add to `~/.mcp.json` on your development machine:

```json
{
  "mcpServers": {
    "infra-brain": {
      "url": "https://infra-brain.devonwatkins.com/mcp",
      "description": "Devon's infrastructure knowledge registry — versions, rules, combos, lessons"
    }
  }
}
```

Or add to individual project `.mcp.json` files where infrastructure decisions are made.

---

## Step 11 — Register in App Brain

In a Claude.ai conversation with App Brain connected, run:

> "Register infra-brain in App Brain. It's a FastAPI + FastMCP + PostgreSQL 16 app
> deployed at https://infra-brain.devonwatkins.com. It's Devon's infrastructure
> knowledge registry storing canonical versions, rules, combos, and lessons.
> MCP endpoint is at /mcp. Repo is github.com/alobarquest/infra-brain. It's Flavor B."

---

## Deploy Complete ✓

At this point:
- Infra Brain is live and serving MCP tools
- Claude.ai and Claude Code can query it for version pins and rules
- Backups are configured
- Any push to `main` auto-deploys via GitHub Actions → GHCR → Coolify webhook

---

## Ongoing Maintenance

**To update a version pin:**
In any AI conversation with Infra Brain connected:
> "Update the SQLAlchemy version in Infra Brain to 2.0.37. It's been validated in contacts."

**To add a new lesson:**
> "Add a lesson to Infra Brain: [description of what you learned]"

**To add a new package:**
> "Add fastapi-users version 13.0.0 to Infra Brain's Python versions. It's been validated in [app]."

No code deploy needed for data updates — MCP write tools handle it live.
