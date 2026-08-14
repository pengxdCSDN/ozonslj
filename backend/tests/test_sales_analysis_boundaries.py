import pytest

from backend.app.domain.sales_analysis import analyze_sales


def test_sales_analysis_rejects_boolean_metric() -> None:
    with pytest.raises(ValueError):
        analyze_sales(
            current_sales_minor=True, previous_sales_minor=100,
            current_orders=1, previous_orders=1,
            current_window="today", previous_window="yesterday",
        )


def test_sales_analysis_marks_zero_baseline_as_incomplete() -> None:
    result = analyze_sales(
        current_sales_minor=100, previous_sales_minor=0,
        current_orders=1, previous_orders=0,
        current_window="today", previous_window="yesterday",
    )
    assert result.change_percent is None
    assert result.order_change_percent is None
    assert result.incomplete is False
