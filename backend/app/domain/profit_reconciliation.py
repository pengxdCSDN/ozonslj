"""把预计费用与 Ozon 订单实际费用对齐，输出可审计的差异结果。"""

import csv
import io
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


class ProfitReconciliationError(ValueError):
    """表示实际费用导入文件或对账输入违反业务约束。"""


@dataclass(frozen=True)
class ProfitReconciliationRow:
    """表示一个 SKU 或订单行的预计/实际费用对账结果。"""

    order_id: str
    sku_id: str
    estimated_profit_minor: int
    actual_profit_minor: int
    estimated_logistics_minor: int
    actual_logistics_minor: int
    variance_minor: int
    variance_percent: float | None
    source: str


@dataclass(frozen=True)
class ProfitReconciliationPreview:
    """表示实际费用 CSV 的校验结果，预览阶段不写入数据库。"""

    row_count: int
    errors: tuple[str, ...]
    rows: tuple[ProfitReconciliationRow, ...]


def preview_profit_reconciliation_csv(content: str) -> ProfitReconciliationPreview:
    """解析实际费用 CSV 并计算预计与实际利润差异。

    Args:
        content: UTF-8 CSV 文本。金额必须是最小货币单位整数，避免浮点误差。

    Returns:
        包含错误摘要和有效对账行的预览结果；存在错误时仍保留可用行。

    Raises:
        ProfitReconciliationError: CSV 为空、缺少表头或无法读取时抛出。
    """
    if not content.strip():
        raise ProfitReconciliationError("实际费用 CSV 不能为空")
    reader = csv.DictReader(io.StringIO(content))
    required = {
        "order_id", "sku_id", "estimated_profit_minor", "actual_profit_minor",
        "estimated_logistics_minor", "actual_logistics_minor", "source",
    }
    headers = set(reader.fieldnames or ())
    missing = sorted(required - headers)
    if missing:
        raise ProfitReconciliationError(f"实际费用 CSV 缺少字段: {', '.join(missing)}")

    errors: list[str] = []
    rows: list[ProfitReconciliationRow] = []
    for line_number, raw in enumerate(reader, start=2):
        try:
            order_id = _required_text(raw, "order_id")
            sku_id = _required_text(raw, "sku_id")
            estimated_profit = _minor(raw, "estimated_profit_minor", allow_negative=True)
            actual_profit = _minor(raw, "actual_profit_minor", allow_negative=True)
            estimated_logistics = _minor(raw, "estimated_logistics_minor")
            actual_logistics = _minor(raw, "actual_logistics_minor")
            source = _required_text(raw, "source")
            variance = actual_profit - estimated_profit
            percentage = (
                round(variance / estimated_profit * 100, 2)
                if estimated_profit
                else None
            )
            rows.append(ProfitReconciliationRow(
                order_id=order_id,
                sku_id=sku_id,
                estimated_profit_minor=estimated_profit,
                actual_profit_minor=actual_profit,
                estimated_logistics_minor=estimated_logistics,
                actual_logistics_minor=actual_logistics,
                variance_minor=variance,
                variance_percent=percentage,
                source=source,
            ))
        except ProfitReconciliationError as error:
            errors.append(f"第 {line_number} 行: {error}")
    return ProfitReconciliationPreview(len(rows) + len(errors), tuple(errors), tuple(rows))


def _required_text(row: dict[str, str | None], field: str) -> str:
    """读取必填文本字段并拒绝空值。"""
    value = (row.get(field) or "").strip()
    if not value:
        raise ProfitReconciliationError(f"{field} 不能为空")
    return value


def _minor(row: dict[str, str | None], field: str, *, allow_negative: bool = False) -> int:
    """读取最小货币单位整数，利润可为负，物流费用必须非负。"""
    value = (row.get(field) or "").strip()
    try:
        parsed = Decimal(value)
    except InvalidOperation as error:
        raise ProfitReconciliationError(f"{field} 必须是金额") from error
    if (not allow_negative and parsed < 0) or parsed != parsed.quantize(Decimal("1")):
        qualifier = "整数最小货币单位" if allow_negative else "非负整数最小货币单位"
        raise ProfitReconciliationError(f"{field} 必须是{qualifier}")
    return int(parsed.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
