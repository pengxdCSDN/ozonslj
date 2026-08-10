from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from backend.app.api.dependencies import (
    get_customer_order_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.customer_order import CustomerOrder, CustomerOrderPage
from backend.app.domain.store_workspace import StoreWorkspace
from backend.app.main import create_app


class StubCustomerOrderGateway:
    """只提供脱敏订单摘要，测试不访问 PostgreSQL 或真实 Ozon。"""

    async def list_customer_orders(
        self,
        *,
        workspace_id: str,
        cursor: str | None,
        limit: int,
    ) -> CustomerOrderPage:
        del workspace_id
        now = datetime.now(UTC)
        orders = [
            CustomerOrder(
                order_id="order-2",
                ozon_order_id="20002",
                status="awaiting_packaging",
                total_amount=Decimal("1290.00"),
                currency="RUB",
                ordered_at=now,
                synced_at=now,
            ),
            CustomerOrder(
                order_id="order-1",
                ozon_order_id="20001",
                status="delivered",
                total_amount=Decimal("880.50"),
                currency="RUB",
                ordered_at=now,
                synced_at=now,
            ),
        ]
        offset = int(cursor) if cursor is not None else 0
        items = orders[offset : offset + limit]
        end = offset + len(items)
        return CustomerOrderPage(
            items=items,
            total=len(orders),
            next_cursor=str(end) if end < len(orders) else None,
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
            display_name="订单测试工作区",
            status=self._workspace_status,
            verified_at=now if self._workspace_status == "active" else None,
            created_at=now,
            updated_at=now,
        )


def _client(workspace_status: str = "active") -> TestClient:
    app = create_app()
    app.dependency_overrides[get_customer_order_gateway] = StubCustomerOrderGateway
    app.dependency_overrides[get_store_workspace_gateway] = lambda: StubWorkspaceGateway(
        workspace_status
    )
    return TestClient(app)


def test_operator_can_list_desensitized_customer_orders() -> None:
    response = _client().get(
        "/v1/store-workspaces/store-1/customer-orders",
        params={"limit": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["next_cursor"] == "1"
    assert body["items"][0]["total_amount"] == "1290.00"
    assert "raw_summary" not in body["items"][0]
    assert body["source"] == "postgresql"


@pytest.mark.parametrize("params", [{"limit": 101}, {"cursor": "-1"}])
def test_customer_order_pagination_is_bounded(params: dict[str, object]) -> None:
    response = _client().get(
        "/v1/store-workspaces/store-1/customer-orders",
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
def test_unavailable_workspace_cannot_read_orders(
    workspace_id: str,
    workspace_status: str,
    expected_status: int,
) -> None:
    response = _client(workspace_status).get(
        f"/v1/store-workspaces/{workspace_id}/customer-orders"
    )

    assert response.status_code == expected_status
