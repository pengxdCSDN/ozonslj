"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class CompetitorObservation:
    """说明 CompetitorObservation 的职责、状态边界和对外协作关系。"""
    seller: str
    brand: str | None
    price_minor: int
    rating: float | None
    review_count: int


@dataclass(frozen=True, slots=True)
class CompetitionAnalysis:
    """说明 CompetitionAnalysis 的职责、状态边界和对外协作关系。"""
    sample_count: int
    competition_score: float
    median_price_minor: int | None
    price_band_low_minor: int | None
    price_band_high_minor: int | None
    seller_concentration_percent: float
    brand_concentration_percent: float
    estimated: bool
    caveat: str


class CompetitionAnalysisGateway(Protocol):
    """说明 CompetitionAnalysisGateway 的职责、状态边界和对外协作关系。"""
    async def save_analysis(
        self, *, workspace_id: str, analysis: CompetitionAnalysis
    ) -> CompetitionAnalysis:
        """执行 save_analysis 的业务流程并返回该流程的结果。"""

    async def list_analyses(
        self, *, workspace_id: str, limit: int
    ) -> list[CompetitionAnalysis]:
        """执行 list_analyses 的业务流程并返回该流程的结果。"""


def analyze_competition(items: list[CompetitorObservation]) -> CompetitionAnalysis:
    """执行 analyze_competition 的业务流程并返回该流程的结果。"""
    if not items:
        return CompetitionAnalysis(
            0, 0.0, None, None, None, 0.0, 0.0, True, "没有公开样本，无法判断竞争度"
        )
    prices = sorted(item.price_minor for item in items)
    sellers = _concentration([item.seller for item in items])
    brands = _concentration([item.brand for item in items if item.brand])
    review_signal = min(sum(item.review_count for item in items) / max(len(items) * 1000, 1), 1.0)
    rating_signal = sum((item.rating or 0) / 5 for item in items) / len(items)
    concentration_signal = (sellers + brands) / 200
    score = round(
        min((review_signal * 45 + rating_signal * 35 + concentration_signal * 20), 100),
        2,
    )
    caveat = (
        "样本少于 3 个，仅能作为低置信度趋势估算"
        if len(items) < 3
        else "公开样本只用于竞争趋势估算，不代表全市场精确排名"
    )
    return CompetitionAnalysis(
        len(items), score, prices[len(prices) // 2], prices[0], prices[-1], sellers, brands, True,
        caveat,
    )


def _concentration(values: list[str]) -> float:
    """执行内部步骤 _concentration，供同一模块的公开流程复用。"""
    if not values:
        return 0.0
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return round(max(counts.values()) / len(values) * 100, 2)
