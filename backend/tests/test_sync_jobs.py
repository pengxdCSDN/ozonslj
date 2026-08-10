from datetime import UTC, datetime

from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_store_workspace_gateway, get_sync_job_gateway
from backend.app.domain.store_workspace import StoreWorkspace
from backend.app.domain.sync_job import SyncJob, SyncJobPage, SyncResourceType
from backend.app.main import create_app


def _job() -> SyncJob:
    now = datetime.now(UTC)
    return SyncJob(
        id="sync-1", workspace_id="store-1", resource_type="stock", status="queued",
        processed_count=0, failure_count=0, attempt_count=0, max_attempts=3,
        next_attempt_at=now, created_at=now,
    )


class StubJobs:
    async def create_sync_job(
        self, *, workspace_id: str, resource_type: SyncResourceType, idempotency_key: str
    ) -> SyncJob:
        del workspace_id, resource_type, idempotency_key
        return _job()

    async def get_sync_job(self, job_id: str) -> SyncJob | None:
        return _job() if job_id == "sync-1" else None

    async def list_sync_jobs(
        self, *, workspace_id: str, cursor: str | None, limit: int
    ) -> SyncJobPage:
        del workspace_id, cursor, limit
        return SyncJobPage(items=[_job()], total=1)

    async def request_cancel_sync_job(self, *, job_id: str) -> bool:
        return job_id == "sync-1"

    async def retry_sync_job(self, *, job_id: str) -> SyncJob | None:
        return _job() if job_id == "sync-1" else None


class StubWorkspaces:
    async def get_workspace(self, workspace_id: str) -> StoreWorkspace | None:
        if workspace_id == "missing":
            return None
        now = datetime.now(UTC)
        return StoreWorkspace(
            id=workspace_id, display_name="测试工作区", status="active", verified_at=now,
            created_at=now, updated_at=now,
        )


def _client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_sync_job_gateway] = StubJobs
    app.dependency_overrides[get_store_workspace_gateway] = StubWorkspaces
    return TestClient(app)


def test_create_and_get_persisted_sync_job() -> None:
    client = _client()
    created = client.post(
        "/v1/store-workspaces/store-1/sync-jobs",
        headers={"Idempotency-Key": "stock-sync-001"},
        json={"resource_type": "stock"},
    )
    fetched = client.get("/v1/sync-jobs/sync-1")

    assert created.status_code == 202
    assert created.headers["location"] == "/v1/sync-jobs/sync-1"
    assert created.headers["retry-after"] == "2"
    assert created.headers["cache-control"] == "no-store"
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "queued"


def test_create_requires_idempotency_key_and_known_resource() -> None:
    client = _client()
    assert client.post(
        "/v1/store-workspaces/store-1/sync-jobs", json={"resource_type": "stock"}
    ).status_code == 422


def test_list_sync_jobs_returns_workspace_history() -> None:
    client = _client()

    response = client.get("/v1/store-workspaces/store-1/sync-jobs?limit=20")

    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == "sync-1"
    assert response.json()["total"] == 1
    assert response.headers["cache-control"] == "no-store"


def test_list_sync_jobs_rejects_invalid_cursor_and_limit() -> None:
    client = _client()

    assert client.get("/v1/store-workspaces/store-1/sync-jobs?cursor=abc").status_code == 422
    assert client.get("/v1/store-workspaces/store-1/sync-jobs?limit=101").status_code == 422


def test_missing_workspace_is_not_exposed_as_task_history() -> None:
    response = _client().get("/v1/store-workspaces/missing/sync-jobs")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "workspace_not_found"


def test_cancel_and_retry_responses_are_not_cacheable() -> None:
    client = _client()

    cancelled = client.post("/v1/sync-jobs/sync-1/cancel")
    retried = client.post("/v1/sync-jobs/sync-1/retry")

    assert cancelled.headers["cache-control"] == "no-store"
    assert retried.headers["cache-control"] == "no-store"


def test_cancel_and_retry_return_latest_task_fact() -> None:
    client = _client()

    cancelled = client.post("/v1/sync-jobs/sync-1/cancel")
    retried = client.post("/v1/sync-jobs/sync-1/retry")

    assert cancelled.status_code == 200
    assert retried.status_code == 200
    assert retried.json()["id"] == "sync-1"


def test_cancel_unknown_task_is_rejected() -> None:
    client = _client()

    response = client.post("/v1/sync-jobs/unknown/cancel")

    assert response.status_code == 409
    assert client.post("/v1/sync-jobs/unknown/retry").status_code == 409
    assert client.post(
        "/v1/store-workspaces/store-1/sync-jobs",
        headers={"Idempotency-Key": "invalid-resource"},
        json={"resource_type": "finance"},
    ).status_code == 422


def test_cancel_and_retry_advertise_follow_up_polling() -> None:
    client = _client()

    cancelled = client.post("/v1/sync-jobs/sync-1/cancel")
    retried = client.post("/v1/sync-jobs/sync-1/retry")

    assert cancelled.headers["retry-after"] == "2"
    assert retried.headers["location"] == "/v1/sync-jobs/sync-1"
    assert retried.headers["retry-after"] == "2"


def test_unknown_sync_job_read_returns_not_found() -> None:
    response = _client().get("/v1/sync-jobs/unknown")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "sync_job_not_found"
