import pytest

from backend.app.domain.seller_fulfillment_sync import map_seller_fulfillment_response


def test_seller_fulfillment_maps_fbo_and_fbs() -> None:
    result = map_seller_fulfillment_response({
        "items": [
            {"posting_id": "P-1", "fulfillment_type": "FBO", "status": "awaiting",
             "shipment_date": "2026-08-09", "item_count": 1, "total_quantity": 2},
            {"posting_id": "P-2", "fulfillment_type": "FBS", "status": "shipped",
             "shipment_date": None, "item_count": 2, "total_quantity": 3},
        ], "total": 2,
    })
    assert [item.fulfillment_type for item in result.items] == ["FBO", "FBS"]
    assert all(item.source == "official_private" for item in result.items)


def test_seller_fulfillment_rejects_unknown_type() -> None:
    with pytest.raises(ValueError, match="FBO 或 FBS"):
        map_seller_fulfillment_response({"items": [{
            "posting_id": "P", "fulfillment_type": "OTHER", "status": "new",
            "item_count": 1, "total_quantity": 1,
        }]})
