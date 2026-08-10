from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_cost_sensitivity_api_returns_three_scenarios() -> None:
    response = TestClient(create_app()).post(
        "/v1/selection/cost-sensitivity/analyze",
        json={
            "selling_price_minor": 10000,
            "purchase_cost_minor": 3000,
            "logistics_cost_minor": 700,
            "commission_minor": 1000,
            "ad_cost_minor": 500,
            "return_loss_minor": 200,
        },
    )
    assert response.status_code == 200
    assert len(response.json()) == 3
