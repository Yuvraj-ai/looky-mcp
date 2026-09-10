"""Vision Profile routes (Architecture §11). Key never returned; blank key on
update = unchanged; activation is transactional."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.session import get_current_user_id
from app.crypto import encrypt_api_key
from app.db.session import get_db
from app.repositories.system_prompts import SystemPromptRepository
from app.repositories.vision_profiles import VisionProfileRepository

router = APIRouter(prefix="/api/vision-profiles", tags=["vision-profiles"])


class VisionProfileCreateBody(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    endpoint: str = Field(min_length=1)
    model: str = Field(min_length=1)
    api_key: str = Field(min_length=1)
    system_prompt_id: uuid.UUID


class VisionProfileUpdateBody(BaseModel):
    """Same as create, but api_key may be "" meaning keep the existing key."""

    name: str = Field(min_length=1, max_length=200)
    endpoint: str = Field(min_length=1)
    model: str = Field(min_length=1)
    api_key: str = ""
    system_prompt_id: uuid.UUID


class VisionProfileResponse(BaseModel):
    id: uuid.UUID
    name: str
    endpoint: str
    model: str
    system_prompt_id: uuid.UUID
    has_api_key: bool
    is_active: bool

    model_config = {"from_attributes": True}

    @classmethod
    def from_profile(cls, profile) -> "VisionProfileResponse":
        return cls(
            id=profile.id,
            name=profile.name,
            endpoint=profile.endpoint,
            model=profile.model,
            system_prompt_id=profile.system_prompt_id,
            has_api_key=True,  # encrypted_api_key is NOT NULL in schema
            is_active=profile.is_active,
        )


def _repos(db: AsyncSession = Depends(get_db)):
    return VisionProfileRepository(db), SystemPromptRepository(db)


@router.get("", response_model=list[VisionProfileResponse])
async def list_profiles(
    user_id: uuid.UUID = Depends(get_current_user_id),
    repos: tuple[VisionProfileRepository, SystemPromptRepository] = Depends(_repos),
) -> list[VisionProfileResponse]:
    vrepo, _ = repos
    profiles = await vrepo.list_for_user(user_id)
    return [VisionProfileResponse.from_profile(p) for p in profiles]


async def _validate_system_prompt_owned(
    system_prompt_id: uuid.UUID, user_id: uuid.UUID, srepo: SystemPromptRepository
) -> None:
    prompt = await srepo.get_for_user(system_prompt_id, user_id)
    if prompt is None:
        raise HTTPException(status_code=422, detail="Unknown system prompt")


@router.post("", response_model=VisionProfileResponse, status_code=201)
async def create_profile(
    body: VisionProfileCreateBody,
    user_id: uuid.UUID = Depends(get_current_user_id),
    repos: tuple[VisionProfileRepository, SystemPromptRepository] = Depends(_repos),
) -> VisionProfileResponse:
    vrepo, srepo = repos
    await _validate_system_prompt_owned(body.system_prompt_id, user_id, srepo)
    profile = await vrepo.create(
        user_id=user_id,
        name=body.name,
        endpoint=body.endpoint,
        model=body.model,
        system_prompt_id=body.system_prompt_id,
        encrypted_api_key=encrypt_api_key(body.api_key),
    )
    return VisionProfileResponse.from_profile(profile)


async def _get_owned(profile_id: uuid.UUID, user_id: uuid.UUID, vrepo: VisionProfileRepository):
    profile = await vrepo.get_for_user(profile_id, user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Vision profile not found")
    return profile


@router.get("/{profile_id}", response_model=VisionProfileResponse)
async def get_profile(
    profile_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    repos: tuple[VisionProfileRepository, SystemPromptRepository] = Depends(_repos),
) -> VisionProfileResponse:
    vrepo, _ = repos
    profile = await _get_owned(profile_id, user_id, vrepo)
    return VisionProfileResponse.from_profile(profile)


@router.put("/{profile_id}", response_model=VisionProfileResponse)
async def update_profile(
    profile_id: uuid.UUID,
    body: VisionProfileUpdateBody,
    user_id: uuid.UUID = Depends(get_current_user_id),
    repos: tuple[VisionProfileRepository, SystemPromptRepository] = Depends(_repos),
) -> VisionProfileResponse:
    vrepo, srepo = repos
    profile = await _get_owned(profile_id, user_id, vrepo)
    await _validate_system_prompt_owned(body.system_prompt_id, user_id, srepo)
    updated = await vrepo.update(
        profile,
        name=body.name,
        endpoint=body.endpoint,
        model=body.model,
        system_prompt_id=body.system_prompt_id,
        encrypted_api_key=(
            encrypt_api_key(body.api_key) if body.api_key else None  # "" = keep old
        ),
    )
    return VisionProfileResponse.from_profile(updated)


@router.delete("/{profile_id}", status_code=204)
async def delete_profile(
    profile_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    repos: tuple[VisionProfileRepository, SystemPromptRepository] = Depends(_repos),
) -> None:
    vrepo, _ = repos
    profile = await _get_owned(profile_id, user_id, vrepo)
    await vrepo.delete(profile)


@router.post("/{profile_id}/activate", response_model=VisionProfileResponse)
async def activate_profile(
    profile_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    repos: tuple[VisionProfileRepository, SystemPromptRepository] = Depends(_repos),
) -> VisionProfileResponse:
    vrepo, _ = repos
    profile = await _get_owned(profile_id, user_id, vrepo)
    activated = await vrepo.activate(profile)
    return VisionProfileResponse.from_profile(activated)
