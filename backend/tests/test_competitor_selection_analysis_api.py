from fastapi.testclient import TestClient

from backend.app.main import app


def test_competitor_selection_analysis_api_returns_recommendation() -> None:
    response = TestClient(app).post(
        "/v1/analysis/competitor-selection/analyze",
        json={
            "sample_count": 2, "opportunity_count": 1,
            "median_price_minor": 2500, "top_competitor_rating": 4.5,
            "source_window": "2026-08",
        },
    )
    assert response.status_code == 200
    assert response.json()["estimated"] is True
    assert response.json()["recommendations"]
