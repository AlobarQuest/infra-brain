from contextlib import asynccontextmanager

import sqlalchemy
from fastapi import FastAPI
from fastmcp import FastMCP

from src.db.engine import async_session_factory, engine
from src.tools.combos import register_combo_tools
from src.tools.lessons import register_lesson_tools
from src.tools.rules import register_rule_tools
from src.tools.versions import register_version_tools


mcp = FastMCP("infra-brain")

register_version_tools(mcp)
register_rule_tools(mcp)
register_combo_tools(mcp)
register_lesson_tools(mcp)

# Build the MCP ASGI app once so we can wire its lifespan into FastAPI's
mcp_asgi_app = mcp.http_app(path="/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start FastMCP's session manager (it requires an active task group)
    async with mcp_asgi_app.router.lifespan_context(mcp_asgi_app):
        yield
    await engine.dispose()


app = FastAPI(title="Infra Brain", lifespan=lifespan)

app.mount("/mcp", mcp_asgi_app)


@app.get("/api/health")
async def health():
    async with async_session_factory() as session:
        try:
            await session.execute(sqlalchemy.text("SELECT 1"))
            db_status = "connected"
        except Exception:
            db_status = "error"
    return {"status": "ok", "app": "infra-brain", "db": db_status}
