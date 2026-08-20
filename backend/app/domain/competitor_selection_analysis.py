"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class CompetitorSelectionAnalysis:
    """说明 CompetitorSelectionAnalysis 的职责、状态边界和对外协作关系。"""
    sample_count: int
    opportunity_count: int
    estimated: bool
    caveat: str
    highlights: list[str]
    recommendations: list[str]
    read_only: bool


class CompetitorSelectionAnalysisGateway(Protocol):
    """说明 CompetitorSelectionAnalysisGateway 的职责、状态边界和对外协作关系。"""
    async def save_report(
        self, *, workspace_id: str, report: CompetitorSelectionAnalysis
    ) -> CompetitorSelectionAnalysis:
        """执行 save_report 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    report: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def list_reports(
        self, *, workspace_id: str, limit: int
    ) -> list[CompetitorSelectionAnalysis]:
        """执行 list_reports 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""


def analyze_competitor_selection(
    *, sample_count: int, opportunity_count: int,
    median_price_minor: int | None, top_competitor_rating: float | None,
    source_window: str,
) -> CompetitorSelectionAnalysis:
    """执行 analyze_competitor_selection 的业务流程并返回该流程的结果。

Args:
    sample_count: 参数语义、输入边界和安全约束。
    opportunity_count: 参数语义、输入边界和安全约束。
    median_price_minor: 参数语义、输入边界和安全约束。
    top_competitor_rating: 参数语义、输入边界和安全约束。
    source_window: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
    if (
        isinstance(sample_count, bool) or not isinstance(sample_count, int)
        or isinstance(opportunity_count, bool) or not isinstance(opportunity_count, int)
        or sample_count < 0 or opportunity_count < 0 or not source_window.strip()
    ):
        raise ValueError("竞品与选品分析输入无效")
    if median_price_minor is not None and median_price_minor < 0:
        raise ValueError("价格不能为负数")
    if (
        top_competitor_rating is not None
        and (
            isinstance(top_competitor_rating, bool)
            or not isinstance(top_competitor_rating, (int, float))
        )
    ):
        raise ValueError("评分格式无效")
    if top_competitor_rating is not None and not 0 <= top_competitor_rating <= 5:
        raise ValueError("评分必须在 0 到 5 之间")
    highlights = [f"已纳入 {sample_count} 个公开竞品样本", f"发现 {opportunity_count} 个选品机会"]
    recommendations: list[str] = []
    if sample_count < 3:
        recommendations.append("样本少于 3 个，建议补充竞品种子后再确认结论")
    if opportunity_count:
        recommendations.append("将候选机会进入 Validate 流程，补充成本与履约假设")
    else:
        recommendations.append("暂未发现候选机会，建议扩大关键词或类目探索范围")
    return CompetitorSelectionAnalysis(
        sample_count, opportunity_count, True,
        "公开页面样本仅用于估算，不代表全市场精确销量或排名",
        highlights, recommendations, True,
    )
