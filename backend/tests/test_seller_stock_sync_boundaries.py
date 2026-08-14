import pytest

from backend.app.domain.seller_stock_sync import map_seller_stock_response


def test_seller_stock_rejects_duplicate_offer_warehouse_snapshot() -> None:
    row = {
        "offer_id": "SKU", "warehouse_id": "WH",
        "available_quantity": 1, "reserved_quantity": 0,
    }
    with pytest.raises(ValueError, match="重复"):
        map_seller_stock_response({"items": [row, row]})


def test_seller_stock_rejects_blank_cursor() -> None:
    with pytest.raises(ValueError, match="next_cursor"):
        map_seller_stock_response({"items": [], "next_cursor": " "})
