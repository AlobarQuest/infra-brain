from contextlib import asynccontextmanager

import sqlalchemy
from fastapi import FastAPI
from fastmcp import FastMCP

from src.db.engine import async_session_factory, engine
from src.tools.combos import register_combo_tools
from src.tools.lessons import register_lesson_tools
from src.tools.rules import register_rule_tools
from src.tools.versions import register_version_tools


# Use stateless streamable HTTP with JSON responses, which is the recommended
# deployment shape for remote/proxied MCP servers.
mcp = FastMCP("infra-brain", json_response=True, stateless_http=True)

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

MCP_HTTP_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]


class MCPPrefixAlias:
    """Serve `/mcp` with the same mounted app behavior as `/mcp/`."""

    def __init__(self, app, mount_path: str):
        self.app = app
        self.mount_path = mount_path.rstrip("/")

    async def __call__(self, scope, receive, send) -> None:
        alias_scope = dict(scope)
        alias_scope["app_root_path"] = alias_scope.get(
            "app_root_path", alias_scope.get("root_path", "")
        )
        alias_scope["root_path"] = f"{alias_scope.get('root_path', '')}{self.mount_path}"
        alias_scope["path"] = f"{scope['path'].rstrip('/')}/"

        raw_path = scope.get("raw_path")
        if raw_path is not None:
            alias_scope["raw_path"] = raw_path.rstrip(b"/") + b"/"

        await self.app(alias_scope, receive, send)


app.add_route(
    "/mcp",
    MCPPrefixAlias(mcp_asgi_app, "/mcp"),
    methods=MCP_HTTP_METHODS,
    include_in_schema=False,
)


@app.get("/api/health")
async def health():
    async with async_session_factory() as session:
        try:
            await session.execute(sqlalchemy.text("SELECT 1"))
            db_status = "connected"
        except Exception:
            db_status = "error"
    return {"status": "ok", "app": "infra-brain", "db": db_status}
