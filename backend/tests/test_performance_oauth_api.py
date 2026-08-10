from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_performance_oauth_api_does_not_echo_refresh_token() -> None:
    response = TestClient(create_app()).post(
        "/v1/advertising/performance-oauth/inspect",
        json={
            "access_token": "perf-token",
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            "refresh_token": "secret-refresh",
        },
    )
    assert response.status_code == 200
    assert "secret-refresh" not in response.text
    assert response.json()["credential_scope"] == "performance_api"
