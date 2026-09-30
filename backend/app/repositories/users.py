"""User repository — all queries scoped by authenticated identity (Architecture §10)."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: str) -> models.User | None:
        result = await self.session.execute(select(models.User).where(models.User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> models.User | None:
        return await self.session.get(models.User, user_id)

    async def delete_user_and_all_data(self, user_id: uuid.UUID) -> None:
        """Deletes only the specified user and all related records (vision profiles,
        system prompts, mcp credentials). Scoped strictly to user_id so no other user's
        data can ever be affected."""
        from sqlalchemy import delete

        # 1. Delete user's vision profiles first (they hold a RESTRICT FK to system_prompts)
        await self.session.execute(
            delete(models.VisionProfile).where(models.VisionProfile.user_id == user_id)
        )
        # 2. Delete user's system prompts
        await self.session.execute(
            delete(models.SystemPrompt).where(models.SystemPrompt.user_id == user_id)
        )
        # 3. Delete user's MCP credentials
        await self.session.execute(
            delete(models.McpCredential).where(models.McpCredential.user_id == user_id)
        )
        # 4. Delete user account record
        await self.session.execute(
            delete(models.User).where(models.User.id == user_id)
        )
        await self.session.commit()
