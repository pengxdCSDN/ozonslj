from fastapi.testclient import TestClient

from backend.app.main import app


def test_keyword_diagnosis_api_returns_read_only_categories() -> None:
    response = TestClient(app).post(
        "/v1/advertising/keywords/diagnose",
        json={"rows": [{
            "keyword": "coat", "impressions": 300, "clicks": 30, "orders": 3,
            "spend_minor": 500, "sales_minor": 5000,
        }]},
    )
    assert response.status_code == 200
    assert response.json()[0]["category"] == "high_cvr"
    assert response.json()[0]["read_only"] is True
