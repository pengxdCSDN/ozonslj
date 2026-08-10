import asyncio

import pytest

from backend.app.application.sync_processes import run_scheduler_loop, run_worker_loop
from backend.app.config import Settings
from backend.app.sync_runtime import _build_handlers, _require_runtime_urls


def test_scheduler_loop_dispatches_until_stop() -> None:
    calls = 0
    stop = asyncio.Event()

    async def dispatch_once() -> int:
        nonlocal calls
        calls += 1
        if calls == 2:
            stop.set()
        return 0

    asyncio.run(run_scheduler_loop(dispatch_once, stop, interval_seconds=0.001))

    assert calls == 2


def test_worker_loop_processes_sequentially_until_stop() -> None:
    calls = 0
    stop = asyncio.Event()

    async def process_one() -> bool:
        nonlocal calls
        calls += 1
        if calls == 3:
            stop.set()
        return False

    asyncio.run(run_worker_loop(process_one, stop))

    assert calls == 3


def test_sync_runtime_requires_redis_even_outside_production() -> None:
    settings = Settings(
        app_env="test",
        database_url="postgresql://app:secret@postgres:5432/ozonslj",
        redis_url=None,
    )

    with pytest.raises(RuntimeError, match="REDIS_URL"):
        _require_runtime_urls(settings)


def test_live_worker_rejects_missing_real_handlers() -> None:
    settings = Settings(
        app_env="test",
        database_url="postgresql://app:secret@postgres:5432/ozonslj",
        redis_url="redis://redis:6379/0",
        ozon_mode="live",
    )

    with pytest.raises(RuntimeError, match="拒绝启动 Worker"):
        _build_handlers(settings)


def test_stub_worker_registers_all_supported_resource_handlers() -> None:
    settings = Settings(
        app_env="test",
        database_url="postgresql://app:secret@postgres:5432/ozonslj",
        redis_url="redis://redis:6379/0",
        ozon_mode="stub",
    )

    assert set(_build_handlers(settings)) == {"products", "stock", "orders", "postings"}
