from datetime import UTC, datetime

from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_current_user, get_sync_job_gateway
from backend.app.domain.identity import AuthenticatedUser
from backend.app.domain.sync_job import SyncJob, SyncJobAlreadyActiveError
from backend.app.main import app


class _SyncJobGateway:
    def __init__(self, *, conflict: bool = False) -> None:
        self.conflict = conflict
        self.requested_by: str | None = None

    async def create_sync_job(
        self,
        *,
        workspace_id: str,
        resource_type: str,
        sync_mode: str,
        requested_by: str,
    ) -> SyncJob:
        if self.conflict:
            raise SyncJobAlreadyActiveError(workspace_id)
        self.requested_by = requested_by
        return SyncJob(
            id="sync_1",
            workspace_id=workspace_id,
            resource_type=resource_type,
            sync_mode=sync_mode,
            status="queued",
            created_at=datetime(2026, 8, 4, tzinfo=UTC),
        )


def _user(*, workspace_ids: tuple[str, ...] = ("local",)) -> AuthenticatedUser:
    return AuthenticatedUser(
        id="operator-1",
        email="operator@example.com",
        display_name="Operator",
        role="operator",
        workspace_ids=workspace_ids,
    )


def test_create_sync_job_returns_queued_job() -> None:
    gateway = _SyncJobGateway()
    app.dependency_overrides[get_sync_job_gateway] = lambda: gateway
    app.dependency_overrides[get_current_user] = lambda: _user()
    try:
        response = TestClient(app).post(
            "/v1/store-workspaces/local/sync-jobs",
            json={"resource_type": "products"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["status"] == "queued"
    assert response.json()["sync_mode"] == "incremental"
    assert gateway.requested_by == "operator-1"


def test_create_sync_job_rejects_unauthorized_workspace() -> None:
    app.dependency_overrides[get_sync_job_gateway] = _SyncJobGateway
    app.dependency_overrides[get_current_user] = lambda: _user(workspace_ids=())
    try:
        response = TestClient(app).post(
            "/v1/store-workspaces/other/sync-jobs",
            json={"resource_type": "products"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


def test_create_sync_job_reports_active_job_conflict() -> None:
    app.dependency_overrides[get_sync_job_gateway] = lambda: _SyncJobGateway(conflict=True)
    app.dependency_overrides[get_current_user] = lambda: _user()
    try:
        response = TestClient(app).post(
            "/v1/store-workspaces/local/sync-jobs",
            json={"resource_type": "stocks", "sync_mode": "reconcile"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    assert "已有同步任务" in response.json()["detail"]
