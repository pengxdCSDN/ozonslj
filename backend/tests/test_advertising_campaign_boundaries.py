import pytest

from backend.app.domain.advertising_campaign import map_performance_campaign


def test_campaign_mapping_rejects_negative_bid() -> None:
    with pytest.raises(ValueError):
        map_performance_campaign(
            {"campaign_id": "c", "keywords": [{"keyword": "термос", "bid_minor": -1}]}
        )
