"""Auth routes — Architecture §11 (login/logout/me; no register route)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.passwords import verify_password
from app.auth.session import (
    clear_session_cookie,
    get_current_user_id,
    set_session_cookie,
)
from app.db.session import get_db
from app.repositories.users import UserRepository

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr

    model_config = {"from_attributes": True}


@router.post("/login", response_model=UserResponse)
async def login(
    body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)
) -> UserResponse:
    repo = UserRepository(db)
    user = await repo.get_by_email(body.email)
    # Same generic error for unknown email and wrong password (no enumeration).
    if (
        user is None
        or user.password_hash is None
        or not verify_password(user.password_hash, body.password)
    ):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    set_session_cookie(response, user.id)
    return UserResponse.model_validate(user)


@router.post("/logout")
async def logout(response: Response, _: uuid.UUID = Depends(get_current_user_id)) -> None:
    clear_session_cookie(response)


@router.get("/me", response_model=UserResponse)
async def me(
    user_id: uuid.UUID = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)
) -> UserResponse:
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return UserResponse.model_validate(user)
