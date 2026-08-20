"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SalesAnalysis:
    """说明 SalesAnalysis 的职责、状态边界和对外协作关系。"""
    current_sales_minor: int
    previous_sales_minor: int
    change_percent: float | None
    current_orders: int
    previous_orders: int
    order_change_percent: float | None
    anomalies: list[str]
    opportunities: list[str]
    incomplete: bool
    read_only: bool


class SalesAnalysisGateway(Protocol):
    """说明 SalesAnalysisGateway 的职责、状态边界和对外协作关系。"""
    async def save_report(
        self, *, workspace_id: str, report: SalesAnalysis
    ) -> SalesAnalysis:
        """执行 save_report 的业务流程并返回该流程的结果。"""

    async def list_reports(
        self, *, workspace_id: str, limit: int
    ) -> list[SalesAnalysis]:
        """执行 list_reports 的业务流程并返回该流程的结果。"""


def analyze_sales(
    *, current_sales_minor: int, previous_sales_minor: int,
    current_orders: int, previous_orders: int,
    current_window: str, previous_window: str,
) -> SalesAnalysis:
    """执行 analyze_sales 的业务流程并返回该流程的结果。"""
    values = (current_sales_minor, previous_sales_minor, current_orders, previous_orders)
    if (
        any(isinstance(value, bool) or not isinstance(value, int) for value in values)
        or min(values) < 0
        or not current_window.strip()
        or not previous_window.strip()
    ):
        raise ValueError("销售分析输入无效")
    change = _change(current_sales_minor, previous_sales_minor)
    order_change = _change(current_orders, previous_orders)
    anomalies: list[str] = []
    opportunities: list[str] = []
    if change is not None and change <= -20:
        anomalies.append("销售额较上一窗口下降 20% 以上")
    if order_change is not None and order_change <= -20:
        anomalies.append("订单量较上一窗口下降 20% 以上")
    if change is not None and change >= 20:
        opportunities.append("销售额增长明显，建议复核库存与广告承接能力")
    if current_orders > 0 and current_sales_minor / current_orders > 0:
        opportunities.append("存在可追踪的客单价变化机会")
    return SalesAnalysis(
        current_sales_minor, previous_sales_minor, change, current_orders,
        previous_orders, order_change, anomalies, opportunities,
        current_sales_minor == 0 and current_orders == 0, True,
    )


def _change(current: int, previous: int) -> float | None:
    """执行内部步骤 _change，供同一模块的公开流程复用。"""
    return (current - previous) / previous * 100 if previous else None
