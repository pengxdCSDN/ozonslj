from backend.app.domain.advertising_metrics import calculate_advertising_metrics


def test_advertising_metrics_calculates_standard_formulas() -> None:
    result = calculate_advertising_metrics(
        impressions=1000, clicks=100, orders=10, ad_sales_minor=50000,
        total_sales_minor=100000, spend_minor=10000, currency="RUB", window="2026-08-01/2026-08-07",
    )
    assert result.acos_percent == 20.0
    assert result.tacos_percent == 10.0
    assert result.cpc_minor == 100.0
    assert result.ctr_percent == 10.0
    assert result.cvr_percent == 10.0
    assert result.roi_percent == 500.0
    assert result.complete is True


def test_advertising_metrics_keeps_zero_denominators_unknown() -> None:
    result = calculate_advertising_metrics(
        impressions=0, clicks=0, orders=0, ad_sales_minor=0,
        total_sales_minor=0, spend_minor=100, currency="RUB", window="day",
    )
    assert result.acos_percent is None
    assert result.cpc_minor is None
    assert result.complete is False
