from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_store_workspace_gateway
from backend.app.domain.store_workspace import StoreWorkspace
from backend.app.main import app


class _WorkspaceGateway:
    async def list_store_workspaces(self) -> list[StoreWorkspace]:
        return [
            StoreWorkspace(
                id="local",
                name="Local workspace",
                seller_display_name="Local stub seller",
                seller_status="disabled",
            )
        ]


def test_store_workspaces_list_excludes_credentials() -> None:
    app.dependency_overrides[get_store_workspace_gateway] = _WorkspaceGateway
    try:
        response = TestClient(app).get("/v1/store-workspaces")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == "local"
    response_text = response.text.lower()
    assert "api_key" not in response_text
    assert "client_id" not in response_text
    assert "encrypted" not in response_text
