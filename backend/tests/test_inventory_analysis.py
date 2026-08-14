from backend.app.domain.inventory_analysis import analyze_inventory


def test_inventory_analysis_reports_stockout_and_inbound() -> None:
    result = analyze_inventory(
        available_units=5, inbound_units=20, average_daily_sales=2,
        safety_days=7, overstock_days=60,
    )
    assert result.days_of_cover == 2.5
    assert result.stockout_risk is True
    assert result.inbound_units == 20
    assert result.read_only is True
