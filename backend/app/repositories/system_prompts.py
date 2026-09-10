"""System Prompt repository — ownership-scoped queries (Architecture §10)."""

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models


class SystemPromptRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_for_user(self, user_id: uuid.UUID) -> list[models.SystemPrompt]:
        result = await self.session.execute(
            select(models.SystemPrompt)
            .where(models.SystemPrompt.user_id == user_id)
            .order_by(models.SystemPrompt.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_for_user(
        self, prompt_id: uuid.UUID, user_id: uuid.UUID
    ) -> models.SystemPrompt | None:
        result = await self.session.execute(
            select(models.SystemPrompt).where(
                models.SystemPrompt.id == prompt_id,
                models.SystemPrompt.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, user_id: uuid.UUID, title: str, content: str) -> models.SystemPrompt:
        prompt = models.SystemPrompt(user_id=user_id, title=title, content=content)
        self.session.add(prompt)
        await self.session.commit()
        await self.session.refresh(prompt)
        return prompt

    async def update(
        self, prompt: models.SystemPrompt, title: str, content: str
    ) -> models.SystemPrompt:
        prompt.title = title
        prompt.content = content
        await self.session.commit()
        await self.session.refresh(prompt)
        return prompt

    async def referencing_profile_names(
        self, prompt_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[str]:
        result = await self.session.execute(
            select(models.VisionProfile.name).where(
                models.VisionProfile.system_prompt_id == prompt_id,
                models.VisionProfile.user_id == user_id,
            )
        )
        return list(result.scalars().all())

    async def delete(self, prompt: models.SystemPrompt) -> None:
        prompt_id, user_id = prompt.id, prompt.user_id  # capture pre-delete (attrs expire)
        await self.session.delete(prompt)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            names = await self.referencing_profile_names(prompt_id, user_id)
            raise PromptInUseError(names) from exc


class PromptInUseError(Exception):
    """System prompt is referenced by one or more Vision Profiles (409)."""

    def __init__(self, profile_names: list[str]):
        self.profile_names = profile_names
        if profile_names:
            quoted = ", ".join(f"'{n}'" for n in profile_names)
            msg = (
                f"This system prompt is used by profile {quoted} — "
                "reassign or delete that profile first"
            )
        else:
            msg = "This system prompt is in use by a Vision Profile"
        super().__init__(msg)
