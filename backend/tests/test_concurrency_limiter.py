"""Concurrency limiter tests (Decision #9, Architecture §14/§26): 3 concurrent
per user; 4th rejected; slot released after success, exception, and timeout."""

import asyncio
import uuid

import pytest

from app.services.concurrency_limiter import ConcurrencyLimitError, run_with_concurrency_limit


class TestConcurrencyLimiter:
    async def test_3_concurrent_4th_rejected(self):
        uid = uuid.uuid4()
        gates = [asyncio.Event() for _ in range(4)]

        async def hold(gate: asyncio.Event) -> str:
            await gate.wait()
            return "done"

        # occupy 3 slots
        t1 = asyncio.create_task(run_with_concurrency_limit(uid, lambda: hold(gates[0])))
        t2 = asyncio.create_task(run_with_concurrency_limit(uid, lambda: hold(gates[1])))
        t3 = asyncio.create_task(run_with_concurrency_limit(uid, lambda: hold(gates[2])))
        await asyncio.sleep(0.05)  # let them acquire

        with pytest.raises(ConcurrencyLimitError):
            await run_with_concurrency_limit(uid, lambda: hold(gates[3]))

        for g in gates[:3]:
            g.set()
        assert sorted(await asyncio.gather(t1, t2, t3)) == ["done"] * 3

    async def test_slot_released_after_success(self):
        uid = uuid.uuid4()
        await run_with_concurrency_limit(uid, lambda: _sleep_ret(0.01))
        # slot must be free again
        await run_with_concurrency_limit(uid, lambda: _sleep_ret(0.01))

    async def test_slot_released_after_exception(self):
        uid = uuid.uuid4()

        async def boom():
            raise RuntimeError("provider exploded")

        with pytest.raises(RuntimeError):
            await run_with_concurrency_limit(uid, boom)
        # slot must be free again
        await run_with_concurrency_limit(uid, lambda: _sleep_ret(0.01))

    async def test_slot_released_after_timeout(self):
        uid = uuid.uuid4()

        async def hang():
            await asyncio.sleep(5)

        task = asyncio.create_task(run_with_concurrency_limit(uid, hang))
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        # slot freed by cancellation (async with guarantees release)
        await run_with_concurrency_limit(uid, lambda: _sleep_ret(0.01))

    async def test_users_isolated(self):
        a, b = uuid.uuid4(), uuid.uuid4()
        gates = [asyncio.Event() for _ in range(4)]
        tasks = [
            asyncio.create_task(run_with_concurrency_limit(a, lambda g=g: _wait(g)))
            for g in gates[:3]
        ]
        await asyncio.sleep(0.05)
        # user b unaffected by a's full slots
        await run_with_concurrency_limit(b, lambda: _sleep_ret(0.01))
        for g in gates[:3]:
            g.set()
        await asyncio.gather(*tasks)


async def _sleep_ret(t: float) -> str:
    await asyncio.sleep(t)
    return "ok"


async def _wait(gate: asyncio.Event) -> str:
    await gate.wait()
    return "ok"
