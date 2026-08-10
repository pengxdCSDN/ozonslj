import pytest

from backend.app.domain.advertising_thresholds import create_advertising_thresholds


def test_thresholds_are_versioned_and_validated() -> None:
    result = create_advertising_thresholds(
        version=2, min_impressions=100, min_clicks=10,
        high_cvr_percent=8, high_spend_minor=1000,
    )
    assert result.version == 2
    with pytest.raises(ValueError):
        create_advertising_thresholds(
            version=0, min_impressions=0, min_clicks=0,
            high_cvr_percent=0, high_spend_minor=0,
        )
