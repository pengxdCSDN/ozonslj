from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_logistics_template_preview_api() -> None:
    content = (
        "template_id,fulfillment_type,warehouse_id,route_id,region_id,version,effective_from,"
        "effective_to,volumetric_divisor_cm3_per_kg,max_weight_g,base_fee_minor,"
        "additional_fee_minor,additional_step_g,fee_rate_bps,currency,source\n"
        "fbs-main,FBS,warehouse-1,route-main,all,v1,2026-08-20,,5000,1000,5000,0,0,0,RUB,manual\n"
    )
    response = TestClient(create_app()).post(
        "/v1/selection/profit-model/logistics-templates/preview",
        json={"content": content},
    )

    assert response.status_code == 200
    assert response.json()["templates"][0]["warehouse_id"] == "warehouse-1"
