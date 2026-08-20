"""说明本模块的职责、边界和主要协作对象。"""

import asyncio
from collections.abc import Awaitable, Callable


async def run_scheduler_loop(
    dispatch_once: Callable[[], Awaitable[int]],
    stop: asyncio.Event,
    *,
    interval_seconds: float,
) -> None:
    """持续分发到期任务，并允许关闭信号立即打断空闲等待。"""
    while not stop.is_set():
        await dispatch_once()
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval_seconds)
        except TimeoutError:
            continue


async def run_worker_loop(
    process_one: Callable[[], Awaitable[bool]],
    stop: asyncio.Event,
) -> None:
    """单并发消费同步任务；Consumer 自身的阻塞读取负责限制空轮询频率。"""
    while not stop.is_set():
        await process_one()
