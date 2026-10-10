"""Per-user setup and MCP request activity summary."""

import uuid
from datetime import UTC, date, datetime, time, timedelta
from math import ceil

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.session import get_current_user_id
from app.db import models
from app.db.session import get_db
from app.services.dashboard_rate_limiter import get_dashboard_rate_limiter

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class SetupSummary(BaseModel):
    active_profile_name: str | None
    active_model: str | None
    profile_count: int
    prompt_count: int
    mcp_configured: bool


class DailyUsage(BaseModel):
    date: date
    total: int
    succeeded: int
    failed: int
    average_duration_ms: int | None


class RecentRequest(BaseModel):
    id: uuid.UUID
    created_at: datetime
    mode: str
    profile_name: str | None
    model: str | None
    duration_ms: int
    succeeded: bool
    error_code: str | None

    model_config = {"from_attributes": True}


class ActivitySummary(BaseModel):
    total_7d: int
    succeeded_7d: int
    failed_7d: int
    average_duration_ms: int | None
    daily: list[DailyUsage]
    recent: list[RecentRequest]


class DashboardResponse(BaseModel):
    setup: SetupSummary
    activity: ActivitySummary


@router.get("", response_model=DashboardResponse)
async def dashboard(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    retry_after = await get_dashboard_rate_limiter().try_acquire(user_id)
    if retry_after is not None:
        seconds = max(1, ceil(retry_after))
        raise HTTPException(
            status_code=429,
            detail=f"Dashboard refresh limit reached. Try again in {seconds} seconds.",
            headers={"Retry-After": str(seconds)},
        )

    active = (
        await db.execute(
            select(models.VisionProfile.name, models.VisionProfile.model).where(
                models.VisionProfile.user_id == user_id,
                models.VisionProfile.is_active.is_(True),
            )
        )
    ).first()
    profile_count = await db.scalar(
        select(func.count()).select_from(models.VisionProfile).where(
            models.VisionProfile.user_id == user_id
        )
    )
    prompt_count = await db.scalar(
        select(func.count()).select_from(models.SystemPrompt).where(
            models.SystemPrompt.user_id == user_id
        )
    )
    mcp_configured = (
        await db.scalar(
            select(models.McpCredential.id)
            .where(
                models.McpCredential.user_id == user_id,
                models.McpCredential.revoked_at.is_(None),
            )
            .limit(1)
        )
        is not None
    )

    today = datetime.now(UTC).date()
    first_day = today - timedelta(days=6)
    since = datetime.combine(first_day, time.min, tzinfo=UTC)
    day_bucket = func.date_trunc("day", models.VisionRequestLog.created_at, "UTC")
    daily_rows = (
        await db.execute(
            select(
                day_bucket.label("day"),
                func.count().label("total"),
                func.count().filter(models.VisionRequestLog.succeeded).label("succeeded"),
                func.avg(models.VisionRequestLog.duration_ms).label("average_duration_ms"),
            )
            .where(
                models.VisionRequestLog.user_id == user_id,
                models.VisionRequestLog.created_at >= since,
            )
            .group_by(day_bucket)
            .order_by(day_bucket)
        )
    ).all()
    daily_by_date = {
        row.day.date(): (row.total, row.succeeded, row.average_duration_ms)
        for row in daily_rows
    }
    daily = []
    for offset in range(7):
        day = first_day + timedelta(days=offset)
        total, succeeded, average = daily_by_date.get(day, (0, 0, None))
        daily.append(
            DailyUsage(
                date=day,
                total=total,
                succeeded=succeeded,
                failed=total - succeeded,
                average_duration_ms=round(average) if average is not None else None,
            )
        )

    total_7d = sum(row.total for row in daily_rows)
    succeeded_7d = sum(row.succeeded for row in daily_rows)
    average_duration_ms = (
        round(
            sum(float(row.average_duration_ms) * row.total for row in daily_rows)
            / total_7d
        )
        if total_7d
        else None
    )
    recent_rows = (
        await db.scalars(
            select(models.VisionRequestLog)
            .where(models.VisionRequestLog.user_id == user_id)
            .order_by(models.VisionRequestLog.created_at.desc(), models.VisionRequestLog.id.desc())
            .limit(20)
        )
    ).all()

    return DashboardResponse(
        setup=SetupSummary(
            active_profile_name=active[0] if active else None,
            active_model=active[1] if active else None,
            profile_count=profile_count or 0,
            prompt_count=prompt_count or 0,
            mcp_configured=mcp_configured,
        ),
        activity=ActivitySummary(
            total_7d=total_7d,
            succeeded_7d=succeeded_7d,
            failed_7d=total_7d - succeeded_7d,
            average_duration_ms=average_duration_ms,
            daily=daily,
            recent=[RecentRequest.model_validate(row) for row in recent_rows],
        ),
    )
