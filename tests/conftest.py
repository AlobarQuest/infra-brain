"""
Test configuration. Uses a separate test database via TEST_DATABASE_URL env var.
Falls back to DATABASE_URL if not set.

Run tests with:
    TEST_DATABASE_URL=postgresql+asyncpg://... pytest
"""
import os

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.db.engine import Base
from src.db import models  # noqa: F401 — register all models


TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    os.environ.get("DATABASE_URL", "postgresql+asyncpg://infrabrain:changeme@localhost:5432/infrabrain_test"),
)


@pytest.fixture(scope="session")
def engine():
    return create_async_engine(TEST_DATABASE_URL, echo=False)


@pytest.fixture(scope="session")
async def setup_db(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture()
async def session(engine, setup_db):
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with factory() as s:
        yield s
        await s.rollback()
