import pytest

from backend.app.domain.seller_order_sync import map_seller_order_response


def test_seller_order_normalizes_currency_and_rejects_duplicates() -> None:
    row = {
        "order_id": "ORDER-1", "ordered_at": "2026-08-09T10:00:00Z",
        "status": "new", "total_amount_minor": 1, "currency": "rub", "item_count": 1,
    }
    result = map_seller_order_response({"items": [row]})
    assert result.items[0].currency == "RUB"
    with pytest.raises(ValueError, match="重复"):
        map_seller_order_response({"items": [row, row]})


def test_seller_order_rejects_blank_cursor() -> None:
    with pytest.raises(ValueError, match="next_cursor"):
        map_seller_order_response({"items": [], "next_cursor": " "})
