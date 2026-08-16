from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_budget_api_returns_readonly_projection() -> None:
    response = TestClient(create_app()).post(
        "/v1/advertising/budget/analyze",
        json={"budget_minor": 10000, "spend_minor": 2000, "days_elapsed": 2, "days_total": 10},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "at_risk"
    assert response.json()["read_only"] is True
