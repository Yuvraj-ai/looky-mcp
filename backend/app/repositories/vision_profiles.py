"""Vision Profile repository — ownership-scoped; transactional activation (§7)."""

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models


class VisionProfileRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_for_user(self, user_id: uuid.UUID) -> list[models.VisionProfile]:
        result = await self.session.execute(
            select(models.VisionProfile)
            .where(models.VisionProfile.user_id == user_id)
            .order_by(models.VisionProfile.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_for_user(
        self, profile_id: uuid.UUID, user_id: uuid.UUID
    ) -> models.VisionProfile | None:
        result = await self.session.execute(
            select(models.VisionProfile).where(
                models.VisionProfile.id == profile_id,
                models.VisionProfile.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_active(self, user_id: uuid.UUID) -> models.VisionProfile | None:
        result = await self.session.execute(
            select(models.VisionProfile).where(
                models.VisionProfile.user_id == user_id,
                models.VisionProfile.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        user_id: uuid.UUID,
        name: str,
        endpoint: str,
        model: str,
        system_prompt_id: uuid.UUID,
        encrypted_api_key: bytes,
    ) -> models.VisionProfile:
        profile = models.VisionProfile(
            user_id=user_id,
            name=name,
            endpoint=endpoint,
            model=model,
            system_prompt_id=system_prompt_id,
            encrypted_api_key=encrypted_api_key,
            is_active=False,
        )
        self.session.add(profile)
        await self.session.commit()
        await self.session.refresh(profile)
        return profile

    async def update(
        self,
        profile: models.VisionProfile,
        *,
        name: str,
        endpoint: str,
        model: str,
        system_prompt_id: uuid.UUID,
        encrypted_api_key: bytes | None,  # None = keep existing key
    ) -> models.VisionProfile:
        profile.name = name
        profile.endpoint = endpoint
        profile.model = model
        profile.system_prompt_id = system_prompt_id
        if encrypted_api_key is not None:
            profile.encrypted_api_key = encrypted_api_key
        await self.session.commit()
        await self.session.refresh(profile)
        return profile

    async def delete(self, profile: models.VisionProfile) -> None:
        await self.session.delete(profile)
        await self.session.commit()

    async def activate(self, profile: models.VisionProfile) -> models.VisionProfile:
        """Transactional swap (Architecture §7): deactivate others then activate,
        committed atomically so the partial unique index never sees two active rows."""
        # order matters: clear the current active row first so the partial unique
        # index (user_id WHERE is_active) isn't violated mid-transaction
        await self.session.execute(
            update(models.VisionProfile)
            .where(
                models.VisionProfile.user_id == profile.user_id,
                models.VisionProfile.is_active.is_(True),
                models.VisionProfile.id != profile.id,
            )
            .values(is_active=False)
        )
        await self.session.execute(
            update(models.VisionProfile)
            .where(models.VisionProfile.id == profile.id)
            .values(is_active=True)
        )
        await self.session.commit()
        await self.session.refresh(profile)
        return profile
