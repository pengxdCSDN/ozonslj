"""说明本模块的职责、边界和主要协作对象。"""

from collections.abc import Sequence
from decimal import Decimal
from typing import Protocol

from backend.app.domain.product_offer import ProductOffer, ProductOfferPage
from backend.app.domain.store_workspace import WorkspaceNotFoundError


class ProductOfferGateway(Protocol):
    """说明 ProductOfferGateway 的职责、状态边界和对外协作关系。"""
    async def list_product_offers(
        self,
        *,
        workspace_id: str,
        cursor: str | None,
        limit: int,
    ) -> ProductOfferPage:
        """执行 list_product_offers 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    cursor: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。"""


STUB_PRODUCT_OFFERS: Sequence[ProductOffer] = (
    ProductOffer(
        offer_id="CN-MUG-420-BL",
        ozon_product_id="1847295031",
        name="双层保温杯 420ml",
        price=Decimal("1290.00"),
        currency="RUB",
        available_stock=37,
    ),
    ProductOffer(
        offer_id="CN-LAMP-DESK-WH",
        ozon_product_id="1847295188",
        name="可调光桌面灯",
        price=Decimal("2490.00"),
        currency="RUB",
        available_stock=12,
    ),
    ProductOffer(
        offer_id="CN-BAG-TRAVEL-28",
        ozon_product_id="1847295276",
        name="轻量旅行收纳包",
        price=Decimal("890.00"),
        currency="RUB",
        available_stock=0,
    ),
)


class StubOzonGateway:
    """说明 StubOzonGateway 的职责、状态边界和对外协作关系。"""
    _offers = STUB_PRODUCT_OFFERS

    async def list_product_offers(
        self,
        *,
        workspace_id: str,
        cursor: str | None,
        limit: int,
    ) -> ProductOfferPage:
        """执行 list_product_offers 的业务流程并返回该流程的结果。

Args:
    workspace_id: 参数语义、输入边界和安全约束。
    cursor: 参数语义、输入边界和安全约束。
    limit: 参数语义、输入边界和安全约束。

Returns:
    返回调用完成后的领域结果。

Raises:
    WorkspaceNotFoundError: 业务约束或外部依赖失败时抛出。
"""
        if workspace_id != "local":
            raise WorkspaceNotFoundError(workspace_id)
        start = int(cursor) if cursor else 0
        end = min(start + limit, len(self._offers))
        next_cursor = str(end) if end < len(self._offers) else None
        return ProductOfferPage(
            items=list(self._offers[start:end]),
            total=len(self._offers),
            next_cursor=next_cursor,
            source="stub",
        )
