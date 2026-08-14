import pytest

from backend.app.domain.seller_order_sync import map_seller_order_response


def test_seller_order_response_maps_official_private_summary() -> None:
    result = map_seller_order_response({
        "items": [{
            "order_id": "ORDER-1", "ordered_at": "2026-08-09T10:00:00Z",
            "status": "awaiting_packaging", "total_amount_minor": 129000,
            "currency": "RUB", "item_count": 2,
        }], "total": 1,
    })
    assert result.items[0].source == "official_private"
    assert result.items[0].total_amount_minor == 129000
    assert result.dry_run is True


def test_seller_order_response_rejects_invalid_time() -> None:
    with pytest.raises(ValueError, match="ISO"):
        map_seller_order_response({"items": [{
            "order_id": "ORDER", "ordered_at": "bad", "status": "new",
            "total_amount_minor": 1, "currency": "RUB", "item_count": 1,
        }]})
