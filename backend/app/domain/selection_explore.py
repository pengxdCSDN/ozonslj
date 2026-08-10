from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ExploreInput:
    keyword: str
    search_count: int
    conversion_rate: float | None
    sample_count: int
    median_price_minor: int | None
    own_stock: int
    own_sales: int


@dataclass(frozen=True, slots=True)
class ExploreOpportunity:
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
    async def save_opportunities(
        self, *, workspace_id: str, opportunities: list[ExploreOpportunity]
    ) -> list[ExploreOpportunity]: ...

    async def list_opportunities(
        self, *, workspace_id: str, limit: int
    ) -> list[ExploreOpportunity]: ...


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
