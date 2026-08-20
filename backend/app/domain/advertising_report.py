"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AdvertisingReportRow:
    """说明 AdvertisingReportRow 的职责、状态边界和对外协作关系。"""
    campaign_id: str
    report_date: date
    impressions: int
    clicks: int
    orders: int
    sales_minor: int
    spend_minor: int
    currency: str
    source: str = "performance_api"


class AdvertisingReportGateway(Protocol):
    """说明 AdvertisingReportGateway 的职责、状态边界和对外协作关系。"""
    async def save_rows(
        self, *, workspace_id: str, rows: list[AdvertisingReportRow]
    ) -> list[AdvertisingReportRow]:
        """执行 save_rows 的业务流程并返回该流程的结果。"""

    async def list_rows(
        self, *, workspace_id: str, limit: int
    ) -> list[AdvertisingReportRow]:
        """执行 list_rows 的业务流程并返回该流程的结果。"""


def normalize_advertising_report(raw: dict[str, object]) -> AdvertisingReportRow:
    """将 Performance API 报表行映射为内部模型，并拒绝不可信的指标组合。"""
    campaign_id = str(raw.get("campaign_id", "")).strip()
    if not campaign_id:
        raise ValueError("广告报表必须包含活动标识")
    currency = str(raw.get("currency", "RUB")).strip().upper()
    if len(currency) != 3 or not currency.isalpha():
        raise ValueError("币种必须是三位字母代码")

    fields = ("impressions", "clicks", "orders", "sales_minor", "spend_minor")
    values: dict[str, int] = {}
    for field in fields:
        value = raw.get(field, 0)
        if isinstance(value, bool) or not isinstance(value, (int, str)):
            raise ValueError(f"{field} 必须是整数")
        try:
            values[field] = int(value)
        except ValueError as error:
            raise ValueError(f"{field} 必须是整数") from error
    if any(value < 0 for value in values.values()):
        raise ValueError("广告报表指标不能为负数")
    if values["clicks"] > values["impressions"]:
        raise ValueError("点击数不能超过展示数")
    if values["orders"] > values["clicks"]:
        raise ValueError("订单数不能超过点击数")
    return AdvertisingReportRow(
        campaign_id=campaign_id,
        report_date=date.fromisoformat(str(raw["report_date"])),
        impressions=values["impressions"],
        clicks=values["clicks"],
        orders=values["orders"],
        sales_minor=values["sales_minor"],
        spend_minor=values["spend_minor"],
        currency=currency,
    )
