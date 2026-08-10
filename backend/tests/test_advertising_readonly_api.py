from fastapi.testclient import TestClient

from backend.app.main import app


def test_advertising_boundary_api_rejects_budget_write() -> None:
    response = TestClient(app).post(
        "/v1/advertising/boundary/check", json={"action": "change_budget"}
    )
    assert response.status_code == 200
    assert response.json()["allowed"] is False
    assert response.json()["audit_required"] is True
