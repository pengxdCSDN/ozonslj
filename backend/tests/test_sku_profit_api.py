from fastapi.testclient import TestClient

from backend.app.main import create_app


def _payload() -> dict[str, object]:
    return {
        "product_name": "测试商品",
        "category_id": "category-1",
        "skus": [
            {
                "sku_id": "sku-1",
                "selling_price_minor": 100000,
                "landed_cost_minor": 30000,
                "weight_g": 400,
                "length_mm": 100,
                "width_mm": 100,
                "height_mm": 100,
                "logistics_template_id": "fbs-default",
            }
        ],
        "commission_rules": [
            {
                "category_id": "category-1",
                "rate_bps": 1500,
                "trace": {
                    "version": "commission-v1",
                    "source": "manual",
                    "effective_at": "2026-08-20",
                },
            }
        ],
        "logistics_templates": [
            {
                "template_id": "fbs-default",
                "volumetric_divisor_cm3_per_kg": 5000,
                "bands": [{"max_chargeable_weight_g": 1000, "fee_minor": 5000}],
                "trace": {
                    "version": "logistics-v1",
                    "source": "manual",
                    "effective_at": "2026-08-20",
                },
            }
        ],
    }


def test_calculate_skus_api_returns_traceable_result() -> None:
    response = TestClient(create_app()).post(
        "/v1/selection/profit-model/calculate-skus", json=_payload()
    )

    assert response.status_code == 200
    result = response.json()[0]
    assert result["sku_id"] == "sku-1"
    assert result["commission_trace"]["version"] == "commission-v1"
    assert result["algorithm_version"] == "sku-profit-v1"


def test_calculate_skus_api_returns_actionable_rule_error() -> None:
    payload = _payload()
    payload["commission_rules"] = [
        {
            "category_id": "other",
            "rate_bps": 1500,
            "trace": {
                "version": "commission-v1",
                "source": "manual",
                "effective_at": "2026-08-20",
            },
        }
    ]

    response = TestClient(create_app()).post(
        "/v1/selection/profit-model/calculate-skus", json=payload
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "profit_calculation_invalid"
