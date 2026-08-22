"""商品事实质量规则运行器。

只读取 PostgreSQL 已同步的商品报价事实，执行必填、枚举、价格和库存边界检查；
不修改商品、不调用 Ozon 写接口，发现问题统一写入质量隔离区。
"""

from typing import Protocol

from backend.app.domain.data_quality import (
    QualityCheckJob,
    QualityFinding,
    check_amount_and_inventory,
    check_required_and_enum,
)
from backend.app.domain.product_offer import ProductOfferPage


class ProductOfferReader(Protocol):
    """商品报价只读端口；实现可来自 PostgreSQL 或测试 Stub。"""

    async def list_product_offers(
        self, *, workspace_id: str, cursor: str | None, limit: int
    ) -> ProductOfferPage:
        """读取一页商品事实。"""


class ProductQualityRunner:
    """按页读取商品事实并执行有限质量规则。"""

    def __init__(self, reader: ProductOfferReader, *, page_size: int = 100) -> None:
        if not 1 <= page_size <= 500:
            raise ValueError("质量检查页大小必须在 1 到 500 之间")
        self._reader = reader
        self._page_size = page_size

    async def run(self, job: QualityCheckJob) -> list[QualityFinding]:
        """读取完整商品页链并返回去重后的质量问题。"""
        findings: list[QualityFinding] = []
        cursor: str | None = None
        seen_cursors: set[str] = set()
        while True:
            page = await self._reader.list_product_offers(
                workspace_id=job.workspace_id, cursor=cursor, limit=self._page_size
            )
            for item in page.items:
                record = {
                    "offer_id": item.offer_id,
                    "name": item.name,
                    "price": item.price,
                    "currency": item.currency,
                    "available_stock": item.available_stock,
                }
                findings.extend(check_required_and_enum(
                    record, required_fields=("offer_id", "name", "currency"),
                    enum_fields={"currency": frozenset({"RUB", "CNY"})},
                ))
                findings.extend(check_amount_and_inventory(record))
            next_cursor = page.next_cursor
            if next_cursor is None:
                break
            if next_cursor in seen_cursors:
                raise ValueError("商品质量检查游标重复，已停止以防止死循环")
            seen_cursors.add(next_cursor)
            cursor = next_cursor
        return _deduplicate_findings(findings)


def _deduplicate_findings(findings: list[QualityFinding]) -> list[QualityFinding]:
    """同一规则和字段只保留一条，避免分页重叠造成重复质量问题。"""
    result: list[QualityFinding] = []
    seen: set[tuple[str, str, str]] = set()
    for finding in findings:
        key = (finding.rule_code, finding.field_name, finding.message)
        if key not in seen:
            seen.add(key)
            result.append(finding)
    return result
