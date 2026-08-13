from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.db.session import Base
from app.models import entities  # noqa: F401


def test_initial_migration_upgrade_downgrade_cycle(tmp_path: Path) -> None:
    database_path = tmp_path / "migration.sqlite3"
    database_url = f"sqlite:///{database_path}"
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.attributes["database_url"] = database_url

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    migrated_tables = set(inspect(engine).get_table_names())
    assert migrated_tables == set(Base.metadata.tables) | {"alembic_version"}
    command.check(config)

    command.downgrade(config, "base")
    assert inspect(engine).get_table_names() == ["alembic_version"]

    command.upgrade(config, "head")
    assert set(inspect(engine).get_table_names()) == set(Base.metadata.tables) | {"alembic_version"}
    engine.dispose()
