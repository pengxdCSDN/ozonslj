import pytest

from backend.app.domain.profit_reconciliation import (
    ProfitReconciliationError,
    preview_profit_reconciliation_csv,
)


def test_reconciliation_preview_calculates_profit_variance() -> None:
    preview = preview_profit_reconciliation_csv(
        "order_id,sku_id,estimated_profit_minor,actual_profit_minor,estimated_logistics_minor,actual_logistics_minor,source\n"
        "O-1,S-1,1000,850,300,450,ozon_finance\n"
    )

    assert preview.errors == ()
    assert preview.rows[0].variance_minor == -150
    assert preview.rows[0].variance_percent == -15.0


def test_reconciliation_preview_keeps_valid_rows_and_reports_bad_rows() -> None:
    preview = preview_profit_reconciliation_csv(
        "order_id,sku_id,estimated_profit_minor,actual_profit_minor,estimated_logistics_minor,actual_logistics_minor,source\n"
        "O-1,S-1,1000,900,300,400,finance\n"
        "O-2,S-2,1000,900,-1,400,finance\n"
    )

    assert len(preview.rows) == 1
    assert len(preview.errors) == 1


def test_reconciliation_preview_requires_contract_headers() -> None:
    with pytest.raises(ProfitReconciliationError, match="缺少字段"):
        preview_profit_reconciliation_csv("order_id,sku_id\nO-1,S-1\n")
