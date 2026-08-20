"""说明本模块的职责、边界和主要协作对象。"""

import math
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AdvertisingAnalysis:
    """说明 AdvertisingAnalysis 的职责、状态边界和对外协作关系。"""
    acos_percent: float | None
    tacos_percent: float | None
    roi_percent: float | None
    anomalies: list[str]
    recommendations: list[str]
    incomplete: bool
    read_only: bool


class AdvertisingAnalysisGateway(Protocol):
    """说明 AdvertisingAnalysisGateway 的职责、状态边界和对外协作关系。"""
    async def save_report(
        self, *, workspace_id: str, report: AdvertisingAnalysis
    ) -> AdvertisingAnalysis:
        """执行 save_report 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    report: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def list_reports(
        self, *, workspace_id: str, limit: int
    ) -> list[AdvertisingAnalysis]:
        """执行 list_reports 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""


def analyze_advertising(
    *, spend_minor: int, ad_sales_minor: int, total_sales_minor: int,
    keyword_count: int, unconverted_keyword_count: int,
    acos_alert_percent: float,
) -> AdvertisingAnalysis:
    """执行 analyze_advertising 的业务流程并返回该流程的结果。

Args:
    spend_minor: 参数语义、输入边界和安全约束。
    ad_sales_minor: 参数语义、输入边界和安全约束。
    total_sales_minor: 参数语义、输入边界和安全约束。
    keyword_count: 参数语义、输入边界和安全约束。
    unconverted_keyword_count: 参数语义、输入边界和安全约束。
    acos_alert_percent: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
    values = (
        spend_minor, ad_sales_minor, total_sales_minor,
        keyword_count, unconverted_keyword_count,
    )
    if (
        any(isinstance(value, bool) or not isinstance(value, int) for value in values)
        or min(values) < 0
        or isinstance(acos_alert_percent, bool)
        or not isinstance(acos_alert_percent, (int, float))
        or not math.isfinite(acos_alert_percent)
        or acos_alert_percent < 0
        or unconverted_keyword_count > keyword_count
    ):
        raise ValueError("广告分析输入无效")
    acos = spend_minor / ad_sales_minor * 100 if ad_sales_minor else None
    tacos = spend_minor / total_sales_minor * 100 if total_sales_minor else None
    roi = ad_sales_minor / spend_minor * 100 if spend_minor else None
    anomalies: list[str] = []
    recommendations: list[str] = []
    if acos is not None and acos >= acos_alert_percent:
        anomalies.append("ACOS 达到或超过告警阈值")
        recommendations.append("复核高花费词、转化率和商品承接能力")
    if unconverted_keyword_count:
        anomalies.append("存在高费无转化关键词")
        recommendations.append("将高费无转化词加入人工否定词候选复核")
    if not anomalies:
        recommendations.append("当前广告指标未触发配置告警")
    return AdvertisingAnalysis(
        acos, tacos, roi, anomalies, recommendations,
        ad_sales_minor == 0 and total_sales_minor == 0, True,
    )
