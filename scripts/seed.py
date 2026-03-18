"""
Seed Infra Brain with initial data from seed/data.json.

Usage:
    python scripts/seed.py               # skip existing records (default)
    python scripts/seed.py --skip-existing
    python scripts/seed.py --force       # overwrite all records
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

# Allow running as a script from the project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.engine import async_session_factory  # noqa: E402
from src.repositories.combos import ComboRepository  # noqa: E402
from src.repositories.lessons import LessonRepository  # noqa: E402
from src.repositories.rules import RuleRepository  # noqa: E402
from src.repositories.versions import VersionRepository  # noqa: E402


async def seed(skip_existing: bool = True) -> None:
    data_path = Path(__file__).parent.parent / "seed" / "data.json"
    data = json.loads(data_path.read_text())

    async with async_session_factory() as session:
        versions_repo = VersionRepository(session)
        rules_repo = RuleRepository(session)
        combos_repo = ComboRepository(session)
        lessons_repo = LessonRepository(session)

        # Versions — upsert (always update if --force, skip if --skip-existing)
        versions_loaded = 0
        for v in data.get("versions", []):
            existing = await versions_repo.get_by_package(v["package"])
            if existing and skip_existing:
                continue
            await versions_repo.upsert(v)
            versions_loaded += 1

        # Rules — race-safe upsert via ON CONFLICT DO NOTHING on unique rule text
        rules_loaded = 0
        for r in data.get("rules", []):
            await rules_repo.add_if_not_exists(r)
            rules_loaded += 1

        # Combos — upsert by name
        combos_loaded = 0
        for c in data.get("combos", []):
            existing = await combos_repo.get_by_name(c["name"])
            if existing and skip_existing:
                continue
            if existing:
                for key, value in c.items():
                    if key != "name":
                        setattr(existing, key, value)
            else:
                from src.db.models import Combo
                session.add(Combo(**c))
            combos_loaded += 1

        # Lessons — race-safe upsert via ON CONFLICT DO NOTHING on unique title
        lessons_loaded = 0
        for l in data.get("lessons", []):
            await lessons_repo.add_if_not_exists(l)
            lessons_loaded += 1

        await session.commit()

    print(
        f"Seed complete — "
        f"versions: {versions_loaded}, "
        f"rules: {rules_loaded}, "
        f"combos: {combos_loaded}, "
        f"lessons: {lessons_loaded}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Infra Brain database")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--skip-existing", action="store_true", default=True, help="Skip records that already exist (default)")
    group.add_argument("--force", action="store_true", help="Overwrite all existing records")
    args = parser.parse_args()

    skip_existing = not args.force
    asyncio.run(seed(skip_existing=skip_existing))


if __name__ == "__main__":
    main()
