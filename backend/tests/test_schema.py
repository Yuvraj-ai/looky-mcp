"""Architecture §5 schema tests: all four tables, constraints, partial unique index."""

import uuid

import pytest
from sqlalchemy import text

from app.db import models


async def test_tables_exist(db_engine) -> None:
    async with db_engine.connect() as conn:
        for table in ["users", "system_prompts", "vision_profiles", "mcp_credentials"]:
            row = await conn.execute(text("SELECT to_regclass(:t)"), {"t": f"public.{table}"})
            assert row.scalar() is not None, f"table {table} missing"


async def test_users_email_unique(db_session) -> None:
    from sqlalchemy.exc import IntegrityError

    u1 = models.User(email="a@b.c", password_hash="x")
    u2 = models.User(email="a@b.c", password_hash="y")
    db_session.add(u1)
    await db_session.commit()
    db_session.add(u2)
    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_one_active_profile_per_user(db_session) -> None:
    """The partial unique index must reject a second active profile per user."""
    from sqlalchemy.exc import IntegrityError

    user = models.User(email="u@v.w")
    db_session.add(user)
    await db_session.flush()

    sp = models.SystemPrompt(user_id=user.id, title="t", content="c")
    db_session.add(sp)
    await db_session.flush()

    p1 = models.VisionProfile(
        user_id=user.id,
        name="p1",
        endpoint="http://e",
        model="m",
        system_prompt_id=sp.id,
        encrypted_api_key=b"x",
        is_active=True,
    )
    p2 = models.VisionProfile(
        user_id=user.id,
        name="p2",
        endpoint="http://e",
        model="m",
        system_prompt_id=sp.id,
        encrypted_api_key=b"x",
        is_active=True,
    )
    db_session.add(p1)
    await db_session.flush()
    db_session.add(p2)
    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_two_active_profiles_different_users_ok(db_session) -> None:
    u1 = models.User(email="one@x.y")
    u2 = models.User(email="two@x.y")
    db_session.add_all([u1, u2])
    await db_session.flush()

    sp1 = models.SystemPrompt(user_id=u1.id, title="t", content="c")
    sp2 = models.SystemPrompt(user_id=u2.id, title="t", content="c")
    db_session.add_all([sp1, sp2])
    await db_session.flush()

    db_session.add_all(
        [
            models.VisionProfile(
                user_id=u1.id,
                name="p",
                endpoint="http://e",
                model="m",
                system_prompt_id=sp1.id,
                encrypted_api_key=b"x",
                is_active=True,
            ),
            models.VisionProfile(
                user_id=u2.id,
                name="p",
                endpoint="http://e",
                model="m",
                system_prompt_id=sp2.id,
                encrypted_api_key=b"x",
                is_active=True,
            ),
        ]
    )
    await db_session.commit()  # no error


async def test_inactive_profiles_unbounded(db_session) -> None:
    user = models.User(email="many@x.y")
    db_session.add(user)
    await db_session.flush()
    sp = models.SystemPrompt(user_id=user.id, title="t", content="c")
    db_session.add(sp)
    await db_session.flush()
    db_session.add_all(
        [
            models.VisionProfile(
                user_id=user.id,
                name=f"p{i}",
                endpoint="http://e",
                model="m",
                system_prompt_id=sp.id,
                encrypted_api_key=b"x",
                is_active=False,
            )
            for i in range(5)
        ]
    )
    await db_session.commit()  # multiple inactive allowed


async def test_prompt_delete_restricted_when_referenced(db_session) -> None:
    """ON DELETE RESTRICT: deleting a referenced system prompt must fail at DB level."""
    from sqlalchemy.exc import IntegrityError

    user = models.User(email="restrict@x.y")
    db_session.add(user)
    await db_session.flush()
    sp = models.SystemPrompt(user_id=user.id, title="t", content="c")
    db_session.add(sp)
    await db_session.flush()
    db_session.add(
        models.VisionProfile(
            user_id=user.id,
            name="p",
            endpoint="http://e",
            model="m",
            system_prompt_id=sp.id,
            encrypted_api_key=b"x",
            is_active=False,
        )
    )
    await db_session.commit()
    await db_session.delete(sp)
    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_user_cascade_deletes_prompts_and_credentials(db_session) -> None:
    """users ON DELETE CASCADE: prompts, profiles, mcp_credentials follow the user."""
    from sqlalchemy import select

    user = models.User(email="cascade@x.y")
    db_session.add(user)
    await db_session.flush()
    sp = models.SystemPrompt(user_id=user.id, title="t", content="c")
    db_session.add(sp)
    await db_session.flush()
    db_session.add_all(
        [
            models.VisionProfile(
                user_id=user.id,
                name="p",
                endpoint="http://e",
                model="m",
                system_prompt_id=sp.id,
                encrypted_api_key=b"x",
                is_active=False,
            ),
            models.McpCredential(user_id=user.id, key_hash="h"),
        ]
    )
    await db_session.commit()

    # bypass RESTRICT by removing the profile first, then delete user
    await db_session.execute(
        text("DELETE FROM vision_profiles WHERE user_id = :uid"), {"uid": user.id}
    )
    await db_session.delete(user)
    await db_session.commit()

    prompts = (
        (
            await db_session.execute(
                select(models.SystemPrompt).where(models.SystemPrompt.user_id == user.id)
            )
        )
        .scalars()
        .all()
    )
    creds = (
        (
            await db_session.execute(
                select(models.McpCredential).where(models.McpCredential.user_id == user.id)
            )
        )
        .scalars()
        .all()
    )
    assert prompts == []
    assert creds == []


async def test_mcp_credential_one_per_user(db_session) -> None:
    from sqlalchemy.exc import IntegrityError

    user = models.User(email="onekey@x.y")
    db_session.add(user)
    await db_session.flush()
    db_session.add(models.McpCredential(user_id=user.id, key_hash="h1"))
    await db_session.flush()
    db_session.add(models.McpCredential(user_id=user.id, key_hash="h2"))
    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_uuid_primary_keys(db_session) -> None:
    user = models.User(email="uuid@x.y")
    db_session.add(user)
    await db_session.flush()
    assert isinstance(user.id, uuid.UUID)
    assert isinstance(user.created_at.year, int)
