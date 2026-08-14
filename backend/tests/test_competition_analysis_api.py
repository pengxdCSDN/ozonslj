from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_competition_analysis_api() -> None:
    response = TestClient(create_app()).post(
        "/v1/selection/competition/analyze",
        json={
            "items": [
                {
                    "seller": "a",
                    "brand": "x",
                    "price_minor": 1000,
                    "rating": 4.5,
                    "review_count": 10,
                }
            ]
        },
    )
    assert response.status_code == 200
    assert response.json()["estimated"] is True
    assert response.json()["sample_count"] == 1
