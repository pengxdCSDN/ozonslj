"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AdvertisingCalendarDay:
    """说明 AdvertisingCalendarDay 的职责、状态边界和对外协作关系。"""
    day: int
    date: date
    phase: str
    recommendation: str
    read_only: bool


class AdvertisingCalendarGateway(Protocol):
    """说明 AdvertisingCalendarGateway 的职责、状态边界和对外协作关系。"""
    async def save_calendar(
        self, *, workspace_id: str, start_date: date,
        days: list[AdvertisingCalendarDay]
    ) -> list[AdvertisingCalendarDay]:
        """执行 save_calendar 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    start_date: 参数语义、输入边界和安全约束。
    days: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def list_calendars(
        self, *, workspace_id: str, limit: int
    ) -> list[list[AdvertisingCalendarDay]]:
        """执行 list_calendars 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""


def build_advertising_calendar(start_date: date) -> list[AdvertisingCalendarDay]:
    """生成新品前 30 天建议；只描述动作，不执行预算或出价变更。

Args:
    start_date: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""
    result: list[AdvertisingCalendarDay] = []
    for day in range(1, 31):
        if day <= 7:
            phase, recommendation = "testing", "测试关键词与素材，记录展示、点击和转化"
        elif day <= 14:
            phase, recommendation = "filtering", "筛选有效词，标记高费无转化词供人工复核"
        elif day <= 21:
            phase, recommendation = "scaling", "评估放量候选词，人工确认预算调整方案"
        else:
            phase, recommendation = "optimizing", "复盘 ACOS、TACOS 与 ROI，形成下一周期建议"
        result.append(AdvertisingCalendarDay(
            day, start_date + timedelta(days=day - 1), phase, recommendation, True
        ))
    return result
