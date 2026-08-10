from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_advertising_reports_api_rejects_impossible_metrics() -> None:
    response = TestClient(create_app()).post(
        "/v1/advertising/reports/sync-preview",
        json={
            "rows": [{
                "campaign_id": "c-1", "report_date": "2026-08-01",
                "impressions": 10, "clicks": 11,
            }],
        },
    )
    assert response.status_code == 422
