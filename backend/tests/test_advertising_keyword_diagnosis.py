import pytest

from backend.app.domain.advertising_keyword_diagnosis import diagnose_keywords


def test_diagnosis_classifies_four_business_categories() -> None:
    rows = [
        {"keyword": "star", "impressions": 500, "clicks": 50, "orders": 3,
         "spend_minor": 500, "sales_minor": 5000},
        {"keyword": "cvr", "impressions": 200, "clicks": 20, "orders": 4,
         "spend_minor": 500, "sales_minor": 4000},
        {"keyword": "waste", "impressions": 200, "clicks": 20, "orders": 0,
         "spend_minor": 2000, "sales_minor": 0},
        {"keyword": "potential", "impressions": 20, "clicks": 2, "orders": 0,
         "spend_minor": 10, "sales_minor": 0},
    ]
    result = diagnose_keywords(rows)
    assert [item.category for item in result] == [
        "star", "high_cvr", "high_spend_no_conversion", "potential"
    ]
    assert all(item.read_only for item in result)


def test_diagnosis_rejects_invalid_metric_relationship() -> None:
    with pytest.raises(ValueError, match="关系"):
        diagnose_keywords([{"keyword": "bad", "impressions": 1, "clicks": 2, "orders": 0}])
