"""说明本模块的职责、边界和主要协作对象。"""

import csv
from dataclasses import dataclass
from datetime import date
from io import StringIO
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ErpSupplyRecord:
    """ERP 补充事实；用于成本、采购和在途分析，不覆盖 Seller 官方事实。"""

    external_id: str
    offer_id: str
    record_type: str
    quantity: int
    amount_minor: int | None
    currency: str | None
    expected_date: date | None
    source: str = "erp_import"


class ErpAdapter(Protocol):
    """未来 ERP 实现必须通过此端口，不允许领域层依赖具体厂商 SDK。"""

    async def list_supply_records(self, *, workspace_id: str) -> list[ErpSupplyRecord]:
        """执行 list_supply_records 的业务流程并返回该流程的结果。"""


def normalize_erp_supply_record(raw: dict[str, object]) -> ErpSupplyRecord:
    """执行 normalize_erp_supply_record 的业务流程并返回该流程的结果。"""
    external_id = _text(raw, "external_id")
    offer_id = _text(raw, "offer_id")
    record_type = _text(raw, "record_type")
    if record_type not in {"purchase", "inbound", "cost"}:
        raise ValueError("ERP 记录类型必须是 purchase、inbound 或 cost")
    quantity = raw.get("quantity", 0)
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 0:
        raise ValueError("ERP 数量必须是非负整数")
    amount = raw.get("amount_minor")
    if amount is not None and (
        isinstance(amount, bool) or not isinstance(amount, int) or amount < 0
    ):
        raise ValueError("ERP 金额必须是非负整数")
    currency = raw.get("currency")
    if currency is not None and (
        not isinstance(currency, str) or len(currency.strip()) != 3
        or not currency.strip().isalpha()
    ):
        raise ValueError("ERP 币种必须是三位字母代码")
    if amount is not None and currency is None:
        # 金额没有币种就无法与 Seller 官方金额进行比较，必须在预览阶段拒绝。
        raise ValueError("ERP 金额存在时必须同时提供币种")
    expected = raw.get("expected_date")
    expected_date = None
    if expected is not None:
        if not isinstance(expected, str):
            raise ValueError("ERP 预计日期必须是 ISO 日期")
        try:
            expected_date = date.fromisoformat(expected)
        except ValueError as error:
            raise ValueError("ERP 预计日期必须是 ISO 日期") from error
    return ErpSupplyRecord(
        external_id, offer_id, record_type, quantity, amount,
        currency.strip().upper() if isinstance(currency, str) else None,
        expected_date,
    )


def parse_erp_csv(content: str) -> list[ErpSupplyRecord]:
    """解析运营导入的 ERP 补充事实；不把导入值冒充 Seller 官方事实。"""
    if not content.strip():
        raise ValueError("ERP 导入文件不能为空")
    records: list[ErpSupplyRecord] = []
    seen_ids: set[str] = set()
    for row in csv.DictReader(StringIO(content)):
        typed_row: dict[str, object] = dict(row)
        for field in ("quantity", "amount_minor"):
            value = typed_row.get(field)
            if value in (None, ""):
                typed_row[field] = 0 if field == "quantity" else None
            else:
                try:
                    typed_row[field] = int(str(value))
                except ValueError as error:
                    raise ValueError(f"ERP CSV 字段 {field} 必须是整数") from error
        record = normalize_erp_supply_record(typed_row)
        if record.external_id in seen_ids:
            raise ValueError("ERP 导入包含重复 external_id")
        seen_ids.add(record.external_id)
        records.append(record)
    if not records:
        raise ValueError("ERP 导入文件不包含有效记录")
    return records


def _text(raw: dict[str, object], field: str) -> str:
    """执行内部步骤 _text，供同一模块的公开流程复用。"""
    value = raw.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"ERP 字段 {field} 不能为空")
    return value.strip()
