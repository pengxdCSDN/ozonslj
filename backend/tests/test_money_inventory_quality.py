from backend.app.domain.money_inventory_quality import check_money_inventory


def test_money_inventory_checks_currency_amount_and_stock() -> None:
    findings = check_money_inventory(
        {"currency": "JPY", "price_minor": 0, "available_stock": -1},
        allowed_currencies={"RUB"},
    )
    assert {finding.rule_code for finding in findings} == {
        "DQ-005-CURRENCY", "DQ-005-AMOUNT", "DQ-005-STOCK"
    }
