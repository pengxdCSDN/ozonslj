"""RAG Worker 的任务租约、并发边界和可恢复状态机。"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Literal

WorkerTaskStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]


@dataclass(frozen=True, slots=True)
class RagWorkerTask:
    task_id: str
    task_type: str
    organization_id: str
    status: WorkerTaskStatus = "queued"
    attempt: int = 0
    lease_until: datetime | None = None
    error_code: str | None = None


class RagWorkerQueue:
    """单进程内的确定性队列替身；生产环境可由 Redis/DB 队列适配。"""

    def __init__(self, *, max_concurrency: int = 1, lease_seconds: int = 300) -> None:
        if max_concurrency < 1 or lease_seconds < 1:
            raise ValueError("Worker 并发和租约时间必须为正数")
        self._max_concurrency = max_concurrency
        self._lease_seconds = lease_seconds
        self._tasks: dict[str, RagWorkerTask] = {}

    def enqueue(self, task: RagWorkerTask) -> RagWorkerTask:
        if task.task_id in self._tasks:
            return self._tasks[task.task_id]
        self._tasks[task.task_id] = task
        return task

    def claim(self, *, organization_id: str, now: datetime | None = None) -> RagWorkerTask | None:
        current = now or datetime.now(UTC)
        active = sum(task.status == "running" for task in self._tasks.values())
        if active >= self._max_concurrency:
            return None
        for task in self._tasks.values():
            lease_expired = task.lease_until is not None and task.lease_until <= current
            if task.organization_id == organization_id and (
                task.status == "queued" or (task.status == "running" and lease_expired)
            ):
                claimed = replace(
                    task, status="running", attempt=task.attempt + 1,
                    lease_until=current + timedelta(seconds=self._lease_seconds),
                )
                self._tasks[task.task_id] = claimed
                return claimed
        return None

    def finish(
        self, task_id: str, *, status: WorkerTaskStatus, error_code: str | None = None
    ) -> RagWorkerTask:
        task = self._tasks[task_id]
        if task.status != "running":
            raise ValueError("只有 running 任务可以结束")
        finished = replace(task, status=status, lease_until=None, error_code=error_code)
        self._tasks[task_id] = finished
        return finished

    def get(self, task_id: str) -> RagWorkerTask:
        return self._tasks[task_id]

    def list(self, *, organization_id: str | None = None) -> tuple[RagWorkerTask, ...]:
        """按组织读取任务快照；返回不可变副本，避免 API 修改队列内部状态。"""

        tasks = tuple(self._tasks.values())
        if organization_id is None:
            return tasks
        return tuple(task for task in tasks if task.organization_id == organization_id)
