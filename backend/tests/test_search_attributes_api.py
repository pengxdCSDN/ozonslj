from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_search_attributes_api() -> None:
    response = TestClient(create_app()).post(
        "/v1/listing/search-attributes/suggest",
        json={
            "required": {"volume": "", "material": ""},
            "current": {"volume": "500 мл"},
            "keyword_terms": {"material": "сталь"},
        },
    )
    assert response.status_code == 200
    assert response.json()["coverage_percent"] == 100.0
