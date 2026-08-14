from fastapi.testclient import TestClient

from backend.app.main import app


def test_seller_product_sync_preview_api() -> None:
    response = TestClient(app).post(
        "/v1/seller/products/sync-preview",
        json={"response": {"items": [], "total": 0}},
    )
    assert response.status_code == 200
    assert response.json()["source"] == "seller_api"
    assert response.json()["dry_run"] is True
