from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_readiness_probe
from backend.app.main import app


class FakeReadinessProbe:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    async def check(self) -> None:
        if self.error is not None:
            raise self.error


def test_service_reports_liveness() -> None:
    response = TestClient(app).get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_service_reports_readiness() -> None:
    app.dependency_overrides[get_readiness_probe] = lambda: FakeReadinessProbe()
    try:
        response = TestClient(app).get("/health/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_fails_closed_when_dependency_is_unavailable() -> None:
    app.dependency_overrides[get_readiness_probe] = lambda: FakeReadinessProbe(
        RuntimeError("database unavailable")
    )
    try:
        response = TestClient(app).get("/health/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "infrastructure_unavailable"
