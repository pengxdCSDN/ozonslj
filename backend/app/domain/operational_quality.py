"""库存、订单和履约事实的通用质量规则。

规则只检查已脱敏的领域模型，不调用外部接口，也不修改业务事实；发现的问题交给
质量隔离区处理，避免异常数据静默进入利润、库存或履约分析。
"""

from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from backend.app.domain.data_quality import QualityFinding


def check_stock_record(record: Mapping[str, Any]) -> list[QualityFinding]:
    """检查库存键、履约方式和数量边界。"""
    findings: list[QualityFinding] = []
    for field in ("offer_id", "warehouse_id", "fulfillment_type"):
        if not str(record.get(field) or "").strip():
            findings.append(QualityFinding(
                rule_code="DQ-009-STOCK-MISSING", field_name=field, severity="error",
                message="库存必填标识缺失",
            ))
    if record.get("fulfillment_type") not in {"FBO", "FBS"}:
        findings.append(QualityFinding(
            rule_code="DQ-009-STOCK-ENUM", field_name="fulfillment_type", severity="error",
            message="履约方式不在允许范围内",
        ))
    for field in ("available_quantity", "reserved_quantity"):
        value = record.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            findings.append(QualityFinding(
                rule_code="DQ-009-STOCK-AMOUNT", field_name=field, severity="error",
                message="库存数量必须是非负整数",
            ))
    return findings


def check_order_record(record: Mapping[str, Any]) -> list[QualityFinding]:
    """检查订单标识、状态、币种、金额和时间。"""
    findings: list[QualityFinding] = []
    for field in ("order_id", "ozon_order_id", "status"):
        if not str(record.get(field) or "").strip():
            findings.append(QualityFinding(
                rule_code="DQ-010-ORDER-MISSING", field_name=field, severity="error",
                message="订单必填标识缺失",
            ))
    currency = record.get("currency")
    if not isinstance(currency, str) or len(currency) != 3 or not currency.isupper():
        findings.append(QualityFinding(
            rule_code="DQ-010-ORDER-CURRENCY", field_name="currency", severity="error",
            message="订单币种必须是三位大写代码",
        ))
    amount = record.get("total_amount")
    try:
        parsed_amount = Decimal(str(amount))
    except (InvalidOperation, ValueError, TypeError):
        parsed_amount = Decimal("-1")
    if amount is None or parsed_amount < 0:
        findings.append(QualityFinding(
            rule_code="DQ-010-ORDER-AMOUNT", field_name="total_amount", severity="error",
            message="订单金额必须是非负数",
        ))
    if not isinstance(record.get("ordered_at"), datetime):
        findings.append(QualityFinding(
            rule_code="DQ-010-ORDER-TIME", field_name="ordered_at", severity="error",
            message="订单时间必须是有效时间",
        ))
    return findings


def check_posting_record(record: Mapping[str, Any]) -> list[QualityFinding]:
    """检查履约单关联、履约方式、数量和日期边界。"""
    findings: list[QualityFinding] = []
    for field in ("posting_id", "ozon_posting_number", "status"):
        if not str(record.get(field) or "").strip():
            findings.append(QualityFinding(
                rule_code="DQ-011-POSTING-MISSING", field_name=field, severity="error",
                message="履约单必填标识缺失",
            ))
    if record.get("fulfillment_type") not in {"FBO", "FBS"}:
        findings.append(QualityFinding(
            rule_code="DQ-011-POSTING-ENUM", field_name="fulfillment_type", severity="error",
            message="履约方式不在允许范围内",
        ))
    for field in ("item_count", "total_quantity"):
        value = record.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            findings.append(QualityFinding(
                rule_code="DQ-011-POSTING-AMOUNT", field_name=field, severity="error",
                message="履约数量必须是非负整数",
            ))
    shipment_date = record.get("shipment_date")
    if shipment_date is not None and not isinstance(shipment_date, date):
        findings.append(QualityFinding(
            rule_code="DQ-011-POSTING-DATE", field_name="shipment_date", severity="error",
            message="发货日期格式无效",
        ))
    return findings
