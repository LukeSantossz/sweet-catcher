from sqlalchemy import Connection, inspect
from sqlalchemy.ext.asyncio import AsyncEngine


def _table_names(connection: Connection) -> set[str]:
    return set(inspect(connection).get_table_names())


async def test_migration_creates_search_criteria_table(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        tables = await connection.run_sync(_table_names)
    assert "search_criteria" in tables
