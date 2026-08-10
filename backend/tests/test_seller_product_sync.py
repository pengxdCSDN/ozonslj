import pytest

from backend.app.domain.seller_product_sync import map_seller_product_response


def test_seller_product_response_is_mapped_to_official_private_preview() -> None:
    result = map_seller_product_response({
        "items": [{
            "offer_id": "SKU-1", "ozon_product_id": 123,
            "name": "Demo", "price_minor": 129000,
            "currency": "RUB", "available_stock": 7,
        }], "total": 1, "next_cursor": "next",
    })
    assert result.items[0].source == "official_private"
    assert result.credentials_required is True
    assert result.dry_run is True


def test_seller_product_response_rejects_invalid_shape() -> None:
    with pytest.raises(ValueError, match="items"):
        map_seller_product_response({"items": "bad"})
