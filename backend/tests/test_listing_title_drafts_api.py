from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_title_draft_api() -> None:
    response = TestClient(create_app()).post(
        "/v1/listing/title-drafts/generate",
        json={"category": "Термосы", "core_terms": ["термос"], "attribute_terms": ["500 мл"]},
    )
    assert response.status_code == 200
    assert response.json()["editable"] is True
    assert response.json()["covered_terms"] == ["термос", "500 мл"]
