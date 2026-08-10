from backend.app.domain.advertising_report import normalize_advertising_report


def test_advertising_report_normalizes_metrics_and_money() -> None:
    result = normalize_advertising_report({
        "campaign_id": "c-1", "report_date": "2026-08-01", "impressions": 100,
        "clicks": 20, "orders": 3, "sales_minor": 50000, "spend_minor": 5000,
        "currency": "RUB",
    })
    assert result.clicks == 20
    assert result.sales_minor == 50000
    assert result.source == "performance_api"
