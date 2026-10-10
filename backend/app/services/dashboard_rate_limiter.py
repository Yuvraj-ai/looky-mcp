"""Per-user in-memory token bucket for dashboard reads."""

import asyncio
import time
import uuid

CAPACITY = 2
REFILL_RATE = 1 / 30  # tokens per second


class DashboardRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[uuid.UUID, tuple[float, float]] = {}
        self._lock = asyncio.Lock()

    async def try_acquire(self, user_id: uuid.UUID) -> float | None:
        """Spend one token, or return seconds until one token is available."""
        now = time.monotonic()
        async with self._lock:
            tokens, updated_at = self._buckets.get(user_id, (CAPACITY, now))
            tokens = min(CAPACITY, tokens + (now - updated_at) * REFILL_RATE)
            if tokens < 1:
                self._buckets[user_id] = (tokens, now)
                return (1 - tokens) / REFILL_RATE
            self._buckets[user_id] = (tokens - 1, now)
            return None


# shortcut: process-local state resets on restart; use shared storage for cross-worker limits.
_limiter = DashboardRateLimiter()


def get_dashboard_rate_limiter() -> DashboardRateLimiter:
    return _limiter
