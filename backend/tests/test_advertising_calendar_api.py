from fastapi.testclient import TestClient

from backend.app.main import app


def test_calendar_api_returns_thirty_days() -> None:
    response = TestClient(app).post(
        "/v1/advertising/calendar/build", json={"start_date": "2026-08-10"}
    )
    assert response.status_code == 200
    assert len(response.json()) == 30
    assert response.json()[0]["phase"] == "testing"
