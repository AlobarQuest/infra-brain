from typing import Optional

from fastmcp import FastMCP

from src.db.engine import async_session_factory
from src.repositories.combos import ComboRepository


def register_combo_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_combo(name: str) -> dict:
        """Get the full validated package set for a named stack combo."""
        async with async_session_factory() as session:
            repo = ComboRepository(session)
            c = await repo.get_by_name(name)
            if not c:
                return {"error": "not_found", "name": name}
            return {
                "name": c.name,
                "description": c.description,
                "ecosystem": c.ecosystem,
                "flavor": c.flavor,
                "packages": c.packages,
                "confirmed_in": c.confirmed_in or [],
            }

    @mcp.tool()
    async def list_combos(
        ecosystem: Optional[str] = None,
        flavor: Optional[str] = None,
    ) -> list[dict]:
        """List all stack combos, optionally filtered by ecosystem or flavor."""
        async with async_session_factory() as session:
            repo = ComboRepository(session)
            combos = await repo.list_all(ecosystem=ecosystem, flavor=flavor)
            return [
                {
                    "name": c.name,
                    "description": c.description,
                    "ecosystem": c.ecosystem,
                    "flavor": c.flavor,
                    "packages": c.packages,
                    "confirmed_in": c.confirmed_in or [],
                }
                for c in combos
            ]
