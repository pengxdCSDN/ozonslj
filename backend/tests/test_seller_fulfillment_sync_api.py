from fastapi.testclient import TestClient

from backend.app.main import app


def test_seller_fulfillment_sync_preview_api() -> None:
    response = TestClient(app).post(
        "/v1/seller/fulfillment/sync-preview",
        json={"response": {"items": [], "total": 0}},
    )
    assert response.status_code == 200
    assert response.json()["dry_run"] is True


def test_seller_fulfillment_sync_preview_api_rejects_duplicate_posting() -> None:
    row = {
        "posting_id": "P-1", "fulfillment_type": "FBS", "status": "created",
        "shipment_date": None, "item_count": 1, "total_quantity": 1,
    }
    response = TestClient(app).post(
        "/v1/seller/fulfillment/sync-preview", json={"response": {"items": [row, row]}},
    )
    assert response.status_code == 422
