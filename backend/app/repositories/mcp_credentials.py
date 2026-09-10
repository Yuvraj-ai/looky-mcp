"""MCP credential repository (Decision #7): one credential per user, hash only."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models


class McpCredentialRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_for_user(self, user_id: uuid.UUID) -> models.McpCredential | None:
        result = await self.session.execute(
            select(models.McpCredential).where(
                models.McpCredential.user_id == user_id,
                models.McpCredential.revoked_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_key_hash(self, key_hash: str) -> models.McpCredential | None:
        result = await self.session.execute(
            select(models.McpCredential).where(
                models.McpCredential.key_hash == key_hash,
                models.McpCredential.revoked_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def upsert(self, user_id: uuid.UUID, key_hash: str) -> models.McpCredential:
        """Create or regenerate. UNIQUE(user_id) means one row per user forever —
        regenerate = replace key_hash + clear revoked_at on the existing row.
        Old key becomes invalid immediately (hash overwritten in the same commit)."""
        cred = await self.get_for_user(user_id)
        if cred is None:
            # row may exist but be revoked — UNIQUE(user_id) forces reuse
            result = await self.session.execute(
                select(models.McpCredential).where(models.McpCredential.user_id == user_id)
            )
            cred = result.scalar_one_or_none()
        if cred is None:
            cred = models.McpCredential(user_id=user_id, key_hash=key_hash)
            self.session.add(cred)
        else:
            cred.key_hash = key_hash
            cred.revoked_at = None
        await self.session.commit()
        await self.session.refresh(cred)
        return cred

    async def revoke(self, credential: models.McpCredential) -> None:
        credential.revoked_at = datetime.now(UTC)
        await self.session.commit()
