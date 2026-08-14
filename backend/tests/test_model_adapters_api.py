from fastapi.testclient import TestClient

from backend.app.main import app


def test_model_adapter_api_inspects_generic_config() -> None:
    response = TestClient(app).post(
        "/v1/model-adapters/inspect",
        json={"adapter": "generic", "provider": "Local", "model": "stub", "enabled": False},
    )
    assert response.status_code == 200
    assert response.json()["adapter"] == "generic"
    assert "api_key" not in response.json()
