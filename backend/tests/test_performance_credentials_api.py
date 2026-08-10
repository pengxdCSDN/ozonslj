from fastapi.testclient import TestClient

from backend.app.main import app


def test_performance_credentials_api_does_not_echo_token() -> None:
    response = TestClient(app).post(
        "/v1/performance/credentials/inspect",
        json={"client_id": "client", "refresh_token": "secret"},
    )
    assert response.status_code == 200
    assert response.json()["refresh_token_present"] is True
    assert "secret" not in response.text
