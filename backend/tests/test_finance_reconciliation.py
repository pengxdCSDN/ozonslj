from backend.app.domain.finance_reconciliation import (
    EstimatedProfitSnapshot,
    aggregate_finance_accruals,
    reconcile_profit_snapshots,
)
from backend.app.domain.ozon_finance_accrual import FinanceAccrualLine


def test_finance_lines_are_aggregated_by_order_and_sku_without_guessing_missing_keys() -> None:
    lines = (
        FinanceAccrualLine("a-1", "2026-08-22", "o-1", "sku-1", "sale", 1000, "RUB", "ozon"),
        FinanceAccrualLine("a-2", "2026-08-22", "o-1", "sku-1", "logistics", -200, "RUB", "ozon"),
        FinanceAccrualLine("a-3", "2026-08-22", None, "sku-2", "sale", 500, "RUB", "ozon"),
    )
    actual = aggregate_finance_accruals(lines)
    assert actual[0].actual_profit_minor == 800
    assert actual[0].actual_logistics_minor == 200
    assert actual[0].accrual_count == 2


def test_reconciliation_only_reports_keys_present_on_both_sides() -> None:
    actual = aggregate_finance_accruals(
        (FinanceAccrualLine("a", "2026-08-22", "o", "s", "sale", 850, "RUB", "ozon"),)
    )
    result = reconcile_profit_snapshots(
        (EstimatedProfitSnapshot("o", "s", 1000, 0), EstimatedProfitSnapshot("missing", "s", 1, 0)),
        actual,
    )
    assert result == {("o", "s"): -150}
