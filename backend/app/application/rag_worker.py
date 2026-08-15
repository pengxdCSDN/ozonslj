"""RAG 任务 Worker；任务事实来自 PostgreSQL，Redis 只负责唤醒。"""

from __future__ import annotations

import asyncio
from contextlib import suppress

from backend.app.domain.knowledge_runtime import KnowledgeRuntimePort, get_knowledge_runtime
from backend.app.infrastructure.postgresql.rag_tasks import PostgresRagTaskGateway
from backend.app.infrastructure.redis_rag_tasks import RedisRagTaskConsumer


class RagWorker:
    def __init__(self, tasks: PostgresRagTaskGateway, consumer: RedisRagTaskConsumer,
                 *, worker_id: str, lease_seconds: int = 300,
                 runtime: KnowledgeRuntimePort | None = None) -> None:
        self._tasks = tasks
        self._consumer = consumer
        self._worker_id = worker_id
        self._lease_seconds = lease_seconds
        self._runtime = runtime

    async def process_one(self, *, block_ms: int = 1_000) -> bool:
        message = await self._consumer.read_one(block_ms=block_ms)
        if message is None:
            return False
        message_id, task_id = message
        task = await self._tasks.claim(task_id, self._worker_id, self._lease_seconds)
        if task is None:
            await self._consumer.acknowledge(message_id)
            return True
        details = await self._tasks.details(task_id)
        heartbeat = asyncio.create_task(self._heartbeat(task_id))
        try:
            if details is None or details[2] is None:
                raise ValueError("rag_task_version_missing")
            runtime = self._runtime or get_knowledge_runtime()
            if task.task_type == "index":
                await runtime.publish(details[2])
            elif task.task_type == "withdraw":
                await runtime.withdraw(details[2])
            elif task.task_type in {"delete", "rebuild"}:
                await runtime.delete(details[2])
            else:
                raise ValueError("rag_task_type_not_supported")
        except ValueError as error:
            finished = await self._tasks.finish(task_id, "failed", str(error))
        except RuntimeError as error:
            finished = await self._tasks.finish(task_id, "failed", str(error)[:100])
        except Exception:
            finished = await self._tasks.finish(task_id, "failed", "rag_task_failed")
        else:
            finished = await self._tasks.finish(task_id, "succeeded")
        finally:
            heartbeat.cancel()
            with suppress(asyncio.CancelledError):
                await heartbeat
        if finished is not None:
            await self._consumer.acknowledge(message_id)
        return finished is not None

    async def _heartbeat(self, task_id: str) -> None:
        interval = max(1, self._lease_seconds // 3)
        while True:
            await asyncio.sleep(interval)
            if not await self._tasks.heartbeat(task_id, self._worker_id, self._lease_seconds):
                return
