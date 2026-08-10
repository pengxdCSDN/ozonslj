from fastapi.testclient import TestClient

from backend.app.main import app


def test_notification_api_returns_preview_configuration() -> None:
    response = TestClient(app).post(
        "/v1/notifications/validate",
        json={"channel": "email", "template": "{{headline}}", "retry_limit": 2},
    )
    assert response.status_code == 200
    assert response.json()["preview_only"] is True
