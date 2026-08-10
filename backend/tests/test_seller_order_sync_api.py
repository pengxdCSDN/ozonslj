from fastapi.testclient import TestClient

from backend.app.main import app


def test_seller_order_sync_preview_api() -> None:
    response = TestClient(app).post(
        "/v1/seller/orders/sync-preview",
        json={"response": {"items": [], "total": 0}},
    )
    assert response.status_code == 200
    assert response.json()["source"] == "seller_api"


def test_seller_order_sync_preview_api_rejects_duplicate_order() -> None:
    row = {
        "order_id": "O-1", "ordered_at": "2026-08-09T10:00:00Z", "status": "new",
        "total_amount_minor": 1, "currency": "RUB", "item_count": 1,
    }
    response = TestClient(app).post(
        "/v1/seller/orders/sync-preview", json={"response": {"items": [row, row]}},
    )
    assert response.status_code == 422
