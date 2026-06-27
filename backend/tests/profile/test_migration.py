from sqlalchemy import Connection, inspect
from sqlalchemy.ext.asyncio import AsyncEngine


def _table_names(connection: Connection) -> set[str]:
    return set(inspect(connection).get_table_names())


def _unique_constraint_column_sets(connection: Connection, table: str) -> list[set[str]]:
    constraints = inspect(connection).get_unique_constraints(table)
    return [set(c["column_names"]) for c in constraints]


async def test_migration_creates_master_profile_tables(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        tables = await connection.run_sync(_table_names)
    assert {"master_profile", "master_profile_version"} <= tables


async def test_migration_creates_unique_constraint_on_version(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        column_sets = await connection.run_sync(
            _unique_constraint_column_sets, "master_profile_version"
        )
    assert {"profile_id", "version_number"} in column_sets
