"""Rate limiter tests (Decision #9, Architecture §15/§26): 20/60s rolling window.
20 allowed, 21st rejected; window slides after 60s."""

import time
import uuid

import pytest

from app.services.rate_limiter import RateLimiter, RateLimitError


@pytest.fixture
def limiter() -> RateLimiter:
    return RateLimiter()


class TestRateLimiter:
    async def test_20_allowed_21st_rejected(self, limiter):
        uid = uuid.uuid4()
        for _ in range(20):
            await limiter.check(uid)  # no error
        with pytest.raises(RateLimitError):
            await limiter.check(uid)

    async def test_independent_per_user(self, limiter):
        a, b = uuid.uuid4(), uuid.uuid4()
        for _ in range(20):
            await limiter.check(a)
        await limiter.check(b)  # other user unaffected

    async def test_window_slides(self, limiter, monkeypatch):
        uid = uuid.uuid4()
        base = time.monotonic()
        clock = {"now": base}
        monkeypatch.setattr(time, "monotonic", lambda: clock["now"])
        for _ in range(20):
            await limiter.check(uid)
        with pytest.raises(RateLimitError):
            await limiter.check(uid)
        clock["now"] = base + 60.1  # first call falls out of window
        await limiter.check(uid)  # allowed again

    async def test_burst_boundary_rejected(self, limiter, monkeypatch):
        """19 at t=0, 1 at t=59.9, next at t=60.05: the t=0 batch still partially
        in window — 20-in-window rule holds via sliding window."""
        uid = uuid.uuid4()
        base = time.monotonic()
        clock = {"now": base}
        monkeypatch.setattr(time, "monotonic", lambda: clock["now"])
        for _ in range(19):
            await limiter.check(uid)
        clock["now"] = base + 59.9
        await limiter.check(uid)  # 20th
        with pytest.raises(RateLimitError):
            await limiter.check(uid)
        clock["now"] = base + 60.05
        # the 19 calls at t=0 are now >60s old → gone; only t=59.9 remains
        await limiter.check(uid)
