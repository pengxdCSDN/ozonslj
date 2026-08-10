from fastapi.testclient import TestClient

from backend.app.main import app


def test_sales_analysis_api_returns_comparison() -> None:
    response = TestClient(app).post(
        "/v1/analysis/sales/analyze",
        json={
            "current_sales_minor": 8000, "previous_sales_minor": 10000,
            "current_orders": 8, "previous_orders": 10,
            "current_window": "this-week", "previous_window": "last-week",
        },
    )
    assert response.status_code == 200
    assert response.json()["change_percent"] == -20
    assert response.json()["anomalies"]
