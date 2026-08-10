from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_listing_fabe_api() -> None:
    response = TestClient(create_app()).post(
        "/v1/listing/fabe/generate",
        json={
            "product_name": "Термос",
            "points": [{
                "feature": "500 мл", "advantage": "удобный",
                "benefit": "для поездок", "copy": "Объём 500 мл для дороги."
            }],
        },
    )
    assert response.status_code == 200
    assert response.json()["editable"] is True
    assert response.json()["missing_evidence"] == ["500 мл"]
