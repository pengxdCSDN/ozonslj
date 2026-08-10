import pytest

from backend.app.domain.seller_fulfillment_sync import map_seller_fulfillment_response


def test_fulfillment_rejects_duplicate_posting() -> None:
    row = {
        "posting_id": "P-1", "fulfillment_type": "FBO", "status": "created",
        "shipment_date": "2026-08-09", "item_count": 1, "total_quantity": 1,
    }
    with pytest.raises(ValueError, match="重复"):
        map_seller_fulfillment_response({"items": [row, row]})


def test_fulfillment_rejects_blank_cursor() -> None:
    with pytest.raises(ValueError, match="next_cursor"):
        map_seller_fulfillment_response({"items": [], "next_cursor": " "})
