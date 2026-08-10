from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_freshness_api_marks_fresh_data() -> None:
    response = TestClient(create_app()).post(
        "/v1/review/freshness/check",
        json={
            "data_domain": "seller_product",
            "observed_at": "2026-08-09T00:00:00Z",
            "max_age_seconds": 3600,
            "now": "2026-08-09T00:30:00Z",
        },
    )
    assert response.status_code == 200
    assert response.json()["fresh"] is True
