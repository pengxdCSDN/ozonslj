"""商品事实质量规则运行器测试。"""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from backend.app.application.product_quality_runner import ProductQualityRunner
from backend.app.domain.data_quality import QualityCheckJob
from backend.app.domain.product_offer import ProductOffer, ProductOfferPage


@dataclass
class Reader:
    pages: list[ProductOfferPage]

    async def list_product_offers(
        self, *, workspace_id: str, cursor: str | None, limit: int
    ) -> ProductOfferPage:
        del workspace_id, limit
        return self.pages[0] if cursor is None else self.pages[1]


def _job() -> QualityCheckJob:
    return QualityCheckJob(
        id="quality-1", workspace_id="workspace-1", status="running", data_version="v1",
        idempotency_key="key-1", parent_run_id="run-1", attempt_count=1,
        created_at=datetime.now(UTC),
    )


def test_runner_checks_product_price_stock_and_currency() -> None:
    page = ProductOfferPage(
        items=[ProductOffer(
            offer_id="offer-1", name="商品", price=Decimal("0"), currency="USD",
            available_stock=0,
        )], total=1, source="postgresql"
    )
    findings = asyncio.run(ProductQualityRunner(Reader([page])).run(_job()))
    assert {finding.rule_code for finding in findings} == {"DQ-003-ENUM", "DQ-005-AMOUNT"}


def test_runner_stops_on_repeated_cursor() -> None:
    page = ProductOfferPage(items=[], total=1, next_cursor="same", source="postgresql")
    reader = Reader([page, page])
    try:
        asyncio.run(ProductQualityRunner(reader).run(_job()))
    except ValueError as error:
        assert "游标重复" in str(error)
    else:
        raise AssertionError("重复游标必须熔断")
