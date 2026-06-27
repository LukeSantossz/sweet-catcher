from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.profile.models import MasterProfile, MasterProfileVersion
from app.profile.schemas import MasterProfileData, ProfileVersionMeta


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
        # Single-profile (single-user V1) assumption: no profile_id filter applied.
        # Revisit for multi-profile per SPEC / ADR 0006.
        result = await self._session.execute(
            select(MasterProfileVersion)
            .order_by(MasterProfileVersion.version_number.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create_version(
        self, data: MasterProfileData, note: str | None = None, *, dedupe: bool = True
    ) -> MasterProfileVersion:
        profile = await self.get_or_create_profile()
        latest = await self.get_current()
        payload = data.model_dump(mode="json")
        if dedupe and latest is not None and latest.data == payload:
            return latest
        # Single-profile (single-user V1) assumption: next version_number is global max + 1.
        # Revisit for multi-profile per SPEC / ADR 0006.
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

    async def list_versions(self) -> list[ProfileVersionMeta]:
        # Single-profile (single-user V1) assumption: no profile_id filter applied.
        # Revisit for multi-profile per SPEC / ADR 0006.
        # Select only metadata columns; do NOT fetch the JSONB data column.
        result = await self._session.execute(
            select(
                MasterProfileVersion.version_number,
                MasterProfileVersion.created_at,
                MasterProfileVersion.note,
            ).order_by(MasterProfileVersion.version_number.desc())
        )
        return [
            ProfileVersionMeta(
                version_number=row.version_number,
                created_at=row.created_at,
                note=row.note,
            )
            for row in result
        ]

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
        # dedupe=False: always create a new version regardless of whether the source
        # data matches the current latest snapshot (spec AC: restore creates a new
        # highest-numbered version unconditionally).
        return await self.create_version(
            data, note=f"restored from v{version_number}", dedupe=False
        )
