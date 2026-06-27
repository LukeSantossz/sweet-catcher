from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.profile.models import MasterProfile, MasterProfileVersion
from app.profile.schemas import MasterProfileData


class MasterProfileManager:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create_profile(self) -> MasterProfile:
        result = await self._session.execute(select(MasterProfile).limit(1))
        profile = result.scalar_one_or_none()
        if profile is None:
            profile = MasterProfile()
            self._session.add(profile)
            await self._session.flush()
        return profile

    async def get_current(self) -> MasterProfileVersion | None:
        result = await self._session.execute(
            select(MasterProfileVersion)
            .order_by(MasterProfileVersion.version_number.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create_version(
        self, data: MasterProfileData, note: str | None = None
    ) -> MasterProfileVersion:
        profile = await self.get_or_create_profile()
        latest = await self.get_current()
        payload = data.model_dump(mode="json")
        if latest is not None and latest.data == payload:
            return latest
        next_number = latest.version_number + 1 if latest is not None else 1
        version = MasterProfileVersion(
            profile_id=profile.id,
            version_number=next_number,
            note=note,
            data=payload,
        )
        self._session.add(version)
        await self._session.flush()
        await self._session.refresh(version)
        return version

    async def list_versions(self) -> list[MasterProfileVersion]:
        result = await self._session.execute(
            select(MasterProfileVersion).order_by(MasterProfileVersion.version_number.desc())
        )
        return list(result.scalars().all())

    async def get_version(self, version_number: int) -> MasterProfileVersion | None:
        result = await self._session.execute(
            select(MasterProfileVersion).where(
                MasterProfileVersion.version_number == version_number
            )
        )
        return result.scalar_one_or_none()

    async def restore_version(self, version_number: int) -> MasterProfileVersion | None:
        source = await self.get_version(version_number)
        if source is None:
            return None
        data = MasterProfileData.model_validate(source.data)
        return await self.create_version(data, note=f"restored from v{version_number}")
