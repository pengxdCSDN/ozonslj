import pytest

from backend.app.domain.advertising_keyword_diagnosis import diagnose_keywords


def test_keyword_diagnosis_rejects_invalid_thresholds() -> None:
    with pytest.raises(ValueError, match="非负整数"):
        diagnose_keywords([], min_clicks=-1)
    with pytest.raises(ValueError, match="高 CVR"):
        diagnose_keywords([], high_cvr_percent=-0.1)


def test_keyword_diagnosis_rejects_boolean_metric() -> None:
    with pytest.raises(ValueError):
        diagnose_keywords([{"keyword": "термос", "impressions": True}])
