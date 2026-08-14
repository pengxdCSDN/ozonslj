from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SelectionDecisionBook:
    opportunity_summary: str
    customer_scene: str
    market_sample: str
    competitor_snapshots: tuple[str, ...]
    profit_calculation: str
    risks: tuple[str, ...]
    price_range: str
    stock_recommendation: str
    seed_keywords: tuple[str, ...]
    data_sources: tuple[str, ...]
    uncertainty: str
    confirmation_status: str


class SelectionDecisionBookGateway(Protocol):
    async def save_book(
        self, *, workspace_id: str, book: SelectionDecisionBook
    ) -> SelectionDecisionBook: ...

    async def list_books(
        self, *, workspace_id: str, limit: int
    ) -> list[SelectionDecisionBook]: ...


def validate_decision_book(book: SelectionDecisionBook) -> None:
    required_text = (
        book.opportunity_summary, book.customer_scene, book.market_sample,
        book.profit_calculation, book.price_range, book.stock_recommendation,
        book.uncertainty,
    )
    if any(not value.strip() for value in required_text):
        raise ValueError("商品立项决策书固定章节不能缺失")
    if not book.competitor_snapshots or not book.seed_keywords or not book.data_sources:
        raise ValueError("决策书必须包含竞品、种子关键词和数据来源")


def validate_confirmation_status(status: str) -> None:
    if status not in {"confirmed", "rejected"}:
        raise ValueError("人工确认状态必须是 confirmed 或 rejected")
