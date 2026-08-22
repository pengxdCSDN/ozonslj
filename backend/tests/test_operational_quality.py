from datetime import datetime
from decimal import Decimal

from backend.app.domain.operational_quality import (
    check_order_record,
    check_posting_record,
    check_stock_record,
)


def test_stock_quality_rejects_negative_and_unknown_fulfillment() -> None:
    findings = check_stock_record({
        "offer_id": "sku-1", "warehouse_id": "w-1", "fulfillment_type": "X",
        "available_quantity": -1, "reserved_quantity": 0,
    })
    assert {item.rule_code for item in findings} == {"DQ-009-STOCK-ENUM", "DQ-009-STOCK-AMOUNT"}


def test_order_quality_accepts_valid_deidentified_order() -> None:
    findings = check_order_record({
        "order_id": "o-1", "ozon_order_id": "oz-1", "status": "delivered",
        "currency": "RUB", "total_amount": Decimal("10"), "ordered_at": datetime.now(),
    })
    assert findings == []


def test_posting_quality_rejects_invalid_quantities_and_date() -> None:
    findings = check_posting_record({
        "posting_id": "p-1", "ozon_posting_number": "p-1", "status": "awaiting",
        "fulfillment_type": "FBS", "item_count": -1, "total_quantity": 2,
        "shipment_date": "bad",
    })
    assert {item.rule_code for item in findings} == {"DQ-011-POSTING-AMOUNT", "DQ-011-POSTING-DATE"}
