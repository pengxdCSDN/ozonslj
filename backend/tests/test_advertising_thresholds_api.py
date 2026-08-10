from fastapi.testclient import TestClient

from backend.app.main import app


def test_thresholds_api_returns_versioned_config() -> None:
    response = TestClient(app).post(
        "/v1/advertising/thresholds/validate",
        json={
            "version": 1, "min_impressions": 100, "min_clicks": 10,
            "high_cvr_percent": 8, "high_spend_minor": 1000,
        },
    )
    assert response.status_code == 200
    assert response.json()["version"] == 1
