from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_listing_layering_api() -> None:
    response = TestClient(create_app()).post(
        "/v1/listing/keywords/classify",
        json={
            "keywords": ["термос", "500 мл"],
            "core_terms": ["термос"],
            "attribute_terms": ["500 мл"],
        },
    )
    assert response.status_code == 200
    assert response.json()[1]["layer"] == "attribute"
    assert response.json()[0]["manually_confirmed"] is True
