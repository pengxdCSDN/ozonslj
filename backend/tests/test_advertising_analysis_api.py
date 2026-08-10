from fastapi.testclient import TestClient

from backend.app.main import app


def test_advertising_analysis_api_returns_recommendations() -> None:
    response = TestClient(app).post(
        "/v1/analysis/advertising/analyze",
        json={
            "spend_minor": 3000, "ad_sales_minor": 10000, "total_sales_minor": 20000,
            "keyword_count": 10, "unconverted_keyword_count": 2, "acos_alert_percent": 20,
        },
    )
    assert response.status_code == 200
    assert response.json()["recommendations"]
