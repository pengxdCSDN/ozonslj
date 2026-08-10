from dataclasses import dataclass
from datetime import date, timedelta
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AdvertisingCalendarDay:
    day: int
    date: date
    phase: str
    recommendation: str
    read_only: bool


class AdvertisingCalendarGateway(Protocol):
    async def save_calendar(
        self, *, workspace_id: str, start_date: date,
        days: list[AdvertisingCalendarDay]
    ) -> list[AdvertisingCalendarDay]: ...

    async def list_calendars(
        self, *, workspace_id: str, limit: int
    ) -> list[list[AdvertisingCalendarDay]]: ...


def build_advertising_calendar(start_date: date) -> list[AdvertisingCalendarDay]:
    """生成新品前 30 天建议；只描述动作，不执行预算或出价变更。"""
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
