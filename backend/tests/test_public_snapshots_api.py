from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_public_snapshot_normalize_api() -> None:
    response = TestClient(create_app()).post(
        "/v1/public-snapshots/normalize",
        json={
            "url": "https://example.com/item",
            "price_minor": 1299,
            "rating": "4.8",
            "review_count": 3,
        },
    )
    assert response.status_code == 200
    assert response.json()["price_minor"] == 1299
    assert response.json()["estimated"] is True
