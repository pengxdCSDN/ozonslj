from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_parser_alerts_compare_api() -> None:
    response = TestClient(create_app()).post(
        "/v1/parser-alerts/compare",
        json={"previous": {"title": "A", "rating": "4.5"}, "current": {"title": "B"}},
    )
    assert response.status_code == 200
    assert response.json()[0]["field_name"] == "rating"
    assert response.json()[0]["severity"] == "error"
