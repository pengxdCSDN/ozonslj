from fastapi.testclient import TestClient

from backend.app.main import app


def test_sync_processor_plan_api_exposes_watermark_policy() -> None:
    response = TestClient(app).post(
        "/v1/sync-processor/plan",
        json={"resource_type": "products", "max_pages": 5, "max_retries": 2},
    )
    assert response.status_code == 200
    assert response.json()["dry_run"] is True
    assert "成功保存" in response.json()["watermark_policy"]
