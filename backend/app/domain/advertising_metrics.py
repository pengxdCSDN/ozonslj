"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AdvertisingMetrics:
    """说明 AdvertisingMetrics 的职责、状态边界和对外协作关系。"""
    acos_percent: float | None
    tacos_percent: float | None
    cpc_minor: float | None
    ctr_percent: float | None
    cvr_percent: float | None
    roi_percent: float | None
    currency: str
    window: str
    complete: bool
    formulas: dict[str, str]


class AdvertisingMetricsGateway(Protocol):
    """说明 AdvertisingMetricsGateway 的职责、状态边界和对外协作关系。"""
    async def save_snapshot(
        self, *, workspace_id: str, inputs: dict[str, object], metrics: AdvertisingMetrics
    ) -> AdvertisingMetrics:
        """执行 save_snapshot 的业务流程并返回该流程的结果。"""

    async def list_snapshots(
        self, *, workspace_id: str, limit: int
    ) -> list[AdvertisingMetrics]:
        """执行 list_snapshots 的业务流程并返回该流程的结果。"""


def calculate_advertising_metrics(
    *, impressions: int, clicks: int, orders: int, ad_sales_minor: int,
    total_sales_minor: int, spend_minor: int, currency: str, window: str,
) -> AdvertisingMetrics:
    """执行 calculate_advertising_metrics 的业务流程并返回该流程的结果。"""
    if min(impressions, clicks, orders, ad_sales_minor, total_sales_minor, spend_minor) < 0:
        raise ValueError("广告指标输入不能为负数")
    if clicks > impressions or orders > clicks:
        raise ValueError("广告指标关系不成立")
    return AdvertisingMetrics(
        acos_percent=_ratio(spend_minor, ad_sales_minor),
        tacos_percent=_ratio(spend_minor, total_sales_minor),
        cpc_minor=spend_minor / clicks if clicks else None,
        ctr_percent=clicks / impressions * 100 if impressions else None,
        cvr_percent=orders / clicks * 100 if clicks else None,
        roi_percent=ad_sales_minor / spend_minor * 100 if spend_minor else None,
        currency=currency, window=window,
        complete=all(
            value > 0 for value in (impressions, clicks, ad_sales_minor, total_sales_minor)
        ),
        formulas={
            "acos_percent": "花费 ÷ 广告销售额 × 100",
            "tacos_percent": "花费 ÷ 总销售额 × 100",
            "cpc_minor": "花费 ÷ 点击数",
            "ctr_percent": "点击数 ÷ 展示数 × 100",
            "cvr_percent": "订单数 ÷ 点击数 × 100",
            "roi_percent": "广告销售额 ÷ 花费 × 100",
        },
    )


def _ratio(numerator: int, denominator: int) -> float | None:
    """执行内部步骤 _ratio，供同一模块的公开流程复用。"""
    return numerator / denominator * 100 if denominator else None
