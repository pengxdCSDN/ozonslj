from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_rag_task_gateway, get_rag_task_queue
from backend.app.api.routes.knowledge_tasks import router
from backend.app.domain.rag_worker import RagWorkerTask


class FakeRagGateway:
    def __init__(self) -> None:
        self.tasks: dict[str, RagWorkerTask] = {}

    async def create(self, task_type: str, idempotency_key: str, source_id: str,
                     document_version_id: str) -> RagWorkerTask:
        task = next(
            (task for task in self.tasks.values() if task.error_code == idempotency_key), None
        )
        if task is None:
            task = RagWorkerTask(idempotency_key, task_type, "org-1", error_code=idempotency_key)
            self.tasks[task.task_id] = task
        return task

    async def list_tasks(self) -> list[RagWorkerTask]:
        return list(self.tasks.values())

    async def claim(self, task_id: str, worker_id: str, lease_seconds: int) -> RagWorkerTask | None:
        task = self.tasks[task_id]
        claimed = RagWorkerTask(task.task_id, task.task_type, task.organization_id, "running", 1)
        self.tasks[task_id] = claimed
        return claimed

    async def finish(
        self, task_id: str, status: str, error_code: str | None = None
    ) -> RagWorkerTask:
        task = self.tasks[task_id]
        finished = RagWorkerTask(
            task.task_id, task.task_type, task.organization_id, status,
            task.attempt, None, error_code,
        )
        self.tasks[task_id] = finished
        return finished

    async def cancel(self, task_id: str) -> RagWorkerTask:
        task = self.tasks[task_id]
        cancelled = RagWorkerTask(
            task.task_id, task.task_type, task.organization_id, "cancelled",
            task.attempt, None, "cancelled_by_operator",
        )
        self.tasks[task_id] = cancelled
        return cancelled

    async def retry(self, task_id: str) -> RagWorkerTask:
        task = self.tasks[task_id]
        retried = RagWorkerTask(
            task.task_id, task.task_type, task.organization_id, "queued",
            task.attempt, None, None,
        )
        self.tasks[task_id] = retried
        return retried


class FakeRagQueue:
    async def enqueue(self, task_id: str) -> None:
        return None


def test_task_is_idempotent_claimed_and_finished() -> None:
    app = FastAPI()
    app.include_router(router)
    fake_gateway = FakeRagGateway()
    app.dependency_overrides[get_rag_task_gateway] = lambda: fake_gateway
    app.dependency_overrides[get_rag_task_queue] = FakeRagQueue
    client = TestClient(app)
    created = client.post(
        "/v1/knowledge-tasks",
        json={
            "task_type": "index", "organization_id": "org-1", "source_id": "source-1",
            "document_version_id": "version-1", "idempotency_key": "task-1",
        },
    )
    task_id = created.json()["task_id"]
    listed = client.get("/v1/knowledge-tasks?organization_id=org-1")
    assert listed.status_code == 200
    assert listed.json()[0]["task_id"] == task_id
    claimed = client.post(f"/v1/knowledge-tasks/{task_id}/claim?organization_id=org-1")
    assert claimed.json()["status"] == "running"
    finished = client.post(
        f"/v1/knowledge-tasks/{task_id}/finish", json={"status": "succeeded"}
    )
    assert finished.json()["status"] == "succeeded"


def test_task_can_be_cancelled_and_retried() -> None:
    app = FastAPI()
    app.include_router(router)
    fake_gateway = FakeRagGateway()
    app.dependency_overrides[get_rag_task_gateway] = lambda: fake_gateway
    app.dependency_overrides[get_rag_task_queue] = FakeRagQueue
    client = TestClient(app)
    created = client.post(
        "/v1/knowledge-tasks",
        json={
            "task_type": "index", "organization_id": "org-1", "source_id": "s",
            "document_version_id": "v", "idempotency_key": "task-cancel",
        },
    )
    task_id = created.json()["task_id"]
    assert client.post(f"/v1/knowledge-tasks/{task_id}/cancel").json()["status"] == "cancelled"
    assert client.post(f"/v1/knowledge-tasks/{task_id}/retry").json()["status"] == "queued"
