from backend.app.domain.sales_analysis import analyze_sales


def test_sales_analysis_reports_anomaly_and_opportunity() -> None:
    result = analyze_sales(
        current_sales_minor=12000, previous_sales_minor=10000,
        current_orders=12, previous_orders=10,
        current_window="this-week", previous_window="last-week",
    )
    assert result.change_percent == 20
    assert result.anomalies == []
    assert result.opportunities
    assert result.read_only is True
