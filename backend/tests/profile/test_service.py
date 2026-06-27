from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.profile.schemas import (
    Basics,
    Experience,
    Language,
    LanguageProficiency,
    Link,
    LinkType,
    MasterProfileData,
    ProfileVersionMeta,
)
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


# --- new tests for fix wave ---


async def test_restore_of_latest_data_always_creates_new_version(
    db_session: AsyncSession,
) -> None:
    """restore_version must always create a new version, even when source data equals the
    current latest snapshot.  Without the dedupe=False fix this dedupes and returns version 1.
    """
    manager = MasterProfileManager(db_session)
    v1 = await manager.create_version(_data("Ada"))
    # v1 is the only (and latest) version; restoring it must produce version 2
    restored = await manager.restore_version(v1.version_number)
    assert restored is not None
    assert restored.version_number == 2
    versions = await manager.list_versions()
    assert len(versions) == 2


async def test_list_versions_returns_profile_version_meta(db_session: AsyncSession) -> None:
    """list_versions must return ProfileVersionMeta objects, not full ORM rows with data."""
    manager = MasterProfileManager(db_session)
    await manager.create_version(_data("Ada"))
    items = await manager.list_versions()
    assert len(items) == 1
    item = items[0]
    assert isinstance(item, ProfileVersionMeta)
    assert not hasattr(item, "data")


async def test_create_version_dedupes_enum_date_httpurl_types(
    db_session: AsyncSession,
) -> None:
    """Regression guard: create_version deduplication still holds across a JSONB round-trip
    for fields that serialise as non-string types (StrEnum → str, date → ISO string,
    HttpUrl → string).  This must pass before and after the fix.
    """
    manager = MasterProfileManager(db_session)
    data = MasterProfileData(
        basics=Basics(full_name="Ada"),
        languages=[Language(name="English", proficiency=LanguageProficiency.native)],
        experiences=[
            Experience(
                company="Acme",
                role="Engineer",
                start_date=date(2020, 1, 1),
                end_date=date(2022, 12, 31),
            )
        ],
        links=[Link(url="https://github.com/ada", type=LinkType.github)],  # type: ignore[arg-type]
    )
    v1 = await manager.create_version(data)
    v2 = await manager.create_version(data)
    assert v1.version_number == v2.version_number
    versions = await manager.list_versions()
    assert len(versions) == 1
