"""Performance 广告预算只读分析。"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AdvertisingBudgetAnalysis:
    """说明 AdvertisingBudgetAnalysis 的职责、状态边界和对外协作关系。"""
    budget_minor: int
    spend_minor: int
    days_elapsed: int
    days_total: int
    utilization_percent: float
    projected_spend_minor: int
    projected_utilization_percent: float
    status: str
    recommendations: list[str]
    read_only: bool


def analyze_advertising_budget(
    *, budget_minor: int, spend_minor: int, days_elapsed: int, days_total: int,
) -> AdvertisingBudgetAnalysis:
    """执行 analyze_advertising_budget 的业务流程并返回该流程的结果。"""
    values = (budget_minor, spend_minor, days_elapsed, days_total)
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        raise ValueError("广告预算分析输入无效")
    if budget_minor <= 0 or spend_minor < 0 or days_elapsed < 1 or days_total < 1:
        raise ValueError("广告预算和统计天数必须为正，花费不能为负")
    if days_elapsed > days_total:
        raise ValueError("已用天数不能超过预算周期")
    utilization = spend_minor / budget_minor * 100
    projected = round(spend_minor / days_elapsed * days_total)
    projected_utilization = projected / budget_minor * 100
    if utilization >= 100:
        status = "exceeded"
        recommendations = ["预算已用尽，暂停自动放量并人工复核活动"]
    elif projected_utilization >= 100:
        status = "at_risk"
        recommendations = ["按当前消耗速度预计超预算，人工复核出价和活动分配"]
    elif projected_utilization >= 90:
        status = "warning"
        recommendations = ["预计接近预算上限，持续观察消耗速度"]
    else:
        status = "healthy"
        recommendations = ["当前消耗速度未显示预算风险"]
    return AdvertisingBudgetAnalysis(
        budget_minor, spend_minor, days_elapsed, days_total,
        utilization, projected, projected_utilization, status, recommendations, True,
    )
