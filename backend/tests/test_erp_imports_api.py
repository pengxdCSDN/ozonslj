from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_erp_csv_preview_api_returns_normalized_records() -> None:
    content = (
        "external_id,offer_id,record_type,quantity,amount_minor,currency,expected_date\n"
        "PO-1,SKU-1,inbound,3,1000,rub,2026-08-20\n"
    )
    response = TestClient(create_app()).post("/v1/erp/csv/preview", json={"content": content})
    assert response.status_code == 200
    assert response.json()[0]["currency"] == "RUB"


def test_erp_csv_preview_api_rejects_duplicate_external_id() -> None:
    content = (
        "external_id,offer_id,record_type,quantity\n"
        "PO-1,SKU-1,inbound,3\n"
        "PO-1,SKU-1,inbound,3\n"
    )
    response = TestClient(create_app()).post("/v1/erp/csv/preview", json={"content": content})
    assert response.status_code == 422
