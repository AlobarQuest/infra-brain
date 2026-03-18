from typing import Optional

from fastmcp import FastMCP

from src.db.engine import async_session_factory
from src.repositories.lessons import LessonRepository


def register_lesson_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def search_lessons(
        query: str,
        app: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> list[dict]:
        """Full-text search across lesson titles and content. Always call before working on a known-problematic area."""
        async with async_session_factory() as session:
            repo = LessonRepository(session)
            lessons = await repo.search(query=query, app=app, tags=tags)
            return [
                {
                    "id": l.id,
                    "app": l.app,
                    "title": l.title,
                    "content": l.content,
                    "tags": l.tags or [],
                    "severity": l.severity,
                    "source": l.source,
                }
                for l in lessons
            ]

    @mcp.tool()
    async def add_lesson(
        title: str,
        content: str,
        app: Optional[str] = None,
        tags: Optional[list[str]] = None,
        severity: str = "INFO",
    ) -> dict:
        """Add a new lesson to the registry. severity: CRITICAL, WARN, or INFO."""
        if severity not in ("CRITICAL", "WARN", "INFO"):
            return {"error": "invalid_severity", "allowed": ["CRITICAL", "WARN", "INFO"]}
        async with async_session_factory() as session:
            repo = LessonRepository(session)
            l = await repo.add({
                "title": title,
                "content": content,
                "app": app,
                "tags": tags or [],
                "severity": severity,
            })
            await session.commit()
            return {"created": True, "id": l.id, "title": l.title}
