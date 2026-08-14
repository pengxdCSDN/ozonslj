import pytest

from backend.app.domain.seller_product_sync import map_seller_product_response


def test_seller_product_normalizes_currency_and_rejects_invalid_product_id() -> None:
    result = map_seller_product_response({
        "items": [{
            "offer_id": "SKU-1", "ozon_product_id": "123", "name": "Demo",
            "price_minor": 100, "currency": "rub", "available_stock": 1,
        }],
    })
    assert result.items[0].currency == "RUB"
    with pytest.raises(ValueError, match="product_id"):
        map_seller_product_response({
            "items": [{
                "offer_id": "SKU-1", "ozon_product_id": True, "name": "Demo",
                "price_minor": 100, "currency": "RUB", "available_stock": 1,
            }],
        })


def test_seller_product_rejects_blank_cursor() -> None:
    with pytest.raises(ValueError, match="next_cursor"):
        map_seller_product_response({"items": [], "next_cursor": " "})
