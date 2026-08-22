"""库存、订单和履约事实的质量检查编排器。"""

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, Protocol

from backend.app.domain.customer_order import CustomerOrderPage
from backend.app.domain.data_quality import QualityCheckJob, QualityFinding
from backend.app.domain.operational_quality import (
    check_order_record,
    check_posting_record,
    check_stock_record,
)
from backend.app.domain.posting import PostingPage
from backend.app.domain.stock_position import StockPositionPage


class StockReader(Protocol):
    async def list_stock_positions(
        self, *, workspace_id: str, cursor: str | None, limit: int
    ) -> StockPositionPage: ...


class OrderReader(Protocol):
    async def list_customer_orders(
        self, *, workspace_id: str, cursor: str | None, limit: int
    ) -> CustomerOrderPage: ...


class PostingReader(Protocol):
    async def list_postings(
        self, *, workspace_id: str, cursor: str | None, limit: int
    ) -> PostingPage: ...


class OperationalQualityRunner:
    """分页读取三类事实并执行规则；重复游标立即熔断，防止任务死循环。"""

    def __init__(
        self,
        stocks: StockReader,
        orders: OrderReader,
        postings: PostingReader,
        *,
        page_size: int = 100,
    ) -> None:
        if not 1 <= page_size <= 500:
            raise ValueError("质量检查页大小必须在 1 到 500 之间")
        self._stocks, self._orders, self._postings, self._page_size = (
            stocks,
            orders,
            postings,
            page_size,
        )

    async def run(self, job: QualityCheckJob) -> list[QualityFinding]:
        findings: list[QualityFinding] = []
        findings.extend(await self._stocks_findings(job))
        findings.extend(await self._orders_findings(job))
        findings.extend(await self._postings_findings(job))
        return _deduplicate(findings)

    async def _stocks_findings(self, job: QualityCheckJob) -> list[QualityFinding]:
        result: list[QualityFinding] = []
        async for page in _pages(
            lambda cursor: self._stocks.list_stock_positions(
                workspace_id=job.workspace_id, cursor=cursor, limit=self._page_size
            )
        ):
            for item in page.items:
                result.extend(check_stock_record(item.model_dump()))
        return result

    async def _orders_findings(self, job: QualityCheckJob) -> list[QualityFinding]:
        result: list[QualityFinding] = []
        async for page in _pages(
            lambda cursor: self._orders.list_customer_orders(
                workspace_id=job.workspace_id, cursor=cursor, limit=self._page_size
            )
        ):
            for item in page.items:
                result.extend(check_order_record(item.model_dump()))
        return result

    async def _postings_findings(self, job: QualityCheckJob) -> list[QualityFinding]:
        result: list[QualityFinding] = []
        async for page in _pages(
            lambda cursor: self._postings.list_postings(
                workspace_id=job.workspace_id, cursor=cursor, limit=self._page_size
            )
        ):
            for item in page.items:
                result.extend(check_posting_record(item.model_dump()))
        return result


async def _pages(loader: Callable[[str | None], Awaitable[Any]]) -> AsyncIterator[Any]:
    cursor: str | None = None
    seen: set[str] = set()
    while True:
        page = await loader(cursor)
        yield page
        if page.next_cursor is None:
            return
        if page.next_cursor in seen:
            raise ValueError("运营事实质量检查游标重复，已停止以防止死循环")
        seen.add(page.next_cursor)
        cursor = page.next_cursor


def _deduplicate(findings: list[QualityFinding]) -> list[QualityFinding]:
    result: list[QualityFinding] = []
    seen: set[tuple[str, str, str]] = set()
    for finding in findings:
        key = (finding.rule_code, finding.field_name, finding.message)
        if key not in seen:
            seen.add(key)
            result.append(finding)
    return result
