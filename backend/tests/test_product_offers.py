from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_product_offer_gateway
from backend.app.infrastructure.ozon.gateway import StubOzonGateway
from backend.app.main import app


def _client() -> TestClient:
    app.dependency_overrides[get_product_offer_gateway] = StubOzonGateway
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
        response = _client().get(
            "/v1/store-workspaces/unknown/product-offers"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
