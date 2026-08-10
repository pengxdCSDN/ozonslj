from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_smart_search_api() -> None:
    response = TestClient(create_app()).post(
        "/v1/listing/smart-search/check",
        json={
            "text": "термос стальной",
            "required_terms": ["термос", "500 мл"],
            "category": "Термосы",
            "category_terms": ["термос"],
        },
    )
    assert response.status_code == 200
    assert response.json()["original_text_preserved"] is True
    assert "500 мл" in response.json()["missing_terms"]
