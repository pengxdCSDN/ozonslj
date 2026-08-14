from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_product_offer_gateway, get_store_workspace_gateway
from backend.app.domain.store_workspace import StoreWorkspace
from backend.app.infrastructure.ozon.gateway import StubOzonGateway
from backend.app.main import app


class StubWorkspaceGateway:
    """路由测试替身；持久化行为由 PostgreSQL 适配器测试覆盖。"""

    async def get_workspace(self, workspace_id: str) -> StoreWorkspace | None:
        if workspace_id != "local":
            return None
        now = datetime.now(UTC)
        return StoreWorkspace(
            id="local",
            display_name="本地测试工作区",
            status="active",
            verified_at=now,
            created_at=now,
            updated_at=now,
        )


@pytest.fixture(autouse=True)
def override_global_app_dependencies() -> None:
    app.dependency_overrides[get_product_offer_gateway] = StubOzonGateway
    app.dependency_overrides[get_store_workspace_gateway] = StubWorkspaceGateway
    yield
    app.dependency_overrides.clear()


def test_operator_can_list_stub_product_offers() -> None:
    response = TestClient(app).get(
        "/v1/store-workspaces/local/product-offers",
        params={"limit": 2},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert response.json()["next_cursor"] == "2"
    assert response.json()["source"] == "stub"


@pytest.mark.parametrize(
    "params",
    [{"limit": 101}, {"cursor": "-1"}],
)
def test_product_offer_pagination_is_bounded(params: dict[str, object]) -> None:
    response = TestClient(app).get(
        "/v1/store-workspaces/local/product-offers",
        params=params,
    )

    assert response.status_code == 422


def test_unknown_workspace_returns_not_found() -> None:
    response = TestClient(app).get("/v1/store-workspaces/unknown/product-offers")

    assert response.status_code == 404
