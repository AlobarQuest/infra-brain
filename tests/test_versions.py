import pytest

from src.repositories.versions import VersionRepository


@pytest.fixture
async def seeded_version(session):
    repo = VersionRepository(session)
    v = await repo.upsert({
        "package": "sqlalchemy",
        "canonical": "2.0.36",
        "min_allowed": "2.0.0",
        "blocked_above": "2.1.0",
        "reason": "async session breaking change in 2.1",
        "confirmed_in": ["contacts", "inbox-assistant"],
        "ecosystem": "python",
    })
    await session.commit()
    return v


async def test_get_version_returns_correct_data(session, seeded_version):
    repo = VersionRepository(session)
    v = await repo.get_by_package("sqlalchemy")
    assert v is not None
    assert v.canonical == "2.0.36"
    assert v.ecosystem == "python"
    assert "contacts" in v.confirmed_in


async def test_get_version_returns_none_for_unknown(session, seeded_version):
    repo = VersionRepository(session)
    v = await repo.get_by_package("nonexistent-package-xyz")
    assert v is None


async def test_update_version_changes_canonical(session, seeded_version):
    repo = VersionRepository(session)
    updated = await repo.upsert({
        "package": "sqlalchemy",
        "canonical": "2.0.37",
        "reason": "updated patch version",
    })
    await session.commit()
    assert updated.canonical == "2.0.37"

    # Confirm persisted
    fetched = await repo.get_by_package("sqlalchemy")
    assert fetched.canonical == "2.0.37"
