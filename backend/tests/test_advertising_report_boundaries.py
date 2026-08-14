import pytest

from backend.app.domain.advertising_report import normalize_advertising_report


def test_advertising_report_rejects_missing_campaign_and_invalid_currency() -> None:
    with pytest.raises(ValueError, match="活动标识"):
        normalize_advertising_report({"report_date": "2026-08-01"})
    with pytest.raises(ValueError, match="三位字母"):
        normalize_advertising_report({
            "campaign_id": "c-1", "report_date": "2026-08-01", "currency": "RUB1",
        })


def test_advertising_report_rejects_boolean_and_non_integer_metrics() -> None:
    with pytest.raises(ValueError, match="整数"):
        normalize_advertising_report({
            "campaign_id": "c-1", "report_date": "2026-08-01", "impressions": True,
        })
    with pytest.raises(ValueError, match="整数"):
        normalize_advertising_report({
            "campaign_id": "c-1", "report_date": "2026-08-01", "clicks": "1.5",
        })
