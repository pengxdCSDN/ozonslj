from fastapi.testclient import TestClient

from backend.app.main import app


def test_agent_permissions_api_returns_permanent_read_only_boundary() -> None:
    response = TestClient(app).post(
        "/v1/agents/permissions/check",
        json={
            "agent": "inventory_agent",
            "requested_capabilities": ["read_inventory", "write_stock"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["read_only"] is True
    assert body["external_write_access"] is False
