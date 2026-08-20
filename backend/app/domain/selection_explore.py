"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ExploreInput:
    """说明 ExploreInput 的职责、状态边界和对外协作关系。"""
    keyword: str
    search_count: int
    conversion_rate: float | None
    sample_count: int
    median_price_minor: int | None
    own_stock: int
    own_sales: int


@dataclass(frozen=True, slots=True)
class ExploreOpportunity:
    """说明 ExploreOpportunity 的职责、状态边界和对外协作关系。"""
    keyword: str
    score: float
    search_count: int
    conversion_rate: float | None
    sample_count: int
    median_price_minor: int | None
    own_coverage_gap: bool
    estimated: bool
    reasons: tuple[str, ...]
    missing_inputs: tuple[str, ...]


class ExploreOpportunityGateway(Protocol):
    """说明 ExploreOpportunityGateway 的职责、状态边界和对外协作关系。"""

    async def save_opportunities(
        self, *, workspace_id: str, opportunities: list[ExploreOpportunity]
    ) -> list[ExploreOpportunity]:
        """执行 save_opportunities 的业务流程并返回该流程的结果。"""

    async def list_opportunities(
        self, *, workspace_id: str, limit: int
    ) -> list[ExploreOpportunity]:
        """读取指定工作区已保存的选品机会快照。"""


@dataclass(frozen=True, slots=True)
class ExploreFilters:
    """Operator-controlled candidate filters applied after a deterministic score."""

    min_score: float = 0.0
    min_search_count: int = 0
    min_conversion_rate: float | None = None
    coverage_gap_only: bool = False


def filter_opportunities(
    opportunities: list[ExploreOpportunity], filters: ExploreFilters
) -> list[ExploreOpportunity]:
    """Filter scored opportunities without changing the score or source facts."""
    return [
        item
        for item in opportunities
        if item.score >= filters.min_score
        and item.search_count >= filters.min_search_count
        and (
            filters.min_conversion_rate is None
            or (
                item.conversion_rate is not None
                and item.conversion_rate >= filters.min_conversion_rate
            )
        )
        and (not filters.coverage_gap_only or item.own_coverage_gap)
    ]

def explore_opportunities(items: list[ExploreInput]) -> list[ExploreOpportunity]:
    """融合搜索热度、公开样本和自有覆盖缺口，生成可复核的机会候选。"""
    if not items:
        return []
    max_search = max(item.search_count for item in items) or 1
    results: list[ExploreOpportunity] = []
    for item in items:
        heat = min(item.search_count / max_search, 1.0)
        conversion = min(max(item.conversion_rate or 0.0, 0.0) / 100, 1.0)
        sample_signal = min(item.sample_count / 10, 1.0)
        gap = item.own_stock == 0 and item.own_sales == 0
        score = round(heat * 60 + conversion * 25 + sample_signal * 15, 2)
        reasons = ["搜索热度较高" if heat >= 0.6 else "搜索热度待验证"]
        missing: list[str] = []
        if item.conversion_rate is None:
            missing.append("conversion_rate")
        if item.sample_count == 0:
            missing.append("public_sample")
        if item.median_price_minor is None:
            missing.append("median_price_minor")
        if item.sample_count:
            reasons.append(f"已有 {item.sample_count} 个公开样本")
        if gap:
            reasons.append("自有商品覆盖缺口")
        results.append(
            ExploreOpportunity(
                item.keyword,
                score,
                item.search_count,
                item.conversion_rate,
                item.sample_count,
                item.median_price_minor,
                gap,
                True,
                tuple(reasons),
                tuple(missing),
            )
        )
    return sorted(results, key=lambda result: (-result.score, result.keyword))
