from fastapi.testclient import TestClient

from backend.app.main import app


def test_data_sources_api_returns_estimation_marker() -> None:
    response = TestClient(app).post("/v1/data-sources/label", json={"source": "public_sample"})
    assert response.status_code == 200
    assert response.json()["estimated"] is True
