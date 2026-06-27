from sqlalchemy import Connection, inspect
from sqlalchemy.ext.asyncio import AsyncEngine


def _table_names(connection: Connection) -> set[str]:
    return set(inspect(connection).get_table_names())


async def test_migration_creates_master_profile_tables(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        tables = await connection.run_sync(_table_names)
    assert {"master_profile", "master_profile_version"} <= tables
