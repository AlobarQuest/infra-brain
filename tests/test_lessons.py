import pytest

from src.repositories.lessons import LessonRepository


@pytest.fixture
async def seeded_lessons(session):
    repo = LessonRepository(session)
    await repo.add({
        "title": "Google OAuth PKCE verifier must persist across redirect",
        "content": "FastAPI OAuth flow requires the PKCE code_verifier to persist. Store in session at authorize step, retrieve at callback.",
        "app": "booking-assistant",
        "tags": ["google", "oauth", "pkce", "fastapi"],
        "severity": "WARN",
        "source": "production-incident",
    })
    await repo.add({
        "title": "Next.js source builds stall VPS deploys",
        "content": "npm build on VPS causes CPU spikes. Always pre-build via GitHub Actions and push to GHCR.",
        "app": "lifeops-portal",
        "tags": ["nextjs", "coolify", "deployment", "cpu"],
        "severity": "CRITICAL",
        "source": "production-incident",
    })
    await session.commit()


async def test_search_lessons_by_keyword(session, seeded_lessons):
    repo = LessonRepository(session)
    results = await repo.search(query="oauth")
    assert len(results) >= 1
    assert any("OAuth" in r.title or "oauth" in r.title.lower() for r in results)


async def test_search_lessons_by_app(session, seeded_lessons):
    repo = LessonRepository(session)
    results = await repo.search(query="oauth", app="booking-assistant")
    assert len(results) >= 1
    assert all(r.app == "booking-assistant" for r in results)


async def test_add_lesson_persists_and_is_searchable(session):
    repo = LessonRepository(session)
    l = await repo.add({
        "title": "Health check endpoint must be exempt from Basic Auth",
        "content": "Coolify health probes do not send credentials. Exempt /api/health.",
        "app": "contacts",
        "tags": ["coolify", "health-check", "basic-auth"],
        "severity": "WARN",
        "source": "production-incident",
    })
    await session.commit()
    assert l.id is not None

    results = await repo.search(query="Basic Auth")
    assert any(r.id == l.id for r in results)
