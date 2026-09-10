"""Per-user concurrency limiter (Architecture §14): max 3 concurrent vision
calls; 4th rejected (no queue); slot released in finally on all outcomes."""

import asyncio
import uuid
from collections import defaultdict
from collections.abc import Awaitable, Callable

MAX_CONCURRENT = 3


class ConcurrencyLimitError(Exception):
    """Stable message per Decision #5/§13."""

    def __init__(self) -> None:
        super().__init__("Too many concurrent vision calls")


_semaphores: dict[uuid.UUID, asyncio.Semaphore] = defaultdict(
    lambda: asyncio.Semaphore(MAX_CONCURRENT)
)


async def run_with_concurrency_limit[T](
    user_id: uuid.UUID, coro_factory: Callable[[], Awaitable[T]]
) -> T:
    sem = _semaphores[user_id]
    if sem.locked():  # all slots taken — reject instead of queueing (Decision #9)
        raise ConcurrencyLimitError()
    async with sem:  # releases on success, exception, cancellation alike
        return await coro_factory()
