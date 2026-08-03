from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_current_user, get_product_offer_gateway
from backend.app.domain.identity import AuthenticatedUser
from backend.app.infrastructure.ozon.gateway import StubOzonGateway
from backend.app.main import app


def _client(workspace_ids: tuple[str, ...] = ("local",)) -> TestClient:
    app.dependency_overrides[get_product_offer_gateway] = StubOzonGateway
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        id="operator-1",
        email="operator@example.com",
        display_name="Operator",
        role="operator",
        workspace_ids=workspace_ids,
    )
    return TestClient(app)


def test_operator_can_list_stub_product_offers() -> None:
    try:
        response = _client().get(
            "/v1/store-workspaces/local/product-offers",
            params={"limit": 2},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert response.json()["next_cursor"] == "2"
    assert response.json()["source"] == "stub"


def test_product_offer_limit_is_bounded() -> None:
    try:
        response = _client().get(
            "/v1/store-workspaces/local/product-offers",
            params={"limit": 101},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_product_offer_cursor_must_be_non_negative_integer() -> None:
    try:
        response = _client().get(
            "/v1/store-workspaces/local/product-offers",
            params={"cursor": "-1"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_unknown_workspace_returns_not_found() -> None:
    try:
        response = _client(("unknown",)).get(
            "/v1/store-workspaces/unknown/product-offers"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_operator_cannot_read_an_unassigned_workspace() -> None:
    try:
        response = _client().get("/v1/store-workspaces/other/product-offers")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "无权访问该工作区"
