import pytest

from backend.app.domain.advertising_thresholds import create_advertising_thresholds


def test_thresholds_reject_boolean_version_and_non_numeric_cvr() -> None:
    with pytest.raises(ValueError):
        create_advertising_thresholds(
            version=True, min_impressions=100, min_clicks=10,
            high_cvr_percent=8, high_spend_minor=1000,
        )
    with pytest.raises((TypeError, ValueError)):
        create_advertising_thresholds(
            version=1, min_impressions=100, min_clicks=10,
            high_cvr_percent="8", high_spend_minor=1000,  # type: ignore[arg-type]
        )
