from typing import Optional

from fastmcp import FastMCP

from src.db.engine import async_session_factory
from src.repositories.versions import VersionRepository


def register_version_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_version(package: str) -> dict:
        """Get the canonical version record for a package."""
        async with async_session_factory() as session:
            repo = VersionRepository(session)
            v = await repo.get_by_package(package)
            if not v:
                return {"error": "not_found", "package": package}
            return {
                "package": v.package,
                "canonical": v.canonical,
                "min_allowed": v.min_allowed,
                "blocked_above": v.blocked_above,
                "reason": v.reason,
                "confirmed_in": v.confirmed_in or [],
                "ecosystem": v.ecosystem,
                "updated_at": v.updated_at.isoformat() if v.updated_at else None,
                "updated_by": v.updated_by,
            }

    @mcp.tool()
    async def list_versions(ecosystem: Optional[str] = None) -> list[dict]:
        """List all version records, optionally filtered by ecosystem."""
        async with async_session_factory() as session:
            repo = VersionRepository(session)
            versions = await repo.list_all(ecosystem=ecosystem)
            return [
                {
                    "package": v.package,
                    "canonical": v.canonical,
                    "min_allowed": v.min_allowed,
                    "blocked_above": v.blocked_above,
                    "reason": v.reason,
                    "confirmed_in": v.confirmed_in or [],
                    "ecosystem": v.ecosystem,
                }
                for v in versions
            ]

    @mcp.tool()
    async def update_version(
        package: str,
        canonical: str,
        reason: Optional[str] = None,
        confirmed_in: Optional[list[str]] = None,
    ) -> dict:
        """Update the canonical version for an existing package."""
        async with async_session_factory() as session:
            repo = VersionRepository(session)
            existing = await repo.get_by_package(package)
            if not existing:
                return {"error": "not_found", "package": package, "hint": "Use add_version to create new packages"}
            data: dict = {"package": package, "canonical": canonical}
            if reason is not None:
                data["reason"] = reason
            if confirmed_in is not None:
                data["confirmed_in"] = confirmed_in
            v = await repo.upsert(data)
            await session.commit()
            return {"updated": True, "package": v.package, "canonical": v.canonical}

    @mcp.tool()
    async def add_version(
        package: str,
        canonical: str,
        ecosystem: str,
        reason: str,
        min_allowed: Optional[str] = None,
        blocked_above: Optional[str] = None,
        confirmed_in: Optional[list[str]] = None,
    ) -> dict:
        """Add a new package to the version registry."""
        async with async_session_factory() as session:
            repo = VersionRepository(session)
            data = {
                "package": package,
                "canonical": canonical,
                "ecosystem": ecosystem,
                "reason": reason,
                "min_allowed": min_allowed,
                "blocked_above": blocked_above,
                "confirmed_in": confirmed_in or [],
            }
            v = await repo.upsert(data)
            await session.commit()
            return {"created": True, "package": v.package, "canonical": v.canonical}
