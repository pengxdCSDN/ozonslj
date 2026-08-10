import pytest

from backend.app.domain.seller_stock_sync import map_seller_stock_response


def test_seller_stock_response_maps_official_private_snapshot() -> None:
    result = map_seller_stock_response({
        "items": [{
            "offer_id": "SKU-1", "warehouse_id": "WH-1",
            "available_quantity": 8, "reserved_quantity": 2,
        }],
        "total": 1, "next_cursor": None,
    })
    assert result.items[0].source == "official_private"
    assert result.items[0].available_quantity == 8
    assert result.dry_run is True


def test_seller_stock_response_rejects_negative_quantity() -> None:
    with pytest.raises(ValueError, match="非负"):
        map_seller_stock_response({"items": [{
            "offer_id": "SKU", "warehouse_id": "WH",
            "available_quantity": -1, "reserved_quantity": 0,
        }]})
