from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_profit_model_api_returns_two_fulfillment_scenarios() -> None:
    response = TestClient(create_app()).post(
        "/v1/selection/profit-model/calculate",
        json={
            "selling_price_minor": 10000,
            "purchase_cost_minor": 3000,
            "fbo_logistics_minor": 700,
            "fbs_logistics_minor": 1000,
            "commission_minor": 1000,
            "ad_cost_minor": 500,
            "return_loss_minor": 200,
        },
    )
    assert response.status_code == 200
    assert [item["fulfillment_type"] for item in response.json()] == ["FBO", "FBS"]
