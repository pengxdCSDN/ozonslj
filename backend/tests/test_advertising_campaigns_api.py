from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_campaign_sync_preview_api() -> None:
    response = TestClient(create_app()).post(
        "/v1/advertising/campaigns/sync-preview",
        json={
            "campaigns": [{
                "campaign_id": "c-1", "name": "测试",
                "campaign_type": "search", "status": "active", "keywords": [],
            }],
        },
    )
    assert response.status_code == 200
    assert response.json()[0]["source"] == "performance_api"
