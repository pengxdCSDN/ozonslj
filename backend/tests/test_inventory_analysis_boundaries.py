import pytest

from backend.app.domain.inventory_analysis import analyze_inventory


def test_inventory_analysis_rejects_boolean_and_reversed_thresholds() -> None:
    with pytest.raises(ValueError):
        analyze_inventory(
            available_units=True, inbound_units=0, average_daily_sales=1,
            safety_days=7, overstock_days=60,
        )
    with pytest.raises(ValueError):
        analyze_inventory(
            available_units=1, inbound_units=0, average_daily_sales=1,
            safety_days=60, overstock_days=7,
        )


def test_inventory_analysis_zero_sales_is_incomplete_without_false_risk() -> None:
    result = analyze_inventory(
        available_units=10, inbound_units=5, average_daily_sales=0,
        safety_days=7, overstock_days=60,
    )
    assert result.incomplete is True
    assert result.days_of_cover is None
    assert result.stockout_risk is False
