from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from backend.app.api.dependencies import (
    get_seller_operation_gateway,
    get_store_workspace_gateway,
)
from backend.app.domain.seller_operation import (
    SellerOperationPage,
    SellerOperationSummary,
)
from backend.app.domain.store_workspace import StoreWorkspace
from backend.app.main import create_app


class StubSellerOperationGateway:
    async def list_seller_operations(
        self,
        *,
        workspace_id: str,
        cursor: str | None,
        limit: int,
    ) -> SellerOperationPage:
        del workspace_id
        operations = [
            SellerOperationSummary(
                operation_id="operation-2",
                operation_type="stock_sync",
                risk_level="read",
                target_type="stock_position",
                target_count=25,
                request_id="request-2",
                result="success",
                occurred_at=datetime.now(UTC),
            ),
            SellerOperationSummary(
                operation_id="operation-1",
                operation_type="credential_verify",
                risk_level="read",
                target_type="seller_account",
                target_count=1,
                request_id="request-1",
                result="failed",
                occurred_at=datetime.now(UTC),
            ),
        ]
        offset = int(cursor) if cursor is not None else 0
        items = operations[offset : offset + limit]
        end = offset + len(items)
        return SellerOperationPage(
            items=items,
            total=len(operations),
            next_cursor=str(end) if end < len(operations) else None,
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
            display_name="审计测试工作区",
            status=self._workspace_status,
            verified_at=now if self._workspace_status == "active" else None,
            created_at=now,
            updated_at=now,
        )


def _client(workspace_status: str = "active") -> TestClient:
    app = create_app()
    app.dependency_overrides[get_seller_operation_gateway] = StubSellerOperationGateway
    app.dependency_overrides[get_store_workspace_gateway] = lambda: StubWorkspaceGateway(
        workspace_status
    )
    return TestClient(app)


def test_operator_can_list_desensitized_operation_timeline() -> None:
    response = _client().get(
        "/v1/store-workspaces/store-1/seller-operations",
        params={"limit": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["next_cursor"] == "1"
    assert body["items"][0]["operation_type"] == "stock_sync"
    assert "detail" not in body["items"][0]
    assert "user_id" not in body["items"][0]


@pytest.mark.parametrize("params", [{"limit": 101}, {"cursor": "-1"}])
def test_operation_pagination_is_bounded(params: dict[str, object]) -> None:
    response = _client().get(
        "/v1/store-workspaces/store-1/seller-operations",
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
def test_unavailable_workspace_cannot_read_operation_timeline(
    workspace_id: str,
    workspace_status: str,
    expected_status: int,
) -> None:
    response = _client(workspace_status).get(
        f"/v1/store-workspaces/{workspace_id}/seller-operations"
    )
    assert response.status_code == expected_status
