import time
import uuid

import pytest
from fastapi import HTTPException

from app.services.dashboard_rate_limiter import CAPACITY, DashboardRateLimiter


@pytest.fixture
def limiter() -> DashboardRateLimiter:
    return DashboardRateLimiter()


async def test_bucket_never_exceeds_capacity_and_refills(limiter, monkeypatch):
    now = time.monotonic()
    clock = {"now": now}
    monkeypatch.setattr(time, "monotonic", lambda: clock["now"])
    user_id = uuid.uuid4()

    for _ in range(CAPACITY):
        assert await limiter.try_acquire(user_id) is None

    retry_after = await limiter.try_acquire(user_id)
    assert retry_after == pytest.approx(30)

    clock["now"] += 30
    assert await limiter.try_acquire(user_id) is None
    assert await limiter.try_acquire(user_id) == pytest.approx(30)


async def test_bucket_is_per_user(limiter):
    user_a, user_b = uuid.uuid4(), uuid.uuid4()
    for _ in range(CAPACITY):
        assert await limiter.try_acquire(user_a) is None
    assert await limiter.try_acquire(user_a) is not None
    assert await limiter.try_acquire(user_b) is None


async def test_limited_dashboard_request_is_rejected_before_database_access(limiter, monkeypatch):
    from app.api import dashboard as dashboard_module

    user_id = uuid.uuid4()
    for _ in range(CAPACITY):
        await limiter.try_acquire(user_id)
    monkeypatch.setattr(dashboard_module, "get_dashboard_rate_limiter", lambda: limiter)

    with pytest.raises(HTTPException) as exc_info:
        await dashboard_module.dashboard(user_id=user_id, db=None)

    assert exc_info.value.status_code == 429
    assert "Retry-After" in exc_info.value.headers
