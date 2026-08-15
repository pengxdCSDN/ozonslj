import pytest

from backend.app.application.rag_worker import RagWorker
from backend.app.domain.rag_worker import RagWorkerTask


class FakeTasks:
    def __init__(self) -> None:
        self.task = RagWorkerTask("task-1", "index", "org-1")
        self.finished: str | None = None

    async def claim(self, task_id: str, worker_id: str, lease_seconds: int) -> RagWorkerTask:
        self.task = RagWorkerTask(task_id, "index", "org-1", "running", 1)
        return self.task

    async def details(self, task_id: str) -> tuple[RagWorkerTask, str, str]:
        return self.task, "source-1", "version-1"

    async def finish(
        self, task_id: str, status: str, error_code: str | None = None
    ) -> RagWorkerTask:
        self.finished = status
        return RagWorkerTask(task_id, "index", "org-1", status, 1, None, error_code)

    async def heartbeat(self, task_id: str, worker_id: str, lease_seconds: int) -> bool:
        return True


class FakeConsumer:
    def __init__(self) -> None:
        self.acked: str | None = None

    async def read_one(self, *, block_ms: int) -> tuple[str, str]:
        return "message-1", "task-1"

    async def acknowledge(self, message_id: str) -> None:
        self.acked = message_id


class FakeRuntime:
    persistent = True
    organization_id = "org-1"

    def __init__(self) -> None:
        self.published: list[str] = []

    async def publish(self, version_id: str) -> int:
        self.published.append(version_id)
        return 1


@pytest.mark.asyncio
async def test_worker_publishes_and_acknowledges_persistent_task() -> None:
    tasks = FakeTasks()
    consumer = FakeConsumer()
    runtime = FakeRuntime()
    worker = RagWorker(tasks, consumer, worker_id="worker-1", runtime=runtime)

    assert await worker.process_one(block_ms=1) is True
    assert runtime.published == ["version-1"]
    assert tasks.finished == "succeeded"
    assert consumer.acked == "message-1"
