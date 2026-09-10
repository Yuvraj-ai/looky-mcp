"""Universal Extra Instructions routes (Architecture requirements §17;
storage decision logged in decisions.md 2026-09-10 / questions.md Q2)."""

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.session import get_current_user_id
from app.db.session import get_db
from app.repositories.settings import AppSettingsRepository

router = APIRouter(prefix="/api/settings", tags=["settings"])


class ExtraInstructionsBody(BaseModel):
    content: str = Field(max_length=20000)


def _repo(db: AsyncSession = Depends(get_db)) -> AppSettingsRepository:
    return AppSettingsRepository(db)


@router.get("/extra-instructions", response_model=ExtraInstructionsBody)
async def get_extra_instructions(
    _: uuid.UUID = Depends(get_current_user_id),
    repo: AppSettingsRepository = Depends(_repo),
) -> ExtraInstructionsBody:
    return ExtraInstructionsBody(content=await repo.get_extra_instructions())


@router.put("/extra-instructions", response_model=ExtraInstructionsBody)
async def put_extra_instructions(
    body: ExtraInstructionsBody,
    _: uuid.UUID = Depends(get_current_user_id),
    repo: AppSettingsRepository = Depends(_repo),
) -> ExtraInstructionsBody:
    await repo.set_extra_instructions(body.content)
    return ExtraInstructionsBody(content=body.content)
