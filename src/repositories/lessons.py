from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Lesson


class LessonRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def search(
        self,
        query: str,
        app: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> list[Lesson]:
        stmt = select(Lesson).where(
            or_(
                Lesson.title.ilike(f"%{query}%"),
                Lesson.content.ilike(f"%{query}%"),
            )
        )
        if app:
            stmt = stmt.where(Lesson.app == app)
        if tags:
            for tag in tags:
                stmt = stmt.where(Lesson.tags.any(tag))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def add(self, data: dict) -> Lesson:
        lesson = Lesson(**data)
        self.session.add(lesson)
        await self.session.flush()
        return lesson

    async def add_if_not_exists(self, data: dict) -> None:
        """Insert lesson, silently skip if the title already exists (race-safe)."""
        stmt = (
            insert(Lesson)
            .values(**data)
            .on_conflict_do_nothing(index_elements=["title"])
        )
        await self.session.execute(stmt)
