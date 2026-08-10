from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_listing_risks_api_preserves_original() -> None:
    response = TestClient(create_app()).post(
        "/v1/listing/risks/check",
        json={"text": "Лучший товар лечит всё Apple EAC"},
    )
    assert response.status_code == 200
    assert response.json()["original_text"] == "Лучший товар лечит всё Apple EAC"
    assert response.json()["safe_to_review"] is True
