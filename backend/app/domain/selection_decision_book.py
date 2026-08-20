"""说明本模块的职责、边界和主要协作对象。"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SelectionDecisionBook:
    """说明 SelectionDecisionBook 的职责、状态边界和对外协作关系。"""
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
    """说明 SelectionDecisionBookGateway 的职责、状态边界和对外协作关系。"""
    async def save_book(
        self, *, workspace_id: str, book: SelectionDecisionBook
    ) -> SelectionDecisionBook:
        """执行 save_book 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    book: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""

    async def list_books(
        self, *, workspace_id: str, limit: int
    ) -> list[SelectionDecisionBook]:
        """执行 list_books 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""


def validate_decision_book(book: SelectionDecisionBook) -> None:
    """执行 validate_decision_book 的业务流程并返回该流程的结果。

Args:
    book: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
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
    """执行 validate_confirmation_status 的业务流程并返回该流程的结果。

Args:
    status: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    ValueError: 业务约束或外部依赖失败时抛出。
"""
    if status not in {"confirmed", "rejected"}:
        raise ValueError("人工确认状态必须是 confirmed 或 rejected")
