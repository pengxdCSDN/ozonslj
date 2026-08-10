from fastapi.testclient import TestClient

from backend.app.main import app


def test_inventory_analysis_api_returns_overstock_signal() -> None:
    response = TestClient(app).post(
        "/v1/analysis/inventory/analyze",
        json={
            "available_units": 100, "inbound_units": 0,
            "average_daily_sales": 1, "safety_days": 7, "overstock_days": 60,
        },
    )
    assert response.status_code == 200
    assert response.json()["overstock_risk"] is True
