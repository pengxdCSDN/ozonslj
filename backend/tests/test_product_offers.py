from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_product_offer_gateway
from backend.app.infrastructure.ozon.gateway import StubOzonGateway
from backend.app.main import app, create_app


def test_product_offers_survive_local_backend_restart(tmp_path) -> None:
    database_path = tmp_path / "ozonslj-test.db"

    first_app = create_app(database_path=database_path)
    first_response = TestClient(first_app).get(
        "/v1/store-workspaces/local/product-offers",
        params={"limit": 1},
    )

    restarted_app = create_app(database_path=database_path)
    restarted_response = TestClient(restarted_app).get(
        "/v1/store-workspaces/local/product-offers",
        params={"limit": 3},
    )

    assert first_response.status_code == 200
    assert first_response.json()["source"] == "sqlite"
    assert restarted_response.status_code == 200
    assert restarted_response.json()["total"] == 3
    assert restarted_response.json()["items"][0]["offer_id"] == "CN-MUG-420-BL"


def test_operator_can_list_stub_product_offers() -> None:
    app.dependency_overrides.clear()
    app.dependency_overrides[get_product_offer_gateway] = StubOzonGateway
    response = TestClient(app).get(
        "/v1/store-workspaces/local/product-offers",
        params={"limit": 2},
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "offer_id": "CN-MUG-420-BL",
                "ozon_product_id": "1847295031",
                "name": "双层保温杯 420ml",
                "price": "1290.00",
                "currency": "RUB",
                "available_stock": 37,
            },
            {
                "offer_id": "CN-LAMP-DESK-WH",
                "ozon_product_id": "1847295188",
                "name": "可调光桌面灯",
                "price": "2490.00",
                "currency": "RUB",
                "available_stock": 12,
            },
        ],
        "total": 3,
        "next_cursor": "2",
        "source": "stub",
    }
    app.dependency_overrides.clear()


def test_product_offer_limit_is_bounded() -> None:
    response = TestClient(app).get(
        "/v1/store-workspaces/local/product-offers",
        params={"limit": 101},
    )

    assert response.status_code == 422
