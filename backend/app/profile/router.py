from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.profile.models import MasterProfileVersion
from app.profile.schemas import (
    MasterProfileData,
    ProfileVersionData,
    ProfileVersionMeta,
)
from app.profile.service import MasterProfileManager

router = APIRouter(prefix="/profile", tags=["profile"])


def get_manager(
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> MasterProfileManager:
    return MasterProfileManager(session)


def _to_version_data(version: MasterProfileVersion) -> ProfileVersionData:
    return ProfileVersionData(
        version_number=version.version_number,
        created_at=version.created_at,
        note=version.note,
        data=MasterProfileData.model_validate(version.data),
    )


@router.get("", response_model=ProfileVersionData)
async def get_current_profile(
    manager: MasterProfileManager = Depends(get_manager),  # noqa: B008
) -> ProfileVersionData:
    version = await manager.get_current()
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no master profile yet")
    return _to_version_data(version)


@router.put("", response_model=ProfileVersionData)
async def put_profile(
    data: MasterProfileData,
    response: Response,
    manager: MasterProfileManager = Depends(get_manager),  # noqa: B008
) -> ProfileVersionData:
    before = await manager.get_current()
    version = await manager.create_version(data)
    is_new = before is None or version.version_number != before.version_number
    response.status_code = status.HTTP_201_CREATED if is_new else status.HTTP_200_OK
    return _to_version_data(version)


@router.get("/versions", response_model=list[ProfileVersionMeta])
async def list_versions(
    manager: MasterProfileManager = Depends(get_manager),  # noqa: B008
) -> list[ProfileVersionMeta]:
    versions = await manager.list_versions()
    return [
        ProfileVersionMeta(version_number=v.version_number, created_at=v.created_at, note=v.note)
        for v in versions
    ]


@router.get("/versions/{version_number}", response_model=ProfileVersionData)
async def get_version(
    version_number: int,
    manager: MasterProfileManager = Depends(get_manager),  # noqa: B008
) -> ProfileVersionData:
    version = await manager.get_version(version_number)
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="version not found")
    return _to_version_data(version)


@router.post(
    "/versions/{version_number}/restore",
    response_model=ProfileVersionData,
    status_code=status.HTTP_201_CREATED,
)
async def restore_version(
    version_number: int,
    manager: MasterProfileManager = Depends(get_manager),  # noqa: B008
) -> ProfileVersionData:
    version = await manager.restore_version(version_number)
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="version not found")
    return _to_version_data(version)
