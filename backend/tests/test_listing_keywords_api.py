from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_listing_keyword_api() -> None:
    response = TestClient(create_app()).post(
        "/v1/listing/keywords/normalize",
        json={
            "keyword": "  термос  ",
            "source": "operator_imported",
            "observed_at": "2026-08-01T00:00:00Z",
            "language": "RU",
            "layer": "core",
            "product_scope": "SKU-1",
        },
    )
    assert response.status_code == 200
    assert response.json()["keyword"] == "термос"
    assert response.json()["language"] == "ru"
