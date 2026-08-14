from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_sampling_policy_api_returns_safe_decision() -> None:
    response = TestClient(create_app()).post(
        "/v1/sampling-policy/check",
        json={"url": "https://example.com/item?x=1", "robots_allowed": True},
    )
    assert response.status_code == 200
    assert response.json()["allowed"] is True
    assert response.json()["normalized_url"] == "https://example.com/item"
