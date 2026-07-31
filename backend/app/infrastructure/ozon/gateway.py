from collections.abc import Sequence
from decimal import Decimal
from typing import Protocol

from backend.app.domain.product_offer import ProductOffer, ProductOfferPage
from backend.app.domain.store_workspace import WorkspaceNotFoundError


class ProductOfferGateway(Protocol):
    async def list_product_offers(
        self,
        *,
        workspace_id: str,
        cursor: str | None,
        limit: int,
    ) -> ProductOfferPage: ...


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
    _offers = STUB_PRODUCT_OFFERS

    async def list_product_offers(
        self,
        *,
        workspace_id: str,
        cursor: str | None,
        limit: int,
    ) -> ProductOfferPage:
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
