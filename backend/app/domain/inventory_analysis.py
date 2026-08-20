"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class InventoryAnalysis:
    """说明 InventoryAnalysis 的职责、状态边界和对外协作关系。"""
    available_units: int
    inbound_units: int
    average_daily_sales: float
    days_of_cover: float | None
    stockout_risk: bool
    overstock_risk: bool
    recommendations: list[str]
    incomplete: bool
    read_only: bool


class InventoryAnalysisGateway(Protocol):
    """说明 InventoryAnalysisGateway 的职责、状态边界和对外协作关系。"""
    async def save_report(
        self, *, workspace_id: str, report: InventoryAnalysis
    ) -> InventoryAnalysis:
        """执行 save_report 的业务流程并返回该流程的结果。"""

    async def list_reports(
        self, *, workspace_id: str, limit: int
    ) -> list[InventoryAnalysis]:
        """执行 list_reports 的业务流程并返回该流程的结果。"""


def analyze_inventory(
    *, available_units: int, inbound_units: int, average_daily_sales: float,
    safety_days: int, overstock_days: int,
) -> InventoryAnalysis:
    """执行 analyze_inventory 的业务流程并返回该流程的结果。"""
    integer_values = (available_units, inbound_units, safety_days, overstock_days)
    if (
        any(isinstance(value, bool) or not isinstance(value, int) for value in integer_values)
        or isinstance(average_daily_sales, bool)
        or not isinstance(average_daily_sales, (int, float))
        or min(available_units, inbound_units, average_daily_sales, safety_days, overstock_days) < 0
        or safety_days > overstock_days
    ):
        raise ValueError("库存分析输入不能为负数")
    cover = available_units / average_daily_sales if average_daily_sales else None
    stockout = cover is not None and cover < safety_days
    overstock = cover is not None and cover > overstock_days
    recommendations: list[str] = []
    if stockout:
        recommendations.append("库存覆盖天数低于安全线，建议复核补货和在途计划")
    if overstock:
        recommendations.append("库存覆盖天数超过积压线，建议复核促销或采购节奏")
    if inbound_units and stockout:
        recommendations.append("在途库存存在，建议核对预计到仓时间")
    if not recommendations:
        recommendations.append("当前库存覆盖处于配置阈值范围内")
    return InventoryAnalysis(
        available_units, inbound_units, average_daily_sales, cover,
        stockout, overstock, recommendations,
        average_daily_sales == 0, True,
    )
