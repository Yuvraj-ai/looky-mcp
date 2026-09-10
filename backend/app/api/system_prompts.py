"""System Prompt routes (Architecture §11). Ownership-scoped; 404 for foreign ids,
409 (with clear message) when deleting a prompt referenced by a Vision Profile."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.session import get_current_user_id
from app.db.session import get_db
from app.repositories.system_prompts import PromptInUseError, SystemPromptRepository

router = APIRouter(prefix="/api/system-prompts", tags=["system-prompts"])


class SystemPromptBody(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)


class SystemPromptResponse(BaseModel):
    id: uuid.UUID
    title: str
    content: str

    model_config = {"from_attributes": True}


def _repo(db: AsyncSession = Depends(get_db)) -> SystemPromptRepository:
    return SystemPromptRepository(db)


@router.get("", response_model=list[SystemPromptResponse])
async def list_prompts(
    user_id: uuid.UUID = Depends(get_current_user_id),
    repo: SystemPromptRepository = Depends(_repo),
) -> list[SystemPromptResponse]:
    prompts = await repo.list_for_user(user_id)
    return [SystemPromptResponse.model_validate(p) for p in prompts]


@router.post("", response_model=SystemPromptResponse, status_code=201)
async def create_prompt(
    body: SystemPromptBody,
    user_id: uuid.UUID = Depends(get_current_user_id),
    repo: SystemPromptRepository = Depends(_repo),
) -> SystemPromptResponse:
    prompt = await repo.create(user_id, body.title, body.content)
    return SystemPromptResponse.model_validate(prompt)


async def _get_owned(prompt_id: uuid.UUID, user_id: uuid.UUID, repo: SystemPromptRepository):
    prompt = await repo.get_for_user(prompt_id, user_id)
    if prompt is None:
        raise HTTPException(status_code=404, detail="System prompt not found")
    return prompt


@router.get("/{prompt_id}", response_model=SystemPromptResponse)
async def get_prompt(
    prompt_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    repo: SystemPromptRepository = Depends(_repo),
) -> SystemPromptResponse:
    prompt = await _get_owned(prompt_id, user_id, repo)
    return SystemPromptResponse.model_validate(prompt)


@router.put("/{prompt_id}", response_model=SystemPromptResponse)
async def update_prompt(
    prompt_id: uuid.UUID,
    body: SystemPromptBody,
    user_id: uuid.UUID = Depends(get_current_user_id),
    repo: SystemPromptRepository = Depends(_repo),
) -> SystemPromptResponse:
    prompt = await _get_owned(prompt_id, user_id, repo)
    updated = await repo.update(prompt, body.title, body.content)
    return SystemPromptResponse.model_validate(updated)


@router.delete("/{prompt_id}", status_code=204)
async def delete_prompt(
    prompt_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    repo: SystemPromptRepository = Depends(_repo),
) -> None:
    prompt = await _get_owned(prompt_id, user_id, repo)
    try:
        await repo.delete(prompt)
    except PromptInUseError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
