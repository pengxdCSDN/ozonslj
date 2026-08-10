from dataclasses import dataclass

from fastapi.testclient import TestClient

from backend.app.api.dependencies import (
    get_seller_product_snapshot_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.seller_product_sync import SellerProductSyncPreview
from backend.app.main import create_app


@dataclass
class MissingWorkspaceGateway:
    async def get_workspace(self, workspace_id: str) -> None:
        return None


@dataclass
class SnapshotGateway:
    async def save_snapshot(
        self, *, workspace_id: str, preview: SellerProductSyncPreview
    ) -> SellerProductSyncPreview:
        return preview


def _payload() -> dict[str, object]:
    return {
        "response": {
            "items": [{
                "offer_id": "SKU-1", "ozon_product_id": "123", "name": "Demo",
                "price_minor": 100, "currency": "RUB", "available_stock": 1,
            }],
            "total": 1,
        }
    }


def test_product_snapshot_api_rejects_missing_workspace() -> None:
    app = create_app()
    app.dependency_overrides[get_store_workspace_gateway] = MissingWorkspaceGateway
    app.dependency_overrides[get_seller_product_snapshot_gateway] = SnapshotGateway
    try:
        response = TestClient(app).post(
            "/v1/seller/products/store-workspaces/ws-missing/sync-and-save",
            json=_payload(),
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_product_snapshot_api_rejects_invalid_upstream_response() -> None:
    app = create_app()

    class ExistingWorkspaceGateway:
        async def get_workspace(self, workspace_id: str) -> object:
            return object()

    app.dependency_overrides[get_store_workspace_gateway] = ExistingWorkspaceGateway
    app.dependency_overrides[get_seller_product_snapshot_gateway] = SnapshotGateway
    try:
        response = TestClient(app).post(
            "/v1/seller/products/store-workspaces/ws-1/sync-and-save",
            json={"response": {"items": "invalid"}},
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
