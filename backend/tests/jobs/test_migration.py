from sqlalchemy import Connection, inspect
from sqlalchemy.ext.asyncio import AsyncEngine


def _table_names(connection: Connection) -> set[str]:
    return set(inspect(connection).get_table_names())


def _unique_constraint_column_sets(connection: Connection, table: str) -> list[set[str]]:
    constraints = inspect(connection).get_unique_constraints(table)
    return [set(c["column_names"]) for c in constraints]


async def test_migration_creates_jobs_table(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        tables = await connection.run_sync(_table_names)
    assert "jobs" in tables


async def test_migration_jobs_unique_source_external_id(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        column_sets = await connection.run_sync(_unique_constraint_column_sets, "jobs")
    assert {"source", "source_external_id"} in column_sets
