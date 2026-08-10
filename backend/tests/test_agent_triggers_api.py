from fastapi.testclient import TestClient

from backend.app.main import app


def test_agent_trigger_api_validates_event_trigger() -> None:
    response = TestClient(app).post(
        "/v1/agent-triggers/validate",
        json={
            "trigger_type": "event", "target": "inventory_agent",
            "event_name": "stock_below_safety",
        },
    )
    assert response.status_code == 200
    assert response.json()["read_only"] is True
