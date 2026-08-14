from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_diff_preview_api_returns_changed_fields() -> None:
    response = TestClient(create_app()).post(
        "/v1/review/diff-previews/build",
        json={
            "old_values": {"price": "2500"},
            "new_values": {"price": "2700"},
            "source": "人工编辑",
            "impact": "影响售价",
        },
    )
    assert response.status_code == 200
    assert response.json()[0]["requires_review"] is True


def test_diff_preview_api_returns_conflict_when_data_is_stale() -> None:
    response = TestClient(create_app()).post(
        "/v1/review/diff-previews/build",
        json={
            "old_values": {"price": "2500"},
            "new_values": {"price": "2700"},
            "source": "人工编辑",
            "impact": "影响售价",
            "observed_at": "2026-08-09T00:00:00Z",
            "max_age_seconds": 60,
            "now": "2026-08-09T00:02:00Z",
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "preview_data_stale"
