from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_sample_scope_api_exposes_uncertainty() -> None:
    response = TestClient(create_app()).post(
        "/v1/public-samples/scope",
        json={"records": [{"sampled_at": "2026-08-01T00:00:00Z", "title": "A"}]},
    )
    assert response.status_code == 200
    assert response.json()["sample_count"] == 1
    assert response.json()["estimated"] is True
    assert "review_count" in response.json()["missing_fields"]
