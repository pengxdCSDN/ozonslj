from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AdvertisingKeywordDiagnosis:
    keyword: str
    category: str
    impressions: int
    clicks: int
    orders: int
    spend_minor: int
    sales_minor: int
    ctr_percent: float | None
    cvr_percent: float | None
    acos_percent: float | None
    reason: str
    read_only: bool


class AdvertisingKeywordDiagnosisGateway(Protocol):
    async def save_report(
        self, *, workspace_id: str, diagnoses: list[AdvertisingKeywordDiagnosis]
    ) -> list[AdvertisingKeywordDiagnosis]: ...

    async def list_reports(
        self, *, workspace_id: str, limit: int
    ) -> list[list[AdvertisingKeywordDiagnosis]]: ...


def diagnose_keywords(
    rows: list[dict[str, object]],
    *,
    min_impressions: int = 100,
    min_clicks: int = 10,
    high_cvr_percent: float = 8.0,
    high_spend_minor: int = 1000,
) -> list[AdvertisingKeywordDiagnosis]:
    """按可解释规则分类关键词；结果只生成诊断建议，不产生广告写操作。"""
    thresholds = (min_impressions, min_clicks, high_spend_minor)
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in thresholds
    ):
        raise ValueError("关键词诊断整数阈值必须是非负整数")
    if isinstance(high_cvr_percent, bool) or high_cvr_percent < 0:
        raise ValueError("高 CVR 阈值必须是非负数")
    result: list[AdvertisingKeywordDiagnosis] = []
    for row in rows:
        keyword = str(row.get("keyword", "")).strip()
        impressions = _integer(row, "impressions")
        clicks = _integer(row, "clicks")
        orders = _integer(row, "orders")
        spend = _integer(row, "spend_minor")
        sales = _integer(row, "sales_minor")
        if not keyword or min(impressions, clicks, orders, spend, sales) < 0:
            raise ValueError("关键词诊断输入无效")
        if clicks > impressions or orders > clicks:
            raise ValueError("关键词指标关系不成立")
        ctr = clicks / impressions * 100 if impressions else None
        cvr = orders / clicks * 100 if clicks else None
        acos = spend / sales * 100 if sales else None
        if spend >= high_spend_minor and orders == 0:
            category, reason = "high_spend_no_conversion", "花费达到阈值但没有订单"
        elif (
            impressions >= min_impressions
            and clicks >= min_clicks
            and (cvr or 0) >= high_cvr_percent
        ):
            category, reason = "high_cvr", "点击量和转化率达到高 CVR 条件"
        elif impressions >= min_impressions and clicks >= min_clicks and orders > 0:
            category, reason = "star", "有稳定流量和订单，适合重点观察"
        else:
            category, reason = "potential", "当前样本不足或仍需积累数据"
        result.append(AdvertisingKeywordDiagnosis(
            keyword=keyword, category=category, impressions=impressions, clicks=clicks,
            orders=orders, spend_minor=spend, sales_minor=sales, ctr_percent=ctr,
            cvr_percent=cvr, acos_percent=acos, reason=reason, read_only=True,
        ))
    return result


def _integer(row: dict[str, object], name: str) -> int:
    value = row.get(name, 0)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{name} 必须是整数")
    return value
