from sqlalchemy.ext.asyncio import AsyncSession

from app.profile.schemas import MasterProfileData
from app.profile.service import MasterProfileManager


def _data(full_name: str) -> MasterProfileData:
    return MasterProfileData.model_validate({"basics": {"full_name": full_name}})


async def test_first_save_creates_version_one(db_session: AsyncSession) -> None:
    manager = MasterProfileManager(db_session)
    version = await manager.create_version(_data("Ada"))
    assert version.version_number == 1


async def test_distinct_save_increments_version(db_session: AsyncSession) -> None:
    manager = MasterProfileManager(db_session)
    await manager.create_version(_data("Ada"))
    second = await manager.create_version(_data("Grace"))
    assert second.version_number == 2


async def test_identical_save_is_deduped(db_session: AsyncSession) -> None:
    manager = MasterProfileManager(db_session)
    first = await manager.create_version(_data("Ada"))
    again = await manager.create_version(_data("Ada"))
    assert again.version_number == first.version_number
    assert len(await manager.list_versions()) == 1


async def test_get_current_returns_latest(db_session: AsyncSession) -> None:
    manager = MasterProfileManager(db_session)
    await manager.create_version(_data("Ada"))
    await manager.create_version(_data("Grace"))
    current = await manager.get_current()
    assert current is not None
    assert current.version_number == 2
    assert current.data["basics"]["full_name"] == "Grace"


async def test_list_versions_is_descending(db_session: AsyncSession) -> None:
    manager = MasterProfileManager(db_session)
    await manager.create_version(_data("Ada"))
    await manager.create_version(_data("Grace"))
    numbers = [v.version_number for v in await manager.list_versions()]
    assert numbers == [2, 1]


async def test_restore_creates_new_version_from_source(db_session: AsyncSession) -> None:
    manager = MasterProfileManager(db_session)
    await manager.create_version(_data("Ada"))
    await manager.create_version(_data("Grace"))
    restored = await manager.restore_version(1)
    assert restored is not None
    assert restored.version_number == 3
    assert restored.data["basics"]["full_name"] == "Ada"


async def test_restore_missing_version_returns_none(db_session: AsyncSession) -> None:
    manager = MasterProfileManager(db_session)
    assert await manager.restore_version(99) is None
