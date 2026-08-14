from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_listing_publish_api_uses_approval_and_readback_gate() -> None:
    response = TestClient(create_app()).post(
        "/v1/listing/publish/execute",
        json={
            "idempotency_key": "cmd-1",
            "version": 2,
            "status": "approved",
            "requested_text": "新标题",
            "readback_text": "新标题",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "executed"
    assert response.json()["matched"] is True
