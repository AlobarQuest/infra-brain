import pytest

from src.repositories.rules import RuleRepository


@pytest.fixture
async def seeded_rules(session):
    repo = RuleRepository(session)
    await repo.add({
        "severity": "BLOCK",
        "category": "deployment",
        "rule": "Never source-build Next.js on VPS",
        "reason": "CPU spikes stall Coolify",
        "source_app": "lifeops-portal",
    })
    await repo.add({
        "severity": "WARN",
        "category": "database",
        "rule": "Do not use Redis as primary datastore",
        "reason": "Redis is cache only",
        "source_app": None,
    })
    await repo.add({
        "severity": "INFO",
        "category": "general",
        "rule": "Query Infra Brain before pinning any version",
        "reason": "Single source of truth",
        "source_app": None,
    })
    await session.commit()


async def test_get_block_rules_returns_only_block(session, seeded_rules):
    repo = RuleRepository(session)
    rules = await repo.list_all(severity="BLOCK")
    assert len(rules) >= 1
    assert all(r.severity == "BLOCK" for r in rules)


async def test_get_rules_by_category(session, seeded_rules):
    repo = RuleRepository(session)
    rules = await repo.list_all(category="database")
    assert len(rules) >= 1
    assert all(r.category == "database" for r in rules)


async def test_add_rule_persists(session):
    repo = RuleRepository(session)
    r = await repo.add({
        "severity": "WARN",
        "category": "ci",
        "rule": "Pin SHA for all GitHub Actions",
        "reason": "Prevent supply chain attacks",
        "source_app": None,
    })
    await session.commit()
    assert r.id is not None
    assert r.severity == "WARN"

    # Confirm it's filterable
    rules = await repo.list_all(category="ci")
    assert any(x.rule == "Pin SHA for all GitHub Actions" for x in rules)
