from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_expand_api_returns_layered_candidates() -> None:
    response = TestClient(create_app()).post(
        "/v1/selection/expand/run",
        json={
            "seed_product": "термос",
            "core_keywords": ["термос"],
            "attributes": ["500 мл"],
            "scenes": ["поход"],
        },
    )
    assert response.status_code == 200
    assert response.json()["variant_candidates"] == ["термос 500 мл"]
