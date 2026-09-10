---
name: services-limiters
status: done
depends_on: []
implements: Decision #9, Architecture §14/§15
related_files: backend/app/services/rate_limiter.py, backend/app/services/concurrency_limiter.py, backend/tests/test_rate_limiter.py, backend/tests/test_concurrency_limiter.py
---

## What this is
In-memory, per-user limiters: sliding-window 20/60s (deque + asyncio.Lock) and 3-concurrent (per-user asyncio.Semaphore, reject-if-would-block, release-on-all-outcomes).

## Current state
Complete. 9 tests (20/21 boundary, per-user isolation, window sliding incl. burst boundary, 3/4 concurrent, slot release after success/exception/cancellation, cross-user isolation).

## Key decisions made while building this
- Concurrency: `if sem.locked()` before `async with` — rejects instead of queueing (Decision #9 no-queue); `async with` guarantees release even on cancel.
- `defaultdict` lazily allocates per-user semaphore/deque — negligible memory, bounded (≤20 timestamps/user).
- Module-level singleton `_semaphores` (matches Architecture §14 sketch); per-process state accepted per Decision #9 — single uvicorn worker in deployment makes this exact.
- Tests monkeypatch `time.monotonic` for window math (no real 60s sleeps).

## Known gaps / TODO
- None.
