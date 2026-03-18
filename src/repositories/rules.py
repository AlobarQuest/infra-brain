from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Rule


class RuleRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(
        self,
        category: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> list[Rule]:
        stmt = select(Rule)
        if category:
            stmt = stmt.where(Rule.category == category)
        if severity:
            stmt = stmt.where(Rule.severity == severity)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def add(self, data: dict) -> Rule:
        rule = Rule(**data)
        self.session.add(rule)
        await self.session.flush()
        return rule

    async def add_if_not_exists(self, data: dict) -> None:
        """Insert rule, silently skip if the rule text already exists (race-safe)."""
        stmt = (
            insert(Rule)
            .values(**data)
            .on_conflict_do_nothing(index_elements=["rule"])
        )
        await self.session.execute(stmt)
