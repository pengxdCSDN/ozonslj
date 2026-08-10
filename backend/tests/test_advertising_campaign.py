from backend.app.domain.advertising_campaign import map_performance_campaign


def test_campaign_mapping_deduplicates_normal_and_negative_keywords() -> None:
    result = map_performance_campaign({
        "campaign_id": "c-1", "name": "测试活动", "campaign_type": "search", "status": "active",
        "keywords": [
            {"keyword": " термос ", "bid_minor": 100},
            {"keyword": "термос", "bid_minor": 200},
            {"keyword": "термос", "negative": True},
        ],
    })
    assert result.source == "performance_api"
    assert len(result.keywords) == 2
    assert result.keywords[1].negative is True
