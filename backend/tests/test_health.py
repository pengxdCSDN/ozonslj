from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_readiness_probe
from backend.app.main import app


class _HealthyProbe:
    async def check(self) -> None:
        return None


class _UnhealthyProbe:
    async def check(self) -> None:
        raise ConnectionError


def test_service_reports_liveness() -> None:
    response = TestClient(app).get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_service_reports_readiness() -> None:
    app.dependency_overrides[get_readiness_probe] = _HealthyProbe
    try:
        response = TestClient(app).get("/health/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_service_reports_unavailable_dependency() -> None:
    app.dependency_overrides[get_readiness_probe] = _UnhealthyProbe
    try:
        response = TestClient(app).get("/health/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
