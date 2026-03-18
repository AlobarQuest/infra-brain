from typing import Optional

from fastmcp import FastMCP

from src.db.engine import async_session_factory
from src.repositories.rules import RuleRepository


def register_rule_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_rules(
        category: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> list[dict]:
        """Get rules, optionally filtered by category and/or severity. Always check severity='BLOCK' before deployment tasks."""
        async with async_session_factory() as session:
            repo = RuleRepository(session)
            rules = await repo.list_all(category=category, severity=severity)
            return [
                {
                    "id": r.id,
                    "severity": r.severity,
                    "category": r.category,
                    "rule": r.rule,
                    "reason": r.reason,
                    "source_app": r.source_app,
                }
                for r in rules
            ]

    @mcp.tool()
    async def add_rule(
        severity: str,
        category: str,
        rule: str,
        reason: str,
        source_app: Optional[str] = None,
    ) -> dict:
        """Add a new rule. severity must be BLOCK, WARN, or INFO."""
        if severity not in ("BLOCK", "WARN", "INFO"):
            return {"error": "invalid_severity", "allowed": ["BLOCK", "WARN", "INFO"]}
        async with async_session_factory() as session:
            repo = RuleRepository(session)
            r = await repo.add({
                "severity": severity,
                "category": category,
                "rule": rule,
                "reason": reason,
                "source_app": source_app,
            })
            await session.commit()
            return {"created": True, "id": r.id, "severity": r.severity, "category": r.category}
