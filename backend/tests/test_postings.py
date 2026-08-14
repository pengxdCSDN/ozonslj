from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_posting_gateway, get_store_workspace_gateway
from backend.app.domain.posting import PostingPage, PostingSummary
from backend.app.domain.store_workspace import StoreWorkspace
from backend.app.main import create_app


class StubPostingGateway:
    """API 测试只提供脱敏履约摘要，不访问 PostgreSQL 或真实 Ozon。"""

    async def list_postings(
        self,
        *,
        workspace_id: str,
        cursor: str | None,
        limit: int,
    ) -> PostingPage:
        del workspace_id
        now = datetime.now(UTC)
        postings = [
            PostingSummary(
                posting_id="posting-2",
                customer_order_id="order-2",
                ozon_posting_number="FBO-20002",
                fulfillment_type="FBO",
                status="awaiting_deliver",
                shipment_date=date(2026, 8, 8),
                item_count=2,
                total_quantity=3,
                synced_at=now,
            ),
            PostingSummary(
                posting_id="posting-1",
                customer_order_id="order-1",
                ozon_posting_number="FBS-20001",
                fulfillment_type="FBS",
                status="delivered",
                shipment_date=date(2026, 8, 7),
                item_count=1,
                total_quantity=1,
                synced_at=now,
            ),
        ]
        offset = int(cursor) if cursor is not None else 0
        items = postings[offset : offset + limit]
        end = offset + len(items)
        return PostingPage(
            items=items,
            total=len(postings),
            next_cursor=str(end) if end < len(postings) else None,
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
            display_name="履约测试工作区",
            status=self._workspace_status,
            verified_at=now if self._workspace_status == "active" else None,
            created_at=now,
            updated_at=now,
        )


def _client(workspace_status: str = "active") -> TestClient:
    app = create_app()
    app.dependency_overrides[get_posting_gateway] = StubPostingGateway
    app.dependency_overrides[get_store_workspace_gateway] = lambda: StubWorkspaceGateway(
        workspace_status
    )
    return TestClient(app)


def test_operator_can_list_fbo_and_fbs_posting_summaries() -> None:
    response = _client().get(
        "/v1/store-workspaces/store-1/postings",
        params={"limit": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["next_cursor"] == "1"
    assert body["items"][0]["fulfillment_type"] == "FBO"
    assert body["items"][0]["total_quantity"] == 3
    assert "tracking_number" not in body["items"][0]


@pytest.mark.parametrize("params", [{"limit": 101}, {"cursor": "-1"}])
def test_posting_pagination_is_bounded(params: dict[str, object]) -> None:
    response = _client().get(
        "/v1/store-workspaces/store-1/postings",
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
def test_unavailable_workspace_cannot_read_postings(
    workspace_id: str,
    workspace_status: str,
    expected_status: int,
) -> None:
    response = _client(workspace_status).get(
        f"/v1/store-workspaces/{workspace_id}/postings"
    )
    assert response.status_code == expected_status
