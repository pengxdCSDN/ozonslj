from typing import Annotated

from fastapi import APIRouter, Depends, Query

from backend.app.api.dependencies import get_product_offer_gateway
from backend.app.domain.product_offer import ProductOfferPage
from backend.app.infrastructure.ozon.gateway import ProductOfferGateway

router = APIRouter(prefix="/v1/store-workspaces", tags=["product-offers"])


@router.get("/{workspace_id}/product-offers", response_model=ProductOfferPage)
async def list_product_offers(
    workspace_id: str,
    gateway: Annotated[ProductOfferGateway, Depends(get_product_offer_gateway)],
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ProductOfferPage:
    # The local workspace is the only accepted workspace until persistence/auth is added.
    if workspace_id != "local":
        return ProductOfferPage(items=[], total=0, next_cursor=None, source="stub")
    return await gateway.list_product_offers(cursor=cursor, limit=limit)

