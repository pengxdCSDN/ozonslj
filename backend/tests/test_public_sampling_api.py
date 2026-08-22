from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_public_sampling_preview_uses_stub_and_policy() -> None:
    response = TestClient(create_app()).post(
        "/v1/public-sampling/preview",
        json={
            "requests": [
                {"url": "https://example.com/item"},
                {"url": "https://example.com/private", "robots_allowed": False},
            ]
        },
    )
    assert response.status_code == 200
    assert response.json()[0]["allowed"] is True
    assert response.json()[1]["allowed"] is False


def test_live_public_sampling_requires_server_allowlist() -> None:
    response = TestClient(create_app()).post(
        "/v1/public-sampling/live-preview",
        json={"requests": [{"url": "https://example.com/item"}]},
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "sampling_not_configured"
