from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_validate_api_returns_separate_fulfillment_models() -> None:
    response = TestClient(create_app()).post(
        "/v1/selection/validate/run",
        json={
            "sku": "SKU-1",
            "selling_price_minor": 10000,
            "purchase_cost_minor": 3000,
            "logistics_cost_minor": 1000,
            "commission_minor": 1000,
            "ad_cost_minor": 500,
            "return_loss_minor": 200,
            "competitor_count": 2,
        },
    )
    assert response.status_code == 200
    assert response.json()["fbo"]["fulfillment_type"] == "FBO"
    assert response.json()["fbs"]["fulfillment_type"] == "FBS"
