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
