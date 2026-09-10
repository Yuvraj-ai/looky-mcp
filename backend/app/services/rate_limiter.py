"""Sliding-window rate limiter (Architecture §15): 20 calls / rolling 60s / user.
In-memory deque per user; per-process state accepted per Decision #9."""

import asyncio
import time
import uuid
from collections import defaultdict, deque

MAX_CALLS = 20
WINDOW_SECONDS = 60.0


class RateLimitError(Exception):
    """Stable message per Decision #5/§13."""

    def __init__(self) -> None:
        super().__init__("Vision call rate limit reached")


class RateLimiter:
    def __init__(self, max_calls: int = MAX_CALLS, window_seconds: float = WINDOW_SECONDS):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._calls: dict[uuid.UUID, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, user_id: uuid.UUID) -> None:
        now = time.monotonic()
        async with self._lock:
            dq = self._calls[user_id]
            while dq and now - dq[0] > self.window_seconds:
                dq.popleft()
            if len(dq) >= self.max_calls:
                raise RateLimitError()
            dq.append(now)
