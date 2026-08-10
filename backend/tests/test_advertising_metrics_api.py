from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_advertising_metrics_api_returns_formula_fields() -> None:
    response = TestClient(create_app()).post(
        "/v1/advertising/metrics/calculate",
        json={
            "impressions": 100,
            "clicks": 10,
            "orders": 2,
            "ad_sales_minor": 5000,
            "total_sales_minor": 10000,
            "spend_minor": 1000,
            "currency": "RUB",
            "window": "day",
        },
    )
    assert response.status_code == 200
    assert response.json()["acos_percent"] == 20.0
    assert response.json()["currency"] == "RUB"
