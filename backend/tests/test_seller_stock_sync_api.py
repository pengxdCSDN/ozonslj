from fastapi.testclient import TestClient

from backend.app.main import app


def test_seller_stock_sync_preview_api() -> None:
    response = TestClient(app).post(
        "/v1/seller/stock/sync-preview",
        json={"response": {"items": [], "total": 0}},
    )
    assert response.status_code == 200
    assert response.json()["source"] == "seller_api"


def test_seller_stock_sync_preview_api_rejects_duplicate_snapshot() -> None:
    row = {
        "offer_id": "SKU", "warehouse_id": "WH",
        "available_quantity": 1, "reserved_quantity": 0,
    }
    response = TestClient(app).post(
        "/v1/seller/stock/sync-preview", json={"response": {"items": [row, row]}},
    )
    assert response.status_code == 422
