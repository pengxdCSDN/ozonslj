"""把只读财务 начисления 聚合为可审计的利润对账结果。"""

from collections import defaultdict
from dataclasses import dataclass

from backend.app.domain.ozon_finance_accrual import FinanceAccrualLine


@dataclass(frozen=True)
class EstimatedProfitSnapshot:
    """预计利润快照；由利润模型产生，金额均为最小货币单位整数。"""

    order_id: str
    sku_id: str
    estimated_profit_minor: int
    estimated_logistics_minor: int


@dataclass(frozen=True)
class ActualProfitSnapshot:
    """按订单和 SKU 聚合后的实际财务结果。"""

    order_id: str
    sku_id: str
    actual_profit_minor: int
    actual_logistics_minor: int
    accrual_count: int
    source: str


def aggregate_finance_accruals(
    lines: tuple[FinanceAccrualLine, ...],
) -> tuple[ActualProfitSnapshot, ...]:
    """聚合财务明细；缺少订单或 SKU 的费用不猜测归属，直接排除并交质量中心处理。"""
    totals: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0, 0])
    sources: dict[tuple[str, str], str] = {}
    for line in lines:
        if not line.order_id or not line.sku_id:
            continue
        key = (line.order_id, line.sku_id)
        bucket = totals[key]
        bucket[0] += line.amount_minor
        if "logistics" in line.category.lower() or "shipping" in line.category.lower():
            bucket[1] += abs(line.amount_minor)
        bucket[2] += 1
        sources[key] = line.source
    return tuple(
        ActualProfitSnapshot(
            order_id=order_id,
            sku_id=sku_id,
            actual_profit_minor=profit,
            actual_logistics_minor=logistics,
            accrual_count=count,
            source=sources[(order_id, sku_id)],
        )
        for (order_id, sku_id), (profit, logistics, count) in sorted(totals.items())
    )


def reconcile_profit_snapshots(
    estimated: tuple[EstimatedProfitSnapshot, ...],
    actual: tuple[ActualProfitSnapshot, ...],
) -> dict[tuple[str, str], int]:
    """返回实际利润减预计利润的差异；缺任一侧的键不生成伪造差异。"""
    actual_by_key = {(item.order_id, item.sku_id): item for item in actual}
    return {
        (item.order_id, item.sku_id): actual_by_key[
            (item.order_id, item.sku_id)
        ].actual_profit_minor
        - item.estimated_profit_minor
        for item in estimated
        if (item.order_id, item.sku_id) in actual_by_key
    }
