from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from backend.app.api.dependencies import (
    get_stock_position_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.stock_position import StockPosition, StockPositionPage
from backend.app.domain.store_workspace import StoreWorkspace
from backend.app.main import create_app


class StubStockPositionGateway:
    """API 测试只验证 HTTP 契约，不连接真实 PostgreSQL 或 Ozon。"""

    async def list_stock_positions(
        self,
        *,
        workspace_id: str,
        cursor: str | None,
        limit: int,
    ) -> StockPositionPage:
        del workspace_id
        items = [
            StockPosition(
                offer_id="SKU-1",
                warehouse_id="WH-FBO",
                warehouse_name="FBO 仓",
                fulfillment_type="FBO",
                available_quantity=12,
                reserved_quantity=2,
                synced_at=datetime.now(UTC),
            ),
            StockPosition(
                offer_id="SKU-1",
                warehouse_id="WH-FBS",
                warehouse_name="自有仓",
                fulfillment_type="FBS",
                available_quantity=5,
                reserved_quantity=1,
                synced_at=datetime.now(UTC),
            ),
        ]
        offset = int(cursor) if cursor is not None else 0
        page_items = items[offset : offset + limit]
        end = offset + len(page_items)
        return StockPositionPage(
            items=page_items,
            total=len(items),
            next_cursor=str(end) if end < len(items) else None,
        )


class StubWorkspaceGateway:
    def __init__(self, workspace_status: str = "active") -> None:
        self._workspace_status = workspace_status

    async def get_workspace(self, workspace_id: str) -> StoreWorkspace | None:
        if workspace_id == "unknown":
            return None
        now = datetime.now(UTC)
        return StoreWorkspace(
            id=workspace_id,
            display_name="库存测试工作区",
            status=self._workspace_status,
            verified_at=now if self._workspace_status == "active" else None,
            created_at=now,
            updated_at=now,
        )


def _client(workspace_status: str = "active") -> TestClient:
    app = create_app()
    app.dependency_overrides[get_stock_position_gateway] = StubStockPositionGateway
    app.dependency_overrides[get_store_workspace_gateway] = lambda: StubWorkspaceGateway(
        workspace_status
    )
    return TestClient(app)


def test_operator_can_list_fbo_and_fbs_stock_positions() -> None:
    response = _client().get(
        "/v1/store-workspaces/store-1/stock-positions",
        params={"limit": 1},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert response.json()["next_cursor"] == "1"
    assert response.json()["items"][0]["fulfillment_type"] == "FBO"
    assert response.json()["source"] == "postgresql"


@pytest.mark.parametrize("params", [{"limit": 101}, {"cursor": "-1"}])
def test_stock_position_pagination_is_bounded(params: dict[str, object]) -> None:
    response = _client().get(
        "/v1/store-workspaces/store-1/stock-positions",
        params=params,
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("workspace_id", "workspace_status", "expected_status"),
    [
        ("unknown", "active", 404),
        ("store-1", "pending", 409),
        ("store-1", "invalid", 403),
        ("store-1", "disabled", 403),
    ],
)
def test_unavailable_workspace_cannot_read_stock(
    workspace_id: str,
    workspace_status: str,
    expected_status: int,
) -> None:
    response = _client(workspace_status).get(
        f"/v1/store-workspaces/{workspace_id}/stock-positions"
    )

    assert response.status_code == expected_status
