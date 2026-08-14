from backend.app.domain.advertising_analysis import analyze_advertising


def test_advertising_analysis_reports_acos_and_unconverted_keywords() -> None:
    result = analyze_advertising(
        spend_minor=3000, ad_sales_minor=10000, total_sales_minor=20000,
        keyword_count=10, unconverted_keyword_count=2, acos_alert_percent=20,
    )
    assert result.acos_percent == 30
    assert len(result.anomalies) == 2
    assert result.read_only is True
