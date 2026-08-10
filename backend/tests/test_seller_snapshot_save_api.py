import pytest
from fastapi.testclient import TestClient

from backend.app.api.dependencies import (
    get_seller_fulfillment_snapshot_gateway,
    get_seller_order_snapshot_gateway,
    get_seller_stock_snapshot_gateway,
    get_store_workspace_gateway,
)
from backend.app.main import create_app


class MissingWorkspaceGateway:
    async def get_workspace(self, workspace_id: str) -> None:
        return None


class NoopSnapshotGateway:
    async def save_snapshot(self, *, workspace_id: str, preview: object) -> object:
        return preview


@pytest.mark.parametrize(
    ("path", "gateway_dependency", "response"),
    [
        (
            "/v1/seller/stock/store-workspaces/ws-missing/sync-and-save",
            get_seller_stock_snapshot_gateway,
            {"items": [], "total": 0},
        ),
        (
            "/v1/seller/orders/store-workspaces/ws-missing/sync-and-save",
            get_seller_order_snapshot_gateway,
            {"items": [], "total": 0},
        ),
        (
            "/v1/seller/fulfillment/store-workspaces/ws-missing/sync-and-save",
            get_seller_fulfillment_snapshot_gateway,
            {"items": [], "total": 0},
        ),
    ],
)
def test_seller_snapshot_save_api_rejects_missing_workspace(
    path: str, gateway_dependency: object, response: dict[str, object]
) -> None:
    app = create_app()
    app.dependency_overrides[get_store_workspace_gateway] = MissingWorkspaceGateway
    app.dependency_overrides[gateway_dependency] = NoopSnapshotGateway  # type: ignore[index]
    try:
        result = TestClient(app).post(path, json={"response": response})
        assert result.status_code == 404
    finally:
        app.dependency_overrides.clear()
