from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True, slots=True)
class MoneyInventoryFinding:
    field: str
    rule_code: str
    message: str


def check_money_inventory(
    record: dict[str, object], *, allowed_currencies: set[str] | None = None
) -> list[MoneyInventoryFinding]:
    currencies = allowed_currencies or {"RUB", "CNY", "USD", "EUR"}
    findings: list[MoneyInventoryFinding] = []
    currency = record.get("currency")
    if currency is not None and str(currency).upper() not in currencies:
        findings.append(MoneyInventoryFinding("currency", "DQ-005-CURRENCY", "币种不在允许范围"))
    for field in ("price_minor", "cost_minor"):
        if field in record:
            try:
                amount = Decimal(str(record[field]))
            except (InvalidOperation, ValueError):
                amount = Decimal("-1")
            if amount <= 0:
                findings.append(MoneyInventoryFinding(field, "DQ-005-AMOUNT", "金额必须是正数"))
    stock = record.get("available_stock")
    if isinstance(stock, bool) or not isinstance(stock, int) or stock < 0:
        findings.append(MoneyInventoryFinding("available_stock", "DQ-005-STOCK", "库存不能为负数"))
    return findings
