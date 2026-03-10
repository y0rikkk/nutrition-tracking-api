from alembic.command import downgrade, upgrade
from alembic.config import Config
from alembic.script import ScriptDirectory


def test_migrations(alembic_config: Config) -> None:
    revisions_dir = ScriptDirectory.from_config(alembic_config)
    revisions = reversed(list(revisions_dir.walk_revisions("base", "heads")))
    # Apply all migrations
    upgrade(alembic_config, "head")

    # Downgrade all migrations
    downgrade(alembic_config, "base")

    # Проходим миграции в порядке 1 -> 0 -> 1 -> 2 -> 1 -> 2 -> 3 -> ...
    for revision in revisions:
        upgrade(alembic_config, revision.revision)
        downgrade(alembic_config, revision.down_revision or "-1")  # type: ignore[arg-type]
        upgrade(alembic_config, revision.revision)
