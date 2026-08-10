from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_listing_versions_compare_api() -> None:
    response = TestClient(create_app()).post(
        "/v1/listing/versions/compare",
        json={"version": 2, "original_text": "标题", "edited_text": "新标题", "status": "review"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "review"
    assert response.json()["original_text"] == "标题"
