from fastapi.testclient import TestClient

from backend.app.main import app


def test_summary_report_api_returns_todos() -> None:
    response = TestClient(app).post(
        "/v1/reports/summary",
        json={
            "report_type": "daily", "period": "2026-08-09",
            "sales_change_percent": -25, "stockout_risk_count": 1,
            "advertising_anomaly_count": 0, "opportunity_count": 0,
        },
    )
    assert response.status_code == 200
    assert response.json()["todos"]
